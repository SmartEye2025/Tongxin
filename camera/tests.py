import cv2
import json
import numpy as np
import websockets
import queue
from threading import Thread, Event
import asyncio
from asgiref.sync import sync_to_async
from HikSDKHelper import *

frame_queue = queue.Queue(maxsize=5)  # 限制队列长度避免内存堆积


class Camera:
    def __init__(self):
        try:
            # ----------海康摄像机参数----------
            self.dev = devClass()
            self.funRealDataCallBack = REALDATACALLBACK(self.real_data_callback)
            self.funcDecCB = DECCBFUNWIN(self.DecCBFun)
            # ------ 初始化摄像头 ------
            self.dev.Init()
            print('登录摄像头......')
            self.dev.LoginDev(ip=b'192.168.1.5', username=b"admin", pwd=b"SHENG666sheng")
            # 启动线程
            self.camera_thread = Thread(target=self.capture_thread, daemon=True).start()
            print('摄像头进程已启动')

        except Exception as e:
            print('摄像头启动失败:', e)

    def __del__(self):
        # 释放摄像头资源
        if hasattr(self, 'dev') and self.dev:
            self.dev.stopPlay()
            self.dev.LogoutDev()
            self.dev.hikSDK.NET_DVR_Cleanup()
            print("摄像头资源已释放")

    # 解码回调函数
    def DecCBFun(self, nPort, pBuf, nSize, pFrameInfo, nUser, nReserved2):
        # 解码YUV数据,YV12格式
        YUV = np.frombuffer(pBuf[:nSize], dtype=np.uint8)
        height, width = 720, 1280
        YUV = np.reshape(YUV, [height + height // 2, width])
        frame = cv2.cvtColor(YUV, cv2.COLOR_YUV2RGB_YV12)
        del YUV
        # 非阻塞放入队列，若满则丢弃旧帧
        if frame_queue.full():
            old_frame = frame_queue.get_nowait()  # 快速丢弃旧帧
            del old_frame
        frame_queue.put(frame)

    # 码流回调函数
    def real_data_callback(self, lPlayHandle, dwDataType, pBuffer, dwBufSize, pUser):
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

    # 捕获视频流线程--海康SDK
    def capture_thread(self):
        preview_info = NET_DVR_PREVIEWINFO()
        preview_info.hPlayWnd = 0
        preview_info.lChannel = 1  # 通道号
        preview_info.dwStreamType = 0  # 主码流
        preview_info.dwLinkMode = 0  # TCP
        # preview_info.dwLinkMode = 1  # UDP
        preview_info.bBlocked = 0  # 非阻塞取流
        # 设置回调函数回调获取实时流数据
        result = self.dev.hikSDK.NET_DVR_RealPlay_V40(self.dev.iUserID, byref(preview_info),
                                                      self.funRealDataCallBack,
                                                      None)
        if result < 0:
            print('Open preview fail, error code is: %d' % self.dev.hikSDK.NET_DVR_GetLastError())
            self.dev.stopPlay()

    # 捕获视频流线程--RTSP流
    # def capture_thread(self):
    #     # RTSP拉流（需摄像机开启RTSP服务）
    #     rtsp_url = "rtsp://admin:SHENG666sheng@192.168.1.5:554/Streaming/Channels/101"
    #     cap = cv2.VideoCapture(rtsp_url)
    #     cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 减少缓冲区
    #     cap.set(cv2.CAP_PROP_FPS, 30)  # 设置预期FPS
    #
    #     while True:
    #         ret, frame = cap.read()
    #         if not ret:
    #             break
    #         # 非阻塞放入队列，若满则丢弃旧帧
    #         if frame_queue.full():
    #             frame_queue.get()
    #         frame_queue.put(frame)
    #     cap.release()


camera = Camera()

# 停止标志
stop_event = Event()


async def send_frames(max_retries=5, retry_delay=3):
    """
    WebSocket发送协程（带自动重连）
    :param uri: WebSocket服务器地址
    :param max_retries: 最大重试次数（None表示无限重试）
    :param retry_delay: 重试延迟（秒）
    """
    uri = 'ws://192.168.1.2:8001/ws/video/'
    retries = 0

    while not stop_event.is_set():
        try:
            print(f"Connecting to WebSocket server at {uri}...")
            async with websockets.connect(uri) as ws:
                print("Connected to WebSocket server")
                retries = 0  # 重置重试计数器

                while not stop_event.is_set():
                    try:
                        if frame_queue.full():
                            print('队列满')
                        # 从队列获取帧（设置超时避免永久阻塞）
                        frame = await sync_to_async(lambda: frame_queue.get(timeout=1.0))()
                        results = {
                            "objects": [{
                                "id": 1,
                                "bbox": [100, 100, 200, 200],
                                "pose": [[x, y] for x, y in zip(range(0, 300, 20), range(0, 300, 20))]
                            }]
                        }

                        # # 发送二进制帧
                        # _, jpeg = cv2.imencode('.jpg', cv2.cvtColor(frame,cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 80])
                        # await ws.send(jpeg.tobytes())

                        # 发送JSON元数据
                        await ws.send(json.dumps({
                            'type': 'detect',
                            "frame_id": int(time.time() * 1000),
                            "results": results,
                            "timestamp": time.time()
                        }))
                        del frame

                    except queue.Empty:
                        print('等待新帧')
                        continue  # 队列为空，继续循环
                    except websockets.exceptions.ConnectionClosed:
                        print("连接中断，尝试重连...")
                        break  # 跳出内层循环，触发重连
                    except Exception as e:
                        print(f"发送错误: {str(e)}")
                        break  # 未知错误，触发重连

        except (websockets.exceptions.InvalidURI, ConnectionRefusedError) as e:
            print(f"连接失败: {e}")
        except Exception as e:
            print(f"未知错误: {e}")
        finally:
            if stop_event.is_set():
                break  # 停止事件触发，退出循环

            # 检查是否达到最大重试次数
            if max_retries is not None and retries >= max_retries:
                print(f"达到最大重连次数：{max_retries}")
                break

            retries += 1
            print(f"Retrying in {retry_delay} seconds... (Attempt {retries})")
            await asyncio.sleep(retry_delay)

    print("发送进程结束")


asyncio.run(send_frames())