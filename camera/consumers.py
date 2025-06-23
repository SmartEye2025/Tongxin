import cv2
import base64
import asyncio
from threading import Thread
import queue
import numpy as np
from ultralytics import YOLO
from channels.generic.websocket import AsyncWebsocketConsumer
from HikSDKHelper import *


# 共享队列（线程安全）
frame_queue =  queue.Queue(maxsize=5)  # 限制队列长度避免内存堆积
result_queue = queue.Queue(maxsize=5)

class VideoConsumer(AsyncWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dev = devClass()
        # 设置回调函数
        self.funRealDataCallBack = REALDATACALLBACK(self.real_data_callback)
        self.funcDecCB = DECCBFUNWIN(self.DecCBFun)
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
            # 非阻塞放入队列，若满则丢弃旧帧
            if frame_queue.full():
                frame_queue.get()
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

    def inference_thread(self):
        # 初始化YOLO模型
        model = YOLO('weight/yolo11n-pose.pt')
        model.to('cuda')

        while True:
            frame = frame_queue.get()  # 阻塞获取
            results = model(frame)  # 推理
            del frame  # 立即释放内存
            annotated_frame = results[0].plot()  # 获取带有检测结果的帧
            # 非阻塞传递结果
            if result_queue.full():
                result_queue.get()
            result_queue.put(annotated_frame)

    async def connect(self):
        await self.accept()

        # 初始化摄像机设备
        self.dev.Init()
        self.dev.LoginDev(ip=b'192.168.1.5', username=b"admin", pwd=b"SHENG666sheng")  # 登录设备
        # 启动消费者进程
        Thread(target=self.capture_thread, daemon=True).start()
        Thread(target=self.inference_thread, daemon=True).start()
        # 持续发送推理结果
        while True:
            if not result_queue.empty():
                frame = result_queue.get()
                _, buffer = cv2.imencode('.jpg', frame)
                await self.send(text_data=base64.b64encode(buffer).decode())
            await asyncio.sleep(0.01)  # 避免空转占用CPU
