import base64
import cv2
import numpy as np
from flask import Flask, render_template
from flask_socketio import SocketIO
import threading
import queue
from ultralytics import YOLO
from HikSDKHelper import *


# 共享队列（线程安全）
frame_queue = queue.Queue(maxsize=3)  # 限制队列长度避免内存堆积
result_queue = queue.Queue(maxsize=3)

def DecCBFun(nPort, pBuf, nSize, pFrameInfo, nUser, nReserved2):
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

        # ret, jpeg_data = cv2.imencode('.jpg', rgb_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        # socketio.emit('video_frame', {'data': base64.b64encode(jpeg_data).decode()})

def real_data_callback(lPlayHandle, dwDataType, pBuffer, dwBufSize, pUser):
    # 码流回调函数
    if dwDataType == NET_DVR_SYSHEAD:
        # 获取一个播放句柄
        if not dev.playM4SDK.PlayM4_GetPort(byref(dev.PlayCtrlPort)):
            print(f'获取播放库句柄失败, 错误码：{dev.playM4SDK.PlayM4_GetLastError(dev.PlayCtrlPort)}')
        dev.playM4SDK.PlayM4_SetStreamOpenMode(dev.PlayCtrlPort, 0)
        # 打开码流，送入40字节系统头数据
        if dev.playM4SDK.PlayM4_OpenStream(dev.PlayCtrlPort, pBuffer, dwBufSize, 1024 * 1024):
            dev.playM4SDK.PlayM4_SetDecCallBackExMend(dev.PlayCtrlPort, funcDecCB, None, 0, None)
            # 开始解码播放
            if dev.playM4SDK.PlayM4_Play(dev.PlayCtrlPort, None):
                print(u'播放库播放成功')
            else:
                print(u'播放库播放失败')
        else:
            print(f'播放库打开流失败, 错误码：{dev.playM4SDK.PlayM4_GetLastError(dev.PlayCtrlPort)}')
    elif dwDataType == NET_DVR_STREAMDATA:
        dev.playM4SDK.PlayM4_InputData(dev.PlayCtrlPort, pBuffer, dwBufSize)
    else:
        print(u'其他数据,长度:', dwBufSize)

nPort = C_LONG(-1)
# 初始化摄像机设备
dev = devClass()
dev.Init()
dev.LoginDev(ip=b'192.168.1.5', username=b"admin", pwd=b"SHENG666sheng")  # 登录设备
# 设置回调函数
funRealDataCallBack = REALDATACALLBACK(real_data_callback)
funcDecCB = DECCBFUNWIN(DecCBFun)

def capture_thread():
    preview_info = NET_DVR_PREVIEWINFO()
    preview_info.hPlayWnd = 0
    preview_info.lChannel = 1  # 通道号
    preview_info.dwStreamType = 0  # 主码流
    preview_info.dwLinkMode = 0  # TCP
    preview_info.bBlocked = 1  # 阻塞取流
    # 设置回调函数回调获取实时流数据
    result = dev.hikSDK.NET_DVR_RealPlay_V40(dev.iUserID, byref(preview_info),
                                                            funRealDataCallBack,
                                                            None)
    if result < 0:
        print('Open preview fail, error code is: %d' % dev.hikSDK.NET_DVR_GetLastError())
        dev.stopPlay()

def inference_thread():
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

def display_thread():
    while True:
        frame = result_queue.get()
        ret, jpeg_data = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if ret:
            socketio.emit('video_frame', {'data': base64.b64encode(jpeg_data).decode()})
        socketio.sleep(0.01)  # 使用SocketIO的sleep,控制帧率
    # cv2.namedWindow("Stream", cv2.WINDOW_NORMAL)
    # cv2.resizeWindow("Stream", 1280, 720)
    #
    # while True:
    #     # frame = frame_queue.get()
    #     frame = result_queue.get()
    #     cv2.imshow("Stream", frame)
    #     if cv2.waitKey(1) == 27:  # ESC退出
    #         break
    # cv2.destroyAllWindows()


#
# if __name__ == "__main__":
#     # 启动线程
#     threading.Thread(target=capture_thread, daemon=True).start()
#     threading.Thread(target=inference_thread, daemon=True).start()
#     display_thread()  # 主线程运行显示


app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

@app.route('/')
def index():
    return render_template('index1.html')


if __name__ == '__main__':
    # 启动视频流线程
    threading.Thread(target=capture_thread, daemon=True).start()
    threading.Thread(target=inference_thread, daemon=True).start()
    socketio.start_background_task(display_thread)
    socketio.run(app, host='0.0.0.0', port=5000,allow_unsafe_werkzeug=True)
