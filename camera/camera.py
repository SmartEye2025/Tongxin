import cv2
from threading import Thread
import queue
import numpy as np
from HikSDKHelper import *


frame_queue =  queue.Queue(maxsize=5)  # 限制队列长度避免内存堆积


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
            Thread(target=self.capture_thread, daemon=True).start()
            print('摄像头进程已启动')

        except Exception as e:
            print('摄像头启动失败:',e)

    def __del__(self):
        # 释放摄像头资源
        if hasattr(self, 'dev') and self.dev:
            self.dev.stopPlay()
            self.dev.LogoutDev()
            self.dev.hikSDK.NET_DVR_Cleanup()
            print("摄像头资源已释放")

    # 解码回调函数
    def DecCBFun(self, nPort, pBuf, nSize, pFrameInfo, nUser, nReserved2):
        # 解码回调函数
        if pFrameInfo.contents.nType == 3:
            # 解码YUV数据,YV12格式
            YUV = np.frombuffer(pBuf[:nSize], dtype=np.uint8)
            width = pFrameInfo.contents.nWidth
            height = pFrameInfo.contents.nHeight
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
