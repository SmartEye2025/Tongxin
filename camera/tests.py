import cv2
import numpy as np
import ipywidgets as widgets
from IPython.display import display
import torch
import torchvision
from skvideo.io import vreader, FFmpegWriter
import IPython.display
from ais_bench.infer.interface import InferSession
import threading
import queue
from typing import List, Tuple, Optional
from asgiref.sync import sync_to_async

from HikSDKHelper import *
from threading import Thread

frame_queue = queue.Queue(maxsize=5)  # 限制队列长度避免内存堆积


# 解码回调函数
def DecCBFun(nPort, pBuf, nSize, pFrameInfo, nUser, nReserved2):
    # print(pFrameInfo.contents.nType)
    # 解码回调函数
    # if pFrameInfo.contents.nType == 3:
    # 解码YUV数据,YV12格式
    YUV = np.frombuffer(pBuf[:nSize], dtype=np.uint8)
    # width = pFrameInfo.contents.nWidth
    # height = pFrameInfo.contents.nHeight
    height, width = 720, 1280
    YUV = np.reshape(YUV, [height + height // 2, width])
    frame = cv2.cvtColor(YUV, cv2.COLOR_YUV2RGB_YV12)
    del YUV
    # 非阻塞放入队列，若满则丢弃旧帧
    if frame_queue.full():
        frame_queue.get_nowait()  # 快速丢弃旧帧
    frame_queue.put(frame)


# 码流回调函数
def real_data_callback(lPlayHandle, dwDataType, pBuffer, dwBufSize, pUser):
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


# 捕获视频流线程--海康SDK
def capture_thread():
    preview_info = NET_DVR_PREVIEWINFO()
    preview_info.hPlayWnd = 0
    preview_info.lChannel = 1  # 通道号
    preview_info.dwStreamType = 0  # 主码流
    preview_info.dwLinkMode = 0  # TCP
    # preview_info.dwLinkMode = 1  # UDP
    preview_info.bBlocked = 0  # 非阻塞取流
    # 设置回调函数回调获取实时流数据
    result = dev.hikSDK.NET_DVR_RealPlay_V40(dev.iUserID, byref(preview_info),
                                             funRealDataCallBack,
                                             None)
    if result < 0:
        print('Open preview fail, error code is: %d' % dev.hikSDK.NET_DVR_GetLastError())
        dev.stopPlay()


# ----------初始化海康摄像机----------
dev = devClass()
funRealDataCallBack = REALDATACALLBACK(real_data_callback)
funcDecCB = DECCBFUNWIN(DecCBFun)

dev.Init()
dev.LoginDev(ip=b'192.168.1.6', username=b"admin", pwd=b"SHENG666sheng")
# 启动线程
Thread(target=capture_thread, daemon=True).start()


# ---------------------------- 1. 图像预处理（Letterbox） ----------------------------
def preprocess_image(image, target_size=(384, 640), bgr2rgb=False):
    """
    将图像resize并填充为模型输入尺寸（保持宽高比）
    Args:
        img: 输入图像 (H, W, 3)
        target_size: 模型输入尺寸 (H, W)
    Returns:
        processed_image: 处理后的图像 (target_size)
        scale: 缩放比例 (scale_x, scale_y)
        padding: 填充像素 (top, left)
    """
    h, w = image.shape[:2]
    target_h, target_w = target_size

    # 计算缩放比例（保持宽高比）
    scale = min(target_h / h, target_w / w)
    new_h, new_w = int(h * scale), int(w * scale)

    # 缩放图像
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    # 计算填充位置（居中填充）
    top = (target_h - new_h) // 2
    bottom = target_h - new_h - top
    left = (target_w - new_w) // 2
    right = target_w - new_w - left

    # 填充灰边（BGR格式的114值）
    img = cv2.copyMakeBorder(
        resized,
        top, bottom, left, right,
        cv2.BORDER_CONSTANT,
        value=(114, 114, 114)
    )
    if bgr2rgb:
        img = img[:, :, ::-1]
    img = img.transpose(2, 0, 1)  # HWC2CHW
    img = np.ascontiguousarray(img, dtype=np.float32)
    return img, (scale, scale), (top, left)


# ---------------------------- 2. 非极大抑制后处理 ----------------------------
def nms(
        prediction,
        conf_thres=0.25,
        iou_thres=0.65,  # 提高IOU阈值使合并更严格
        kpt_conf_thres=0.4,
        max_det=100
):
    """
    终极版姿态NMS：
    1. 每个目标只保留1个最优检测框
    2. 支持多目标共存
    3. 严格防止重复检测
    """
    # 1. 输入处理
    print(prediction.shape)
    pred = prediction.squeeze(0).permute(1, 0)  # [5040,56]
    boxes = pred[:, :4]  # xywh
    conf = pred[:, 4]  # 置信度
    kpts = pred[:, 5:].view(-1, 17, 3)  # [5040,17,3]

    # 2. 双重过滤（置信度 + 关键点质量）
    kpts_mean_conf = kpts[..., 2].mean(dim=1)
    mask = (conf > conf_thres) & (kpts_mean_conf > kpt_conf_thres)
    boxes, conf, kpts = boxes[mask], conf[mask], kpts[mask]

    if boxes.shape[0] == 0:
        return torch.zeros((0, 6)), torch.zeros((0, 17, 3))

    # 3. 坐标转换+排序
    boxes = xywh2xyxy(boxes)
    sorted_idx = torch.argsort(conf, descending=True)
    boxes, conf, kpts = boxes[sorted_idx], conf[sorted_idx], kpts[sorted_idx]

    # 4. 关键改进：联合使用IOU和关键点距离
    keep = []
    remaining_mask = torch.ones(len(boxes), dtype=torch.bool)

    for i in range(len(boxes)):
        if not remaining_mask[i] or len(keep) >= max_det:
            continue

        keep.append(i)

        # 计算当前框与所有剩余框的相似度
        ious = box_iou(boxes[i:i + 1], boxes)[0]  # [N]
        kpt_dists = keypoint_distance(kpts[i], kpts)  # [N]

        # 标记需要抑制的检测（同一目标）
        suppress_mask = (ious > iou_thres) | (kpt_dists < 15)  # 联合条件
        remaining_mask &= ~suppress_mask

    # 5. 结果组装
    final_boxes = torch.cat([
        boxes[keep],
        conf[keep].unsqueeze(1),
        torch.zeros((len(keep), 1), device=boxes.device)  # 类别ID
    ], dim=1)

    return final_boxes, kpts[keep]


def keypoint_distance(kpts1, kpts2):
    """计算关键点加权欧氏距离矩阵"""
    # kpts1: [17,3], kpts2: [N,17,3]
    diff = kpts1[None, :, :2] - kpts2[:, :, :2]  # [N,17,2]
    weights = kpts1[None, :, 2] * kpts2[:, :, 2]  # [N,17]
    return torch.norm(diff * weights.unsqueeze(-1), dim=2).mean(dim=1)  # [N]


def xywh2xyxy(x):
    """Convert nx4 boxes from [x, y, w, h] to [x1, y1, x2, y2]"""
    y = x.clone() if isinstance(x, torch.Tensor) else np.copy(x)
    y[:, 0] = x[:, 0] - x[:, 2] / 2  # x1
    y[:, 1] = x[:, 1] - x[:, 3] / 2  # y1
    y[:, 2] = x[:, 0] + x[:, 2] / 2  # x2
    y[:, 3] = x[:, 1] + x[:, 3] / 2  # y2
    return y


def box_iou(box1, box2):
    """昇腾优化的IOU计算，支持批量"""
    # 获取交集坐标
    lt = torch.max(box1[:, None, :2], box2[:, :2])  # [N,M,2]
    rb = torch.min(box1[:, None, 2:], box2[:, 2:])  # [N,M,2]

    # 计算交集面积
    wh = (rb - lt).clamp(min=0)  # [N,M,2]
    inter = wh[:, :, 0] * wh[:, :, 1]  # [N,M]

    # 计算各自面积
    area1 = (box1[:, 2] - box1[:, 0]) * (box1[:, 3] - box1[:, 1])  # [N,]
    area2 = (box2[:, 2] - box2[:, 0]) * (box2[:, 3] - box2[:, 1])  # [M,]

    # 计算IOU
    iou = inter / (area1[:, None] + area2 - inter)
    return iou.squeeze(0)  # 移除多余的批次维度

# def ascend_nms_impl(boxes, scores, iou_thres):
#     """昇腾NPU加速的NMS实现"""
#     # 将数据转为NPU友好格式
#     boxes_np = boxes.cpu().numpy().astype(np.float16)
#     scores_np = scores.cpu().numpy().astype(np.float16)

#     # 使用昇腾ACL加速计算 (替代torchvision.ops.nms)
#     def acl_nms(boxes, scores, iou_threshold):
#         # 这里需要调用昇腾的ACL接口
#         # 实际部署时替换为:
#         # from acl.nms import nms
#         # return nms(boxes, scores, iou_threshold)
#         # 以下是模拟实现:
#         import numpy as np
#         from collections import deque
#         keep = []
#         order = np.argsort(scores)[::-1]
#         while order.size > 0:
#             i = order[0]
#             keep.append(i)
#             ious = bbox_overlaps_np(boxes[i:i+1], boxes[order[1:]])
#             inds = np.where(ious <= iou_threshold)[1]
#             order = order[inds + 1]
#         return np.array(keep)

#     keep = acl_nms(boxes_np, scores_np, iou_thres)
#     return torch.from_numpy(keep).to(boxes.device)

# def bbox_overlaps_np(boxes, query_boxes):
#     """NumPy实现的IOU计算，用于昇腾NPU"""
#     n = boxes.shape[0]
#     k = query_boxes.shape[0]
#     overlaps = np.zeros((n, k), dtype=np.float32)
#     for i in range(n):
#         box_area = (
#             (boxes[i, 2] - boxes[i, 0]) *
#             (boxes[i, 3] - boxes[i, 1])
#         )
#         for j in range(k):
#             iw = (
#                 min(boxes[i, 2], query_boxes[j, 2]) -
#                 max(boxes[i, 0], query_boxes[j, 0])
#             )
#             if iw > 0:
#                 ih = (
#                     min(boxes[i, 3], query_boxes[j, 3]) -
#                     max(boxes[i, 1], query_boxes[j, 1])
#                 )
#                 if ih > 0:
#                     ua = box_area + (
#                         (query_boxes[j, 2] - query_boxes[j, 0]) *
#                         (query_boxes[j, 3] - query_boxes[j, 1])
#                     ) - iw * ih
#                     overlaps[i, j] = iw * ih / ua
#     return overlaps


# ---------------------------- 3. 坐标反变换回原尺寸 ----------------------------
def postprocess_coords(boxes, keypoints, original_shape, scale, padding):
    """
    将坐标映射回原图尺寸
    Args:
        boxes: [N, 4] (xyxy格式，基于模型输入尺寸)
        keypoints: [N, 17, 3]
        original_shape: 原图尺寸 (H, W)
        scale: 预处理时的缩放比例 (scale_x, scale_y)
        padding: 预处理时的填充 (top, left)
    """
    # 去除填充影响并缩放
    boxes[:, [0, 2]] = (boxes[:, [0, 2]] - padding[1]) / scale[0]
    boxes[:, [1, 3]] = (boxes[:, [1, 3]] - padding[0]) / scale[1]
    keypoints[:, :, 0] = (keypoints[:, :, 0] - padding[1]) / scale[0]
    keypoints[:, :, 1] = (keypoints[:, :, 1] - padding[0]) / scale[1]

    # 确保坐标不越界
    h, w = original_shape[0], original_shape[1]
    boxes[:, :4] = np.clip(boxes[:,:4], 0, [w, h, w, h])  # 分别限制 x1, y1, x2, y2
    keypoints[:, :, :2] = np.clip(keypoints[:, :, :2], 0, [w, h])
    print(boxes.shape, keypoints.shape)
    return boxes, keypoints


# ---------------------------- 4. 绘制检测结果 ----------------------------
def plot_pose_results(
        image: np.ndarray,
        keypoints: np.ndarray,  # shape: (num_persons, num_keypoints, 3) - (x,y,conf)
        boxes: Optional[np.ndarray] = None,  # shape: (num_persons, 6) - (x1,y1,x2,y2,conf,cls)
        track_ids: Optional[List[int]] = None,
        skeleton: List[Tuple[int, int]] = [
            (15, 13), (13, 11), (16, 14), (14, 12),  # 腿部
            (11, 12), (5, 11), (6, 12),  # 躯干
            (5, 7), (7, 9), (6, 8), (8, 10),  # 手臂
            (5, 6), (1, 2), (0, 1), (0, 2),  # 头部
            (1, 3), (2, 4), (3, 5), (4, 6)  # 肩部连接
        ],  # COCO 17关键点完整连接关系
        kpt_radius: int = 5,
        skeleton_thickness: int = 2,
        box_thickness: int = 2,
        text_scale: float = 0.6,
        kpt_color_map: Optional[List[Tuple[int, int, int]]] = None,
        skeleton_color: Tuple[int, int, int] = (0, 255, 255)  # 骨骼默认黄色
) -> np.ndarray:
    """
    修正后的YOLOv11n-pose可视化函数

    参数:
        image: 原始BGR图像 (H,W,3)
        keypoints: 关键点数组 [N,17,3] (x,y,conf)
        boxes: 检测框 [N,4] (xyxy)
        track_ids: 跟踪ID列表
        skeleton: 骨骼连接关系
        kpt_radius: 关键点绘制半径
        skeleton_thickness: 骨骼线宽
        box_thickness: 框线宽
        text_scale: 文本大小
        kpt_color_map: 自定义关键点颜色表
        skeleton_color: 骨骼线统一颜色

    返回:
        可视化后的BGR图像
    """
    if kpt_color_map is None:
        # COCO 17关键点默认颜色 (BGR格式)
        kpt_color_map = [
            (255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0),
            (255, 0, 255), (0, 255, 255), (255, 128, 0), (128, 255, 0),
            (0, 255, 128), (128, 0, 255), (255, 0, 128), (0, 128, 255),
            (128, 128, 0), (128, 0, 128), (0, 128, 128), (64, 64, 64),
            (192, 192, 192)
        ]

    annotated_image = image

    # ========== 1. 绘制检测框和ID ==========
    if boxes is not None:
        for i, box in enumerate(boxes):
            x1, y1, x2, y2, conf, cls = map(int, box[:6])

            # 框颜色 (根据track_id生成唯一颜色或使用默认绿色)
            if track_ids is not None:
                color = (
                    hash(str(track_ids[i])) % 256,
                    hash(str(track_ids[i] + 1)) % 256,
                    hash(str(track_ids[i] + 2)) % 256
                )
            else:
                color = (0, 255, 0)  # 默认绿色

            # 画检测框
            cv2.rectangle(
                annotated_image,
                (x1, y1),
                (x2, y2),
                color,
                box_thickness
            )

            # 显示track_id
            if track_ids is not None:
                label = f"ID:{track_ids[i]}{conf}"
                (label_width, label_height), _ = cv2.getTextSize(
                    label, cv2.FONT_HERSHEY_SIMPLEX, text_scale, 1
                )
                cv2.rectangle(
                    annotated_image,
                    (x1, y1 - label_height - 5),
                    (x1 + label_width, y1),
                    color,
                    -1  # 填充矩形
                )
                cv2.putText(
                    annotated_image,
                    label,
                    (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    text_scale,
                    (0, 0, 0),  # 黑色文本
                    1
                )

    # ========== 2. 绘制骨骼连接 ==========
    for person_kpts in keypoints:
        # 先绘制骨骼连接线（确保在关键点下方）
        for (start_idx, end_idx) in skeleton:
            if start_idx >= len(person_kpts) or end_idx >= len(person_kpts):
                continue

            start_kpt = person_kpts[start_idx]
            end_kpt = person_kpts[end_idx]

            # 只绘制置信度>0.3的关键点连接
            if start_kpt[2] > 0.3 and end_kpt[2] > 0.3:
                start_pos = (int(start_kpt[0]), int(start_kpt[1]))
                end_pos = (int(end_kpt[0]), int(end_kpt[1]))
                cv2.line(
                    annotated_image,
                    start_pos,
                    end_pos,
                    skeleton_color,
                    skeleton_thickness
                )

    # ========== 3. 绘制关键点 ==========
    for person_kpts in keypoints:
        for kpt_id, kpt in enumerate(person_kpts):
            x, y, conf = kpt
            if conf < 0.3:  # 置信度阈值过滤
                continue

            center = (int(x), int(y))
            color = kpt_color_map[kpt_id % len(kpt_color_map)]

            # 画关键点（实心圆+黑色边框）
            cv2.circle(
                annotated_image,
                center,
                kpt_radius,
                color,
                -1  # 填充
            )
            cv2.circle(
                annotated_image,
                center,
                kpt_radius,
                (0, 0, 0),  # 黑色边框
                1
            )

    return annotated_image


def infer_frame(image, model, input_shape):
    h, w = image.shape[:2]
    # 数据预处理
    img, scale, padding = preprocess_image(image, input_shape)
    # 模型推理
    output = model.infer([img])[0]
    output = torch.tensor(output)
    # 非极大抑制
    boxes, keypoints = nms(output, conf_thres=0.4, iou_thres=0.45)
    # 将坐标映射回原图尺寸
    boxes, keypoints = postprocess_coords(
        boxes.cpu().numpy(),
        keypoints.cpu().numpy(),
        original_shape=(h, w),
        scale=scale,
        padding=padding
    )
    # 绘制检测结果
    annotated_frame = plot_pose_results(image, keypoints, boxes)
    return annotated_frame


def img2bytes(image):
    """将图片转换为字节码"""
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    return bytes(cv2.imencode('.jpg', image)[1])


def infer_camera(model, input_shape, original_shape):
    # rtsp_url = "rtsp://admin:SHENG666sheng@192.168.1.6:554/Streaming/Channels/101"
    # cap = cv2.VideoCapture(rtsp_url)
    # cap.set(cv2.CAP_PROP_BUFFERSIZE, 5)  # 减少缓冲区
    # cap.set(cv2.CAP_PROP_FPS, 30)  # 设置预期FPS
    # 初始化可视化对象
    image_widget = widgets.Image(format='jpeg', width=original_shape[1], height=original_shape[0])
    display(image_widget)
    while True:
        # 对摄像头每一帧进行推理和可视化
        # ret, img_frame = cap.read()
        # if ret:
        #     infer_frame(img_frame, model, input_shape)
        #     image_widget.value = img2bytes(img_frame)
        try:
            frame = frame_queue.get(timeout=1)
            infer_frame(frame, model, input_shape)
            image_widget.value = img2bytes(frame)
            del frame

        except queue.Empty:
            print("等待新帧...")
            continue


model_path = 'yolo11n-pose.om'
# 初始化推理模型
model = InferSession(0, model_path)
infer_camera(model, input_shape=[384, 640], original_shape=[720, 1280])