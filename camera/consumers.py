import time
import cv2
import asyncio
from threading import Thread
import queue
import numpy as np
import torch
from ultralytics import YOLO
from channels.generic.websocket import AsyncWebsocketConsumer
from HikSDKHelper import *
import serial
import json
from camera.mqtt_client import client
from camera.models import *
from camera.servo import OmnidirectionalGimbal
from camera.speaker import Speaker
from sklearn.neighbors import KDTree
from asgiref.sync import sync_to_async


# 共享队列（线程安全）
frame_queue =  queue.Queue(maxsize=3)  # 限制队列长度避免内存堆积
location_queue = queue.Queue(maxsize=10)

# 像素坐标到世界坐标转化
def pixel_to_world(matrix, x, y):
    h_matrix = np.array(matrix)

    if h_matrix.shape != (3, 3):
        raise ValueError("透视变换矩阵必须是3x3矩阵")
    # 创建齐次像素坐标向量 [x, y, 1]
    pixel_vec = np.array([[x], [y], [1]])
    # 计算世界坐标
    world_vec = np.dot(h_matrix, pixel_vec)
    # 转换为非齐次坐标
    w = world_vec[2, 0]
    if w == 0:
        raise ValueError("齐次坐标w不能为0")
    world_x = world_vec[0, 0] / w
    world_y = world_vec[1, 0] / w
    return world_x, world_y

# 坐标点匹配算法
def match_points(cal_points,actual_points):
    cal_points = np.array(cal_points)
    actual_points = np.array(actual_points)
    results = []
    # 构建 KD 树用于快速最近邻搜索
    tree = KDTree(actual_points)
    # 对每个点，寻找实际物理坐标中的最近邻
    distances, indices = tree.query(cal_points, k=1)
    # 检查是否在允许的最大距离内
    for i in range(len(cal_points)):
        distance = distances[i]
        index = indices[i][0]
        results.append([cal_points[i].tolist(), actual_points[index].tolist(), distance[0], index])

    return results

#--------------------------------摄像头-----------------------------------------
class VideoConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dev = None
        self.ser = None
        self.model = None
        self.inference_task = None
        self.gimbal = None  #  舵机云台
        self.speaker = None  # 定向扬声器

        self.enableHotMap = True  # 是否显示热力图
        self.enableAutoRemind = True  # 是否启用自动提醒
        self.serial_thread_running = False  # 监视串口进程状态

        self.locations = {}

    async def connect(self):
        await self.accept()
        print(f"客户端 {self.scope['client']} 已连接")

        try:
            # ------ 初始化摄像头 ------
            self.dev = devClass()
            self.funRealDataCallBack = REALDATACALLBACK(self.real_data_callback)
            self.funcDecCB = DECCBFUNWIN(self.DecCBFun)
            self.dev.Init()
            self.dev.LoginDev(ip=b'192.168.1.5', username=b"admin", pwd=b"SHENG666sheng")

            # ------ 初始化串口 ------
            self.ser = serial.Serial('COM6', baudrate=115200, timeout=1)
            self.serial_thread_running = True

            # ------ 初始化YOLO模型 ------
            self.model = YOLO('weight/yolo11n-pose.pt')
            self.model.to('cuda')

            # ------ 初始化舵机控制器 ------
            # 异步获取云台坐标点
            obj = await sync_to_async(
                lambda: Classroom.objects.last(),
                thread_sensitive=True
            )()
            if obj:
                self.gimbal = OmnidirectionalGimbal((obj.ptz_x, obj.ptz_y, obj.ptz_z),obj.base_z)

            # ------ 初始化定向扬声器 ------
            self.speaker = Speaker(device_name='RSK', audio='0006.mp3')
            self.speaker.connect()

            # 启动线程
            Thread(target=self.capture_thread, daemon=True).start()
            Thread(target=self.serial_thread, daemon=True).start()

            # 启动异步推理任务
            self.inference_task = asyncio.create_task(self.inference_loop())

        except Exception as e:
            print(f"初始化失败: {e}")
            await self.cleanup_resources()  # 如果初始化失败，立即清理
            raise  # 抛出异常，让连接失败

    async def disconnect(self, close_code):
        print(f"客户端 {self.scope['client']} 已断开")

        try:
            # 取消推理任务
            if self.inference_task and not self.inference_task.done():
                self.inference_task.cancel()
                try:
                    await asyncio.wait_for(self.inference_task, timeout=1.0)
                except (asyncio.CancelledError, asyncio.TimeoutError) as e:
                    print(f"任务取消结果: {type(e).__name__}")

            # 清理资源
            await self.cleanup_resources()

        except Exception as e:
            print(f"disconnect 全局异常: {e}")
        finally:
            print("disconnect 执行完毕")  # 最终确认

    async def cleanup_resources(self):
        """统一清理所有资源"""
        # 停止串口线程
        if hasattr(self, 'serial_thread_running'):
            self.serial_thread_running = False  # 通知线程退出
        # 关闭串口
        if hasattr(self, 'ser') and self.ser and self.ser.is_open:
            self.ser.close()
            print("串口已关闭")
        # 释放摄像头资源
        if hasattr(self, 'dev') and self.dev:
            self.dev.stopPlay()
            self.dev.LogoutDev()
            self.dev.hikSDK.NET_DVR_Cleanup()
            print("摄像头资源已释放")

        # 释放YOLO模型
        if hasattr(self, 'model') and self.model:
            del self.model
            torch.cuda.empty_cache()
            print("YOLO模型已释放")
        # 释放扬声器资源
        if hasattr(self, 'speaker') and self.speaker:
            self.speaker.disconnect()

    async def receive(self, text_data):
        data = json.loads(text_data)
        print(data)
        if data.get('type') == 'setting1':
            self.enableHotMap = data.get('enableHotMap')
        elif data.get('type') == 'setting2':
            self.enableAutoRemind = data.get('enableAutoRemind')
        elif data.get('type') == 'control':
            await self.send_reminder(data.get('remindStudentId'),intensity=data.get('intensity'))
    # 解码回调函数
    def DecCBFun(self,nPort, pBuf, nSize, pFrameInfo, nUser, nReserved2):
        # 解码回调函数
        if pFrameInfo.contents.nType == 3:
            # 解码YUV数据,YV12格式
            YUV = np.frombuffer(pBuf[:nSize], dtype=np.uint8)
            width = pFrameInfo.contents.nWidth
            height = pFrameInfo.contents.nHeight
            YUV = np.reshape(YUV, [height + height // 2, width])
            frame = cv2.cvtColor(YUV, cv2.COLOR_YUV2BGR_YV12)
            del YUV
            # 非阻塞放入队列，若满则丢弃旧帧
            if frame_queue.full():
                frame_queue.get_nowait()  # 快速丢弃旧帧
            frame_queue.put(frame)

    # 码流回调函数
    def real_data_callback(self,lPlayHandle, dwDataType, pBuffer, dwBufSize, pUser):
        if dwDataType == NET_DVR_SYSHEAD:
            # 获取一个播放句柄
            if not self.dev.playM4SDK.PlayM4_GetPort(byref(self.dev.PlayCtrlPort)):
                print(f'获取播放库句柄失败, 错误码：{self.dev.playM4SDK.PlayM4_GetLastError(self.dev.PlayCtrlPort)}')
            self.dev.playM4SDK.PlayM4_SetStreamOpenMode(self.dev.PlayCtrlPort, 0)
            # 打开码流，送入40字节系统头数据
            if self.dev.playM4SDK.PlayM4_OpenStream(self.dev.PlayCtrlPort, pBuffer, dwBufSize, 1024 * 1024):
                self.dev.playM4SDK.PlayM4_SetDecCallBackExMend(self.dev.PlayCtrlPort, self.funcDecCB, None, 0, None)
                # 开始解码播放
                if self.dev.playM4SDK.PlayM4_Play(self.dev.PlayCtrlPort, None):
                    print(u'播放库播放成功')
                else:
                    print(u'播放库播放失败')
            else:
                print(f'播放库打开流失败, 错误码：{self.dev.playM4SDK.PlayM4_GetLastError(self.dev.PlayCtrlPort)}')
        elif dwDataType == NET_DVR_STREAMDATA:
            self.dev.playM4SDK.PlayM4_InputData(self.dev.PlayCtrlPort, pBuffer, dwBufSize)
        else:
            print(u'其他数据,长度:', dwBufSize)

    # 捕获视频流线程
    def capture_thread(self):
        preview_info = NET_DVR_PREVIEWINFO()
        preview_info.hPlayWnd = 0
        preview_info.lChannel = 1  # 通道号
        preview_info.dwStreamType = 0  # 主码流
        preview_info.dwLinkMode = 0  # TCP
        preview_info.bBlocked = 1  # 阻塞取流
        # 设置回调函数回调获取实时流数据
        result = self.dev.hikSDK.NET_DVR_RealPlay_V40(self.dev.iUserID, byref(preview_info),
                                                 self.funRealDataCallBack,
                                                 None)
        if result < 0:
            print('Open preview fail, error code is: %d' % self.dev.hikSDK.NET_DVR_GetLastError())
            self.dev.stopPlay()

    # 读取串口数据线程
    def serial_thread(self):
        while getattr(self, 'serial_thread_running', True):  # 使用标志位控制循环
            if self.ser.in_waiting > 0:
                raw_data = self.ser.read(29)  # 读取足够长的数据（至少29字节）
                if len(raw_data) >= 29:
                    try:
                        # 解析定位标签编号
                        id = (raw_data[3] << 8) | raw_data[4]
                        # 解析 x, y, z（假设数据从第7字节开始，索引6~11）
                        x = (raw_data[7] << 8) | raw_data[8]
                        y = (raw_data[9] << 8) | raw_data[10]
                        z = (raw_data[11] << 8) | raw_data[12]
                        # 转换为有符号 Int16（处理负数）
                        x = x if x < 32768 else x - 65536
                        y = y if y < 32768 else y - 65536
                        z = z if z < 32768 else z - 65536
                        # print(f"id:{id},x:{x}, y:{y}, z:{z}")
                        # 非阻塞传递结果
                        if location_queue.full():
                            old_data = location_queue.get()
                            del old_data  # 显示释放内存
                        location_queue.put([id, x, y, z])
                    except Exception as e:
                        print("解析错误:", e)

    # 向前端发送推理结果
    async def send_result(self, frame, results):
        # _, buffer = cv2.imencode('.jpg', frame)
        # print('111111')
        # self.send(text_data=json.dumps({
        #     'frame': base64.b64encode(buffer).decode(),
        #     'results': 1,
        # }))
        # asyncio.sleep(0.03)  # 控制帧率
        try:
            # 并行处理帧和结果
            loop = asyncio.get_running_loop()

            # 通道1：二进制视频帧（异步编码）
            buffer = await loop.run_in_executor(
                None,
                lambda: cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])[1]
            )

            # 通道2：文本检测结果
            result_data = json.dumps({
                "type": "detection",
                "data": results  # 可以是数组或对象
            })

            # 同时发送（顺序保证）
            await self.send(bytes_data=buffer.tobytes())  # 优先发送帧
            await self.send(text_data=result_data)  # 随后发送结果

        except Exception as e:
            print(f"发送失败: {e}")

    # 发送MQTT消息提醒
    async def send_reminder(self, student_id, intensity=1, remind_type=1):
        #  remind_type : 提醒类型，1-震动+语音，2-只震动，3-只语音
        if self.enableAutoRemind:
            if remind_type == 1:
                # 通过MQTT发送震动指令
                await client.publish(
                    f"remind/{student_id}/vibrate",
                    payload=json.dumps({
                        'intensity': intensity,
                        'duration': 20000
                    })
                )
                # 发送舵机旋转指令
                if student_id in self.locations:
                    x = self.locations[student_id]['x']
                    y = self.locations[student_id]['y']
                    pan, tilt, hem = self.gimbal.point_at()
                    await self.gimbal.normal_move(pan, tilt, hem,time_sleep=0.1)
                # 播放语音提醒
                self.speaker.play()
            elif remind_type == 2:
                # 通过MQTT发送震动指令
                await client.publish(
                    f"remind/{student_id}/vibrate",
                    payload=json.dumps({
                        'intensity': intensity,
                        'duration': 20000
                    })
                )
            elif remind_type == 3:
                # 发送舵机旋转指令
                if student_id in self.locations:
                    x = self.locations[student_id]['x']
                    y = self.locations[student_id]['y']
                    pan, tilt, hem = self.gimbal.point_at()
                    await self.gimbal.normal_move(pan, tilt, hem, time_sleep=0.1)
                # 播放语音提醒
                self.speaker.play()


    # 视频推理
    async def inference_loop(self):
        while True:
            try:
                start_time = time.time()
                # 异步获取帧（避免阻塞事件循环）
                frame = await sync_to_async(lambda: frame_queue.get(timeout=2.0))()
                # 异步执行CPU密集型操作
                loop = asyncio.get_running_loop()
                results = await loop.run_in_executor(
                    None,
                    lambda: self.model(frame, verbose=False)
                )
                annotated_frame = results[0].plot()
                # # 获取学生列表(uwb_id作为索引)
                # students = {}
                # for student in Student.objects.all():
                #     students[student.uwb_id] = {
                #         'student_id': student.student_id,
                #         'seat_x': student.seat_x,
                #         'seat_y': student.seat_y,
                #     }
                # # 获取坐标变换矩阵
                # H = TransformationMatrix.objects.last()
                # # 获取视频中每个对象的坐标
                # cal_points = []
                # for result in results:
                #     # 这里获取yolo检测结果中的左手关键点像素坐标（假设手环佩戴在左手）
                #     cal_points.append(pixel_to_world(H.matrix,result.pixel[0],result.pixel[1]))
                # # 获取定位系统返回的坐标,检查10条数据
                # actual_points = []
                # actual_points_dict = {}
                # for i in range(10):
                #     p = location_queue.get()
                #     # 确保是有效坐标点
                #     if p and not (p[1]==p[2]==p[3]==0):
                #         # 根据uwb_id求绑定的student_id
                #         student_id = students[p[0]]['student_id']
                #         actual_points_dict[student_id] = [p[1],p[2]]
                #     if len(actual_points_dict)>=len(students):
                #         break
                # # 生成实际坐标列表并记录索引
                # idx = 0
                # idx_dict = {}
                # for k, v in actual_points_dict.items():
                #     actual_points.append(v)
                #     idx_dict[idx] = k
                #     idx+=1
                #
                # # 坐标匹配
                # matched_res = match_points(cal_points, actual_points)
                # detected_results = []
                # for res in matched_res:
                #     student_id = idx_dict[res[3]]
                #     detected_results.append({
                #         'student_id':student_id,
                #         'x':res[1][0],
                #         'y':res[1][0],
                #         'behavior':'',
                #     })
                detected_results = []
                # 异步获取帧（避免阻塞事件循环）
                p = await sync_to_async(lambda: location_queue.get(timeout=2.0))()
                if p and not (p[1]==p[2]==p[3]==0):
                    # # 异步查询学生信息
                    # student = await sync_to_async(
                    #     lambda: Student.objects.get(uwb_id=p[0]),
                    #     thread_sensitive=True
                    # )()
                    detected_results = [{
                        'student_id': 1,
                        'x':p[1],
                        'y':p[2],
                        'z':p[3],
                    }]
                if self.enableHotMap:
                    send_frame = annotated_frame
                else:
                    send_frame = frame
                # 发送结果（带错误处理）
                await self.send_result(send_frame,detected_results)
                del frame,annotated_frame,results
                # 精确帧率控制
                await asyncio.sleep(max(0, 0.03 - (time.time() - start_time)))


            except queue.Empty:
                print("帧队列超时")
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"推理失败: {e}")
                await self.close()
                break

