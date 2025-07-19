import cv2
from ultralytics import YOLO
import queue
import threading


# 共享队列（线程安全）
frame_queue = queue.Queue(maxsize=3)  # 限制队列长度避免内存堆积
result_queue = queue.Queue(maxsize=3)


def capture_thread():
    # RTSP拉流（需摄像机开启RTSP服务）
    rtsp_url = "rtsp://admin:SHENG666sheng@192.168.1.6:554/Streaming/Channels/101"
    cap = cv2.VideoCapture(rtsp_url)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 减少缓冲区
    cap.set(cv2.CAP_PROP_FPS, 30)  # 设置预期FPS

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        # 非阻塞放入队列，若满则丢弃旧帧
        if frame_queue.full():
            frame_queue.get()
        frame_queue.put(frame)
    cap.release()

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
        result_queue.put(annotated_frame)  # 渲染检测框


def display_thread():
    cv2.namedWindow("Stream", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Stream", 1280, 720)

    while True:
        frame = result_queue.get()
        cv2.imshow("Stream", frame)
        if cv2.waitKey(1) == 27:  # ESC退出
            break
    cv2.destroyAllWindows()

if __name__ == "__main__":
    # 启动线程
    threading.Thread(target=capture_thread, daemon=True).start()
    threading.Thread(target=inference_thread, daemon=True).start()
    display_thread()  # 主线程运行显示
