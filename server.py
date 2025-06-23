
import numpy as np
from flask import Flask, Response, render_template
import cv2
import threading
from HikMain import *

app = Flask(__name__)
# 初始化设备
dev = devClass()
dev.SetSDKInitCfg()  # 设置SDK初始化依赖库路径
dev.hikSDK.NET_DVR_Init()  # 初始化sdk
dev.GeneralSetting()  # 通用设置，日志，回调函数等
dev.LoginDev(ip=b'192.168.1.5', username=b"admin", pwd=b"SHENG666sheng")  # 登录设备
# 抓图参数配置
iChannel = 1  # 通道号
jpegPara = NET_DVR_JPEGPARA()
jpegPara.wPicQuality = 0  # 图像质量
jpegPara.wPicSize = 167  # 抓图分辨率，0xff- Auto(使用当前码流分辨率),167-720*960
iBuffsize = 400000
iSizeReturned = c_ulong(0)  # 返回图像数据大小

# 全局变量用于存储视频帧
latest_frame = None

def get_video_stream():
    global latest_frame
    while True:
        try:
            iBuffer = create_string_buffer(iBuffsize)
            # 抓图
            result = dev.hikSDK.NET_DVR_CaptureJPEGPicture_NEW(dev.iUserID,iChannel,byref(jpegPara),iBuffer,c_ulong(iBuffsize),byref(iSizeReturned))
            if result==0:
                print('抓图错误，错误代码为：',dev.hikSDK.NET_DVR_GetLastError())
            else:
                frame = cv2.imdecode(np.frombuffer(iBuffer, dtype=np.uint8), cv2.IMREAD_COLOR)
                print('图片大小：',iSizeReturned)
                latest_frame = frame
        except Exception as e:
            print(f"Error fetching video stream: {e}")
            break

# 启动一个线程来获取视频流
threading.Thread(target=get_video_stream, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')

def gen_frames():
    global latest_frame
    while True:
        if latest_frame is not None:
            # 将 OpenCV 格式的帧转换为 JPEG 格式
            _, buffer = cv2.imencode('.jpg', latest_frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        else:
            # 如果没有帧，发送一个空白图像
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + np.zeros((480, 640, 3), dtype=np.uint8).tobytes() + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(debug=True)