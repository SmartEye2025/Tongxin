import cv2
import numpy as np
from scipy.optimize import linear_sum_assignment

#--------------------实现监控摄像头图像坐标系与UWB定位物理坐标系的对齐-------------
# 标定点：4个已知位置的标记点（图像坐标⇄物理坐标）
img_pts = np.array([[320,240], [640,240], [640,480], [320,480]], dtype=np.float32)
uwb_pts = np.array([[0,0], [5,0], [5,3], [0,3]], dtype=np.float32)  # 单位：米

# 计算单应性矩阵
H, _ = cv2.findHomography(img_pts, uwb_pts)

# 应用变换：将图像坐标转为物理坐标
def image_to_world(u, v):
    uv = np.array([[u, v]], dtype=np.float32).reshape(-1,1,2)
    xy = cv2.perspectiveTransform(uv, H)
    return xy[0][0]  # 返回[x,y]

# 匈牙利算法，匹配摄像头检测的目标对应哪个UWB标签
def match_targets(visual_positions, uwb_positions):
    """
    输入:
        visual_positions: 视觉检测的N个坐标 [[x1,y1],...]
        uwb_positions: UWB系统的M个坐标 [[x2,y2],...] (M≥N)
    输出:
        matches: 匹配索引对 [(vis_idx, uwb_idx), ...]
    """
    # 构建代价矩阵（欧氏距离）
    cost_matrix = np.zeros((len(visual_positions), len(uwb_positions)))
    for i, v_pos in enumerate(visual_positions):
        for j, u_pos in enumerate(uwb_positions):
            cost_matrix[i, j] = np.linalg.norm(v_pos - u_pos)

    # 匈牙利算法求解
    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    return list(zip(row_ind, col_ind))


def fuse_coordinates(visual_detections, uwb_data):
    # 步骤1：图像坐标→物理坐标
    visual_positions = [image_to_world(u, v) for u, v, _ in visual_detections]

    # 步骤2：数据关联
    uwb_positions = list(uwb_data.values())
    matches = match_targets(visual_positions, uwb_positions)

    # 步骤3：生成最终输出
    results = []
    for vis_idx, uwb_idx in matches:
        tag_id = list(uwb_data.keys())[uwb_idx]
        behavior = visual_detections[vis_idx][2]  # 举手/站立
        results.append({
            "tag_id": tag_id,
            "x": uwb_positions[uwb_idx][0],
            "y": uwb_positions[uwb_idx][1],
            "behavior": behavior
        })
    return results