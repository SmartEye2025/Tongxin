import time
import asyncio
import torch
from channels.generic.websocket import AsyncWebsocketConsumer
import json
from camera.models import *
from camera.camera import *
from camera.uwb import *
from camera.mqtt_client import client
from camera.servo import OmnidirectionalGimbal
from camera.speaker import speaker
from camera.detector import Detector
from sklearn.neighbors import KDTree
from asgiref.sync import sync_to_async


class VideoConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ----------行为识别检测器参数----------
        self.detector = Detector(
            yolo_path="weight/yolo11n-pose.pt",
            lstm_path="weight/attention_lstm_model_best.pth",
            label_mapping_path="weight/merged_label_mapping.json",
            font_path="weight/Deng.ttf",
            sequence_length=60,
            step=10,
            num_classes=6,
            # device=torch.device("cuda" if torch.cuda.is_available() else "cpu")
            device=torch.device("cpu")
        )
        self.inference_task = None

        self.gimbal = None  #  舵机云台
        # 设置
        self.enableHotMap = True  # 是否显示热力图
        self.enableAutoRemind = True  # 是否启用自动提醒
        self.off_seat_threshold = 200  # 离座判定阈值(cm)
        # 记录当前学生状态（以学号为索引）
        self.student_status = {}
        # 格式如下：
        # {
        #     'uwb_id':'',
        #     'x':0,  # 当前坐标
        #     'y':0,
        #     'seat_x': 0,  # 座位坐标
        #     'seat_y':0,
        #     'behavior':'',
        #     'status':'',  # 提醒状态，True:正在被提醒, False:未被提醒
        # }

    async def connect(self):
        await self.accept()
        print(f"客户端 {self.scope['client']} 已连接")

        try:
            # ------ 初始化行为识别模型 ------
            self.detector.load_all_models()

            # ------ 初始化舵机控制器 ------
            # 异步获取云台坐标点
            obj = await sync_to_async(
                lambda: Classroom.objects.last(),
                thread_sensitive=True
            )()
            if obj:
                self.gimbal = OmnidirectionalGimbal((obj.ptz_x, obj.ptz_y, obj.ptz_z),obj.base_z)

            # ------ 初始化学生状态列表 ------
            # 异步查询学生字典
            studentsObj = await sync_to_async(list)(Student.objects.all())
            for student in studentsObj:
                self.student_status[student.student_id] = {
                    'uwb_id': student.uwb_id,
                    'x':0,  # 当前坐标
                    'y':0,
                    'seat_x': student.seat_x,  # 座位坐标
                    'seat_y':student.seat_y,
                    'behavior':'normal',
                    'status': False
                }

            # 启动异步推理任务
            self.inference_task = asyncio.create_task(self.inference_loop())

        except Exception as e:
            print(f"初始化失败: {e}")
            # 清理资源,释放行为识别模型
            if hasattr(self, 'detector') and self.detector.pose_model and self.detector.action_model:
                del self.detector.pose_model
                del self.detector.action_model
                torch.cuda.empty_cache()
                print("模型资源已释放")
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

            # 清理资源,释放行为识别模型
            if hasattr(self, 'detector') and self.detector.pose_model and self.detector.action_model:
                del self.detector.pose_model
                del self.detector.action_model
                torch.cuda.empty_cache()
                print("模型资源已释放")

        except Exception as e:
            print(f"disconnect 全局异常: {e}")
        finally:
            print("disconnect 执行完毕")  # 最终确认


    # 像素坐标到世界坐标转化
    def pixel_to_world(self,matrix, x, y):
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
        return (world_x, world_y)

    def match_points(self,cal_points, actual_points, max_distance=None):
        # 构建结果字典：{actual_key: cal_key}
        matched_results = {}
        if cal_points and actual_points:
            # 提取 cal_points 的键（编号）和坐标
            cal_keys = list(cal_points.keys())
            cal_coords = np.array([v for v in cal_points.values()])

            # 提取 actual_points 的键（编号）和坐标
            actual_keys = list(actual_points.keys())
            actual_coords = np.array([v for v in actual_points.values()])

            # 构建 KD 树
            tree = KDTree(cal_coords)

            # 查询最近邻（k=1 表示每个点只找最近的一个）
            distances, indices = tree.query(actual_coords, k=1)

            for i, actual_key in enumerate(actual_keys):
                distance = distances[i][0]  # 最近邻距离
                cal_index = indices[i][0]  # cal_points 中的索引
                cal_key = cal_keys[cal_index]  # 匹配的 cal_points 的键

                # 如果设置了最大距离，检查是否满足条件
                if max_distance is not None and distance > max_distance:
                    continue  # 跳过不满足条件的匹配

                matched_results[actual_key] = cal_key  # 存储键的匹配关系

        return matched_results

    # 接收socket消息
    async def receive(self, text_data):
        data = json.loads(text_data)
        print('socket接收数据：',data)
        if data.get('type') == 'setting1':
            self.enableHotMap = data.get('enableHotMap')
        elif data.get('type') == 'setting2':
            self.enableAutoRemind = data.get('enableAutoRemind')
        elif data.get('type') == 'control':
            # 如果同时提醒多名学生，语音提醒只作用于列表第一个
            studentList = data.get('studentList')
            for student_id in studentList:
                # 发送提醒前先检查该学生当前是否在被提醒状态
                if not self.student_status[student_id]['status']:
                    self.send_vibrate_remind(student_id,remind_type=2)
                    # self.student_status[student_id]['status'] = True  # 由于是教师端控制单次提醒，所以不更新被提醒状态
            if not self.student_status[studentList[0]]['status']:
                await self.send_servo_order(studentList[0])
                # 提醒结束后恢复追踪状态
                self.gimbal.student_id = None
                speaker.play(studentList[0])

    # 向前端发送推理结果
    async def send_result(self, frame, results):
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

    # 发送震动提醒
    def send_vibrate_remind(self, student_id, remind_type):
        # remind_type : 提醒类型，1-自动震动提醒（梯度增强式），2-教师控制震动提醒（单次），3-关闭震动
        if client.is_connected():
            # 通过MQTT发送震动指令
            client.publish(
                f"remind/{student_id}/vibrate",
                payload="type"+str(remind_type) # 1表示自动提醒，2表示教师端控制提醒，3表示停止震动
            )

    # 发送云台控制指令
    async def send_servo_order(self, student_id):
        # 检查MQTT是否连接
        if client.is_connected():
            x = self.student_status[student_id]['x']
            y = self.student_status[student_id]['y']
            pan, tilt, hem = self.gimbal.point_at((x,y))
            await self.gimbal.normal_move(student_id, pan, tilt, hem,time_sleep=0.1)
        else:
            print('未连接mqtt，或当前云台正在追踪其他目标')

    # 决策函数
    async def decide(self):
        final_result = {}

        for k,student in self.student_status.items():
            behavior_status = current_behavior = student['behavior']
            if student['x']!=0 or student['y']!=0:
                # 计算当前位置与座位的欧氏距离
                current_dist = ((student['x'] - student['seat_x']) ** 2 +
                                (student['y'] - student['seat_y']) ** 2) ** 0.5
                print('偏离：',current_dist)
                # 根据座位偏离和视觉识别判断行为状态
                if current_dist > self.off_seat_threshold and (behavior_status != 'focus' or behavior_status != 'normal'):
                    # if current_behavior == 'walk' or current_behavior=='standup' or current_behavior=='dance':
                    behavior_status = 'offSeat'
                    # 检测到离座，发送提醒，发送提醒前先检查该学生当前是否在被提醒状态
                    if self.enableAutoRemind:
                        if not self.student_status[k]['status']:
                            self.send_vibrate_remind(k, remind_type=1)
                            # 播放语音提醒
                            speaker.play(k,loop=True)
                            self.student_status[k]['status'] = True
                        await self.send_servo_order(k)
                else:
                    if current_behavior == 'walk':
                        behavior_status = 'standup'
                    if self.enableAutoRemind:
                        # 若当前正在被提醒,则发送停止提醒指令
                        if self.student_status[k]['status']:
                            print('发送停止提醒指令')
                            self.send_vibrate_remind(k,remind_type=3)
                            # 停止语音提醒
                            speaker.stop()
                            self.student_status[k]['status'] = False
                            # 提醒结束后恢复追踪状态
                            self.gimbal.student_id = None
                            speaker.student_id = None

            final_result[k] = {
                'x': student['x'],
                'y': student['y'],
                'status': behavior_status
            }

        return final_result

    # 视频推理
    async def inference_loop(self):
        while True:
            try:
                start_time = time.time()
                # 异步获取帧（避免阻塞事件循环）
                frame = await sync_to_async(lambda: frame_queue.get(timeout=2.0))()
                loop = asyncio.get_running_loop()
                annotated_frame,persons_points,behaviors = await loop.run_in_executor(
                    None,
                    lambda: self.detector.detect(frame)
                )
                # 异步获取坐标变换矩阵
                classObj = await sync_to_async(
                    lambda: Classroom.objects.last(),
                    thread_sensitive=True
                )()
                H = classObj.matrix['data']
                # 像素坐标到物理坐标转化
                persons_points = {k:self.pixel_to_world(H,v[0],v[1]) for k,v in persons_points.items()}

                # 生成uwb_id-student_id的键值对映射
                uid2sid = {}
                for k,v in self.student_status.items():
                    uid2sid[v['uwb_id']] = k
                # 获取定位系统返回的坐标,检查10条数据
                actual_points = {}
                for i in range(1):
                    # 异步获取帧（避免阻塞事件循环）
                    p = await sync_to_async(lambda: location_queue.get(timeout=2.0))()
                    # 确保是有效坐标点
                    if p and not (p[1]==p[2]==p[3]==0):
                        # 根据uwb_id求绑定的student_id
                        student_id = uid2sid[str(p[0])]
                        actual_points[student_id] = (p[1],p[2])
                    if len(actual_points)>=len(uid2sid):
                        break
                # 坐标匹配
                matched_res = self.match_points(persons_points, actual_points)
                print('坐标匹配结果',matched_res)
                # 更新学生状态
                for student_id,track_id in matched_res.items():
                    # 若与当前坐标差距过大，则视为定位异常，保留原来坐标
                    coord = (self.student_status[student_id]['x'], self.student_status[student_id]['y'])
                    x = actual_points[student_id][0]
                    y = actual_points[student_id][1]
                    if coord == (0, 0) or (coord != (0, 0) and abs(coord[0] - x) + abs(coord[1] - y) < 500):
                        self.student_status[student_id]['x'] = x
                        self.student_status[student_id]['y'] = y
                    self.student_status[student_id]['behavior'] = behaviors[track_id]
                # 根据手环姿态感知和离座距离进一步优化检测结果，并做出决策，发送震动和扬声提醒
                final_results = await self.decide()
                if self.enableHotMap:
                    send_frame = annotated_frame
                else:
                    send_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                # 发送结果
                await self.send_result(send_frame,final_results)
                del frame,annotated_frame
                # 精确帧率控制
                await asyncio.sleep(max(0, 0.03 - (time.time() - start_time)))


            except queue.Empty:
                print("帧队列超时")
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"推理失败: {e}")
                await self.close()
                break

