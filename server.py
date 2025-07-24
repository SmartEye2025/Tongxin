import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import cv2
import numpy as np
import threading
import queue
from ultralytics import YOLO
from HikSDKHelper import *
import json
import torch
import torch.nn as nn
from collections import deque
import time
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

# 共享队列（线程安全）
frame_queue = queue.Queue(maxsize=5)  # 限制队列长度避免内存堆积


# result_queue = queue.Queue(maxsize=3)

def DecCBFun(nPort, pBuf, nSize, pFrameInfo, nUser, nReserved2):
    # 解码回调函数
    if pFrameInfo.contents.nType == 3:
        # 解码YUV数据,YV12格式
        YUV = np.frombuffer(pBuf[:nSize], dtype=np.uint8)
        width = pFrameInfo.contents.nWidth
        height = pFrameInfo.contents.nHeight
        YUV = np.reshape(YUV, [height + height // 2, width])
        # frame = cv2.cvtColor(YUV, cv2.COLOR_YUV2BGR_YV12)
        frame = cv2.cvtColor(YUV, cv2.COLOR_YUV2RGB_YV12)
        del YUV
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
dev.LoginDev(ip=b'192.168.1.6', username=b"admin", pwd=b"SHENG666sheng")  # 登录设备
# 设置回调函数
funRealDataCallBack = REALDATACALLBACK(real_data_callback)
funcDecCB = DECCBFUNWIN(DecCBFun)

# --- 1. 全局配置 ---
# 请根据您的实际文件路径和需求进行修改
CONFIG = {
    # --- 文件路径 ---
    "yolo_pose_model_path": "weight/yolo11n-pose.pt",
    "action_model_path": "weight/attention_lstm_model_best.pth",  # LSTM模型路径
    "label_mapping_path": "weight/merged_label_mapping.json",  # 使用合并版标签映射
    # 中文字体文件路径
    "font_path": "weight/Deng.ttf",

    # --- 模型参数 (兼容新训练的合并版模型) ---
    "sequence_length": 60,  # 与新模型训练时保持一致

    # --- 行为分析阈值 (可调整以优化灵敏度) ---
    "history_length": 5,  # 用于判断重复/持续行为的短期历史长度
    "stereotype_threshold": 4,  # 在history_length中，出现多少次刻板行为则触发
    "inattention_threshold": 4,  # 在history_length中，出现多少次分心行为则触发
}


# --- 行为状态机 ---
class BehaviorStateMachine:
    def __init__(self, track_id):
        self.track_id = track_id
        self.state = "IDLE"
        self.alert_message = ""
        self.last_action = "等待检测..."
        self.action_history = deque(maxlen=CONFIG["history_length"])
        self.STEREOTYPE_ACTIONS = {"dance", "curlup", "turn-head"}
        self.INATTENTION_ACTIONS = {"dance", "turn-head"}
        self.ELOPEMENT_ACTIONS = {"standup", "run", "walk"}

    def update(self, atomic_action):
        self.last_action = atomic_action
        self.action_history.append(atomic_action)
        self.alert_message = atomic_action
        print('动作：', atomic_action)
        # self.alert_message = ""

        # # 规则 0: 检测高频刻板行为 (最高优先级)
        # stereotype_count = sum(1 for act in self.action_history if act in self.STEREOTYPE_ACTIONS)
        # if len(self.action_history) == CONFIG["history_length"] and stereotype_count >= CONFIG["stereotype_threshold"]:
        #     if self.state != "STEREOTYPY": self.state = "STEREOTYPY"
        #     self.alert_message = "注意: 高频刻板行为"
        #     return
        #
        # # 规则 1: 处理正常状态 (SITTING_CALMLY)
        # if self.state == "SITTING_CALMLY":
        #     if atomic_action in self.ELOPEMENT_ACTIONS:
        #         self.state = "POTENTIAL_ELOPEMENT"
        #         self.alert_message = "!! 离座风险 !!"
        #     elif atomic_action == "handup":
        #         self.state = "HANDUP"
        #         self.alert_message = "举手 (正常)"
        #     else:
        #         inattention_count = sum(1 for act in self.action_history if act in self.INATTENTION_ACTIONS)
        #         if len(self.action_history) == CONFIG["history_length"] and inattention_count >= CONFIG[
        #             "inattention_threshold"]:
        #             self.state = "INATTENTION"
        #             self.alert_message = "注意: 持续分心"
        #
        # # 规则 2: 处理“举手”状态
        # elif self.state == "HANDUP":
        #     if atomic_action == "focus":
        #         self.state = "SITTING_CALMLY"
        #     elif atomic_action in self.ELOPEMENT_ACTIONS:
        #         self.state = "POTENTIAL_ELOPEMENT"
        #         self.alert_message = "!! 举手后离座 !!"
        #
        # # 规则 3: 处理“离座风险”状态
        # elif self.state == "POTENTIAL_ELOPEMENT":
        #     if atomic_action == "focus":
        #         self.state = "SITTING_CALMLY"
        #     elif atomic_action in ["walk", "turn-head"]:
        #         self.state = "WALKING_WANDERING"
        #         self.alert_message = "徘徊中..."
        #
        # # 规则 4: 处理“徘徊”状态
        # elif self.state == "WALKING_WANDERING":
        #     if atomic_action == "focus":
        #         self.state = "SITTING_CALMLY"
        #     elif atomic_action == "run":
        #         self.state = "POTENTIAL_ELOPEMENT"
        #         self.alert_message = "!! 徘徊中加速 !!"
        #
        # # 规则 5: 处理“分心”状态
        # elif self.state == "INATTENTION":
        #     if atomic_action == "focus":
        #         self.state = "SITTING_CALMLY"
        #     elif atomic_action in self.ELOPEMENT_ACTIONS:
        #         self.state = "POTENTIAL_ELOPEMENT"
        #         self.alert_message = "!! 分心后离座 !!"
        #
        # # 规则 6: 处理“刻板行为”状态
        # elif self.state == "STEREOTYPY":
        #     if atomic_action not in self.STEREOTYPE_ACTIONS: self.state = "IDLE"
        #
        #     # 默认初始化/恢复规则
        # if self.state == "IDLE":
        #     if atomic_action == "focus":
        #         self.state = "SITTING_CALMLY"
        #     elif atomic_action in self.ELOPEMENT_ACTIONS:
        #         self.state = "WALKING_WANDERING"
        #         self.alert_message = "徘徊中..."


    def get_display_info(self):
        # status_text = f"ID-{self.track_id} [状态: {self.state}] 动作:{self.last_action}"
        status_text = f"ID-{self.track_id} 动作:{self.last_action}"
        alert_text = self.alert_message
        return status_text, alert_text


# --- 辅助函数与类定义 ---
def draw_text_cn(frame, text, position, font_size, color_bgr):
    try:
        img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        font = ImageFont.truetype(CONFIG["font_path"], font_size, encoding="utf-8")
        draw.text(position, text, font=font, fill=color_bgr[::-1])  # PIL颜色是RGB
        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    except Exception as e:
        print(f"绘制中文失败: {e}")
        # 降级方案：使用OpenCV绘制英文字符
        cv2.putText(frame, "Error: Font not found.", position, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        return frame


class AttentionLayer(nn.Module):
    """
    注意力机制层
    输入: (batch_size, seq_len, hidden_size)
    输出: (batch_size, hidden_size), attention_weights
    """

    def __init__(self, hidden_size):
        super(AttentionLayer, self).__init__()
        self.hidden_size = hidden_size

        # 注意力权重计算网络
        self.attention = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.Tanh(),
            nn.Linear(hidden_size // 2, 1)
        )

    def forward(self, lstm_output):
        # lstm_output: (batch_size, seq_len, hidden_size)

        # 计算每个时间步的注意力得分
        attention_scores = self.attention(lstm_output)  # (batch_size, seq_len, 1)
        attention_scores = attention_scores.squeeze(-1)  # (batch_size, seq_len)

        # 应用softmax得到注意力权重
        attention_weights = torch.softmax(attention_scores, dim=1)  # (batch_size, seq_len)

        # 加权求和
        weighted_output = torch.sum(lstm_output * attention_weights.unsqueeze(-1), dim=1)  # (batch_size, hidden_size)

        return weighted_output, attention_weights


class AttentionLSTM(nn.Module):
    """
    带注意力机制的动作识别LSTM模型
    保持与原模型相同的接口，但内部使用Attention机制
    """

    def __init__(self, input_size=68, hidden_size=128, num_layers=2, num_classes=5, dropout=0.25, use_attention=True):
        super(AttentionLSTM, self).__init__()

        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.use_attention = use_attention

        # LSTM层
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0,
            batch_first=True,
            bidirectional=True  # 使用双向LSTM提高性能
        )

        # 双向LSTM的输出是hidden_size * 2
        lstm_output_size = hidden_size * 2

        # 注意力机制（可选）
        if self.use_attention:
            self.attention = AttentionLayer(lstm_output_size)
            print("🎯 启用注意力机制")
        else:
            print("📍 使用传统的最后时间步输出")

        # 全连接层
        self.fc1 = nn.Linear(lstm_output_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, num_classes)

        # 激活函数和正则化
        self.relu = nn.ReLU()
        self.dropout = nn.Dropout(dropout)
        self.batch_norm = nn.BatchNorm1d(hidden_size)

    def forward(self, x):
        # x shape: (batch_size, sequence_length, input_size)

        # LSTM前向传播
        lstm_out, (h_n, c_n) = self.lstm(x)  # (batch_size, seq_len, hidden_size*2)

        # 选择输出方式
        if self.use_attention:
            # 使用注意力机制加权融合所有时间步
            attended_output, attention_weights = self.attention(lstm_out)
            # 注意力权重可以用于可视化，了解模型关注哪些时间步
        else:
            # 传统方法：只使用最后一个时间步的输出
            attended_output = lstm_out[:, -1, :]

        # 全连接网络
        out = self.fc1(attended_output)
        out = self.batch_norm(out)
        out = self.relu(out)
        out = self.dropout(out)
        out = self.fc2(out)

        return out


def load_all_models():
    # device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    device = torch.device("cpu")
    print(f"正在使用设备进行推理: {device}")

    # 加载YOLO姿态检测模型
    pose_model = YOLO(CONFIG["yolo_pose_model_path"])

    # 加载标签映射
    with open(CONFIG["label_mapping_path"], 'r', encoding='utf-8') as f:
        label_mapping = json.load(f)
    idx_to_label = {int(v): k for k, v in label_mapping['action_to_label'].items()}
    num_classes = label_mapping['num_classes']

    model_path = CONFIG["action_model_path"]

    try:
        checkpoint = torch.load(model_path, map_location=device)
        action_model = AttentionLSTM()
        # 加载权重
        action_model.load_state_dict(checkpoint)
        action_model.eval()

        print(f"✓ 模型加载成功: {model_path}")

    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        raise e

    return pose_model, action_model, idx_to_label, device


def preprocess_sequence(keypoints_sequence):
    """
    预处理关键点序列，生成(x, y, dx, dy)特征格式
    输出维度：17关键点 * 4特征 = 68维
    """
    keypoints = np.array(keypoints_sequence, dtype=np.float32)

    # 计算髋关节中心点作为参考点进行归一化
    hip_center = np.mean(keypoints[:, [11, 12], :], axis=1, keepdims=True)

    # 计算相对坐标（相对于髋关节中心）
    normalized_keypoints = keypoints - hip_center

    # 计算躯干长度用于尺度归一化
    shoulder_center = np.mean(keypoints[:, [5, 6], :], axis=1, keepdims=True)
    torso_length = np.linalg.norm(shoulder_center - hip_center, axis=2, keepdims=True)
    torso_length[torso_length < 1e-6] = 1.0
    normalized_keypoints /= torso_length

    # 准备输出序列
    max_len = CONFIG["sequence_length"]
    seq_len = min(len(normalized_keypoints), max_len)
    processed_sequence = np.zeros((max_len, 68), dtype=np.float32)  # 17*4 = 68维

    # 计算每帧的(x, y, dx, dy)特征
    for i in range(seq_len):
        for j in range(17):  # 17个关键点
            # x, y坐标（归一化后）
            x, y = normalized_keypoints[i, j, 0], normalized_keypoints[i, j, 1]

            # 计算相对位移量 dx, dy（相对于前一帧的位置变化）
            if i > 0:
                dx = normalized_keypoints[i, j, 0] - normalized_keypoints[i - 1, j, 0]
                dy = normalized_keypoints[i, j, 1] - normalized_keypoints[i - 1, j, 1]
            else:
                dx, dy = 0.0, 0.0  # 第一帧位移量为0

            # 存储(x, y, dx, dy)特征
            feature_idx = j * 4
            processed_sequence[i, feature_idx:feature_idx + 4] = [x, y, dx, dy]

    return processed_sequence


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


def display_thread():
    cv2.namedWindow("Stream", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Stream", 1280, 720)

    while True:
        # frame = result_queue.get()
        try:
            frame = frame_queue.get(timeout=1)  # 阻塞获取，超时避免卡死
        except queue.Empty:
            print("等待新帧...")
            continue
        cv2.imshow("Stream", frame)
        if cv2.waitKey(1) == 27:  # ESC退出
            break
    cv2.destroyAllWindows()


def main():
    pose_model, action_model, idx_to_label, device = load_all_models()
    tracked_persons = {}
    step = 10
    cnt = 0
    while True:
        try:
            frame = frame_queue.get(timeout=1)  # 阻塞获取
        except queue.Empty:
            print("等待新帧...")
            continue
        results = pose_model.track(frame, persist=True, verbose=False)
        annotated_frame = results[0].plot()
        annotated_frame = cv2.cvtColor(annotated_frame, cv2.COLOR_RGB2BGR)

        current_tracked_ids = []
        if results[0].boxes and results[0].boxes.id is not None:
            track_ids = results[0].boxes.id.int().cpu().numpy()
            current_tracked_ids = list(track_ids)
            keypoints_data = results[0].keypoints.data
            boxes = results[0].boxes.xywh.cpu().numpy()
            print(keypoints_data.shape, boxes.shape)

            for track_id, kpts, box in zip(track_ids, keypoints_data, boxes):
                if track_id not in tracked_persons:
                    tracked_persons[track_id] = {"keypoints_q": deque(maxlen=CONFIG["sequence_length"]),
                                                 "fsm": BehaviorStateMachine(track_id), "center": (0, 0)}

                tracked_persons[track_id]["keypoints_q"].append(kpts[:, :2].cpu().numpy())
                tracked_persons[track_id]["center"] = (int(box[0]), int(box[1]))
                # 实现窗口按步长滑动
                cnt += 1
                if len(tracked_persons[track_id]["keypoints_q"]) == CONFIG["sequence_length"] and cnt>=step:
                    processed_seq = preprocess_sequence(tracked_persons[track_id]["keypoints_q"])
                    input_tensor = torch.FloatTensor(processed_seq).unsqueeze(0).to(device)

                    with torch.no_grad():
                        output = action_model(input_tensor)
                        _, pred_idx = torch.max(output, 1)

                    action_label = idx_to_label.get(pred_idx.item(), "未知")
                    tracked_persons[track_id]["fsm"].update(action_label)
                    cnt = 0

        for track_id in list(tracked_persons.keys()):
            if track_id not in current_tracked_ids:
                del tracked_persons[track_id]

        # --- 可视化 ---
        for track_id, data in tracked_persons.items():
            status_text, alert_text = data['fsm'].get_display_info()
            x_center, y_center = data['center']

            # 使用新的中文绘制函数
            if alert_text:
                annotated_frame = draw_text_cn(annotated_frame, alert_text,
                                             (x_center - 70, y_center - 55),
                                             font_size=20, color_bgr=(0, 0, 255))  # 红色

            annotated_frame = draw_text_cn(annotated_frame, status_text,
                                         (x_center - 70, y_center - 30),
                                         font_size=18, color_bgr=(0, 255, 0))  # 绿色

        cv2.imshow("瞳心守护 - 实时行为分析系统", annotated_frame)
        del frame,annotated_frame,results
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    # 启动线程
    threading.Thread(target=capture_thread, daemon=True).start()
    main()





