import os

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import cv2
import numpy as np
from ultralytics import YOLO
import json
import torch
import torch.nn as nn
from collections import deque
from PIL import Image, ImageDraw, ImageFont


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


class Detector:
    def __init__(self,yolo_path,lstm_path,label_mapping_path,font_path,sequence_length,step,num_classes,device):
        self.config = {
            # --- 文件路径 ---
            "yolo_pose_model_path": yolo_path,
            "action_model_path": lstm_path,  # LSTM模型路径
            "label_mapping_path": label_mapping_path,  # 使用合并版标签映射
            # 中文字体文件路径
            "font_path": font_path,

            # --- 模型参数 (兼容新训练的合并版模型) ---
            "sequence_length": sequence_length,  # 与新模型训练时保持一致
        }
        self.behavior_dict = {
            'detecting':'等待检测中',
            'normal':'正常',
            'focus':'专注',
            'dance':'多动',
            'handup':'举手',
            'standup':'起立',
            'walk':'走动'
        }
        self.device = device
        self.pose_model = None
        self.action_model = None
        self.num_classes = num_classes
        self.idx_to_label = {}
        self.tracked_persons = {}
        # 滑动窗口步长
        self.step = step
        self.cnt = 0

    # 加载模型
    def load_all_models(self):
        print(f"正在使用设备进行推理: {self.device}")

        # 加载YOLO姿态检测模型
        self.pose_model = YOLO(self.config["yolo_pose_model_path"])

        # 加载标签映射
        with open(self.config["label_mapping_path"], 'r', encoding='utf-8') as f:
            label_mapping = json.load(f)
        self.idx_to_label = {int(v): k for k, v in label_mapping['action_to_label'].items()}
        self.num_classes = label_mapping['num_classes']

        model_path = self.config["action_model_path"]

        try:
            checkpoint = torch.load(model_path, map_location=self.device)
            self.action_model = AttentionLSTM()
            # 加载权重
            self.action_model.load_state_dict(checkpoint)
            self.action_model.eval()

            print(f"✓ 模型加载成功: {model_path}")

        except Exception as e:
            print(f"❌ 模型加载失败: {e}")
            raise e

    # 处理帧序列-维度扩展
    def preprocess_sequence(self, keypoints_sequence):
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
        max_len = self.config["sequence_length"]
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

    # 绘制检测结果
    def draw_text_cn(self, frame, text, position, font_size, color_bgr):
        try:
            img_pil = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(img_pil)
            font = ImageFont.truetype(self.config["font_path"], font_size, encoding="utf-8")
            draw.text(position, text, font=font, fill=color_bgr[::-1])  # PIL颜色是RGB
            return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
        except Exception as e:
            print(f"绘制中文失败: {e}")
            # 降级方案：使用OpenCV绘制英文字符
            cv2.putText(frame, "Error: Font not found.", position, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            return frame

    def detect(self,frame):
        results = self.pose_model.track(frame, persist=True, verbose=False)
        annotated_frame = results[0].plot()
        persons_points = {}
        current_tracked_ids = []
        behaviors = {}
        if results[0].boxes and results[0].boxes.id is not None:
            track_ids = results[0].boxes.id.int().cpu().numpy()
            current_tracked_ids = list(track_ids)
            keypoints_data = results[0].keypoints.data
            boxes = results[0].boxes.xywh.cpu().numpy()

            for track_id, kpts, box in zip(track_ids, keypoints_data, boxes):
                # 解析所有检测到的人的关键点信息为字典格式，并提取左腕关键点坐标（手环佩戴位置）作为学生位置坐标
                keypoints_xy = kpts[:, :2].cpu().numpy()  # shape: (17, 2)
                # YOLO关键点顺序 (COCO格式):
                # 0: 鼻子, 1: 左眼, 2: 右眼, 3: 左耳, 4: 右耳
                # 5: 左肩, 6: 右肩, 7: 左肘, 8: 右肘, 9: 左腕, 10: 右腕
                # 11: 左髋, 12: 右髋, 13: 左膝, 14: 右膝, 15: 左踝, 16: 右踝
                persons_points[track_id] = keypoints_xy[9]
                # 如果出现新的检测对象，则添加进记录中
                if track_id not in self.tracked_persons:
                    self.tracked_persons[track_id] = {"keypoints_q": deque(maxlen=self.config["sequence_length"]),
                                                      "center": (0, 0),"action":'detecting'}

                self.tracked_persons[track_id]["keypoints_q"].append(kpts[:, :2].cpu().numpy())
                self.tracked_persons[track_id]["center"] = (int(box[0]), int(box[1]))
                # 实现窗口按步长滑动
                self.cnt += 1
                if len(self.tracked_persons[track_id]["keypoints_q"]) == self.config["sequence_length"] and self.cnt >= self.step:
                    processed_seq = self.preprocess_sequence(self.tracked_persons[track_id]["keypoints_q"])
                    input_tensor = torch.FloatTensor(processed_seq).unsqueeze(0).to(self.device)

                    with torch.no_grad():
                        output = self.action_model(input_tensor)
                        _, pred_idx = torch.max(output, 1)

                    self.tracked_persons[track_id]['action'] = self.idx_to_label.get(pred_idx.item(), "未知")
                    self.cnt = 0

        for track_id in list(self.tracked_persons.keys()):
            if track_id not in current_tracked_ids:
                del self.tracked_persons[track_id]

        # --- 可视化 ---
        for track_id, data in self.tracked_persons.items():
            x_center, y_center = data['center']
            action = self.tracked_persons[track_id]['action']
            behaviors[track_id] = action
            if action=='detecting':
                color_bgr = (255, 0, 0)  # 蓝色
            elif action=='focus' or action=='normal' or action=='handup':
                color_bgr = (0, 255, 0)  # 绿色
            else:
                color_bgr = (0, 0, 255)  # 红色
            alart_text = f"ID-{track_id} 动作:{self.behavior_dict[action]}"
            annotated_frame = self.draw_text_cn(annotated_frame, alart_text,
                                         (x_center - 70, y_center - 30),
                                         font_size=18, color_bgr=color_bgr)
        del results
        return annotated_frame,persons_points,behaviors
