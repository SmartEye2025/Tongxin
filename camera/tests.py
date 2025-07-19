from camera.mqtt_client import client
import json
import math
import time
from threading import Thread
import numpy as np


class OmnidirectionalGimbal:
    def __init__(self, gimbal_pos,base_z, pan_range=(0, 180), tilt_range=(0, 180)):
        """
        全向云台控制器
        参数：
            gimbal_pos_cm : (x,y,z) 云台安装位置（厘米）
            pan_range : (min, max) 水平舵机机械限位（度）
            tilt_range : (min, max) 俯仰舵机机械限位（度）
        """
        # 初始化核心参数
        self.g_pos = np.array(gimbal_pos, dtype=float)
        self.base_z = base_z
        self.pan_range = pan_range
        self.tilt_range = tilt_range

        # 运动控制参数
        self.backlash_comp = 2  # 齿轮间隙补偿值（度）
        self.pan_comp = 0  # 水平轴当前补偿值
        self.tilt_comp = 0  # 俯仰轴当前补偿值

        # 当前状态变量
        self.current_pan = 90  # 当前水平角（度）
        self.current_tilt = 90  # 当前俯仰角（度）
        self.last_pan = 90  # 上次水平角（度）
        self.last_tilt = 90  # 上次俯仰角（度）
        self.hemisphere = "front"  # 当前半球模式

        # 安全参数
        self.min_distance = 20  # 最小有效距离（cm）
        self.max_current = 1.5  # 最大允许电流（A）
        self.watchdog_running = True

        # 启动看门狗线程
        Thread(target=self._watchdog, daemon=True).start()

        # 预计算常用位置
        self.kinematic_cache = {}
        self._precompute_kinematics()

    def _precompute_kinematics(self):
        """预计算教室网格点的运动学参数"""
        grid_size = 100  # cm
        x_range = range(0, 1001, grid_size)
        y_range = range(0, 801, grid_size)
        z = self.g_pos[2]-self.base_z

        for x in x_range:
            for y in y_range:
                key = (x, y, z)
                self.kinematic_cache[key] = self._calculate_angles((
                    x-self.g_pos[0],
                    y-self.g_pos[1],
                    self.g_pos[2]-z,
                ))

    def _calculate_angles(self, delta_cm):
        """核心运动学计算（相对坐标）"""
        dx, dy, dz = delta_cm
        # 计算原始pan角度（数学坐标系：0°为正右方，调整为：0°为正左方）
        pan_raw = (math.degrees(math.atan2(dy, dx)) - 90) % 360
        # 计算原始tilt角度（数学坐标系：0°为水平，调整为：90°为正下方）
        distance_xy = math.sqrt(dx ** 2 + dy ** 2)
        tilt_angle = 90 - math.degrees(math.atan2(distance_xy, dz))

        # 处理水平旋转超过180°的情况
        if pan_raw > 180:
            pan_angle = pan_raw - 180  # 水平舵机实际旋转角度（取余）
            tilt_angle = 180 - tilt_angle  # 竖直舵机镜像翻转
            hemisphere = "rear"
        else:
            pan_angle = pan_raw
            tilt_angle = tilt_angle
            hemisphere = "front"
        return pan_angle, tilt_angle, hemisphere

    def point_at(self, target_pos):
        """
        计算目标位置对应的舵机角度

        参数：
            target_pos : (x,y,z) 目标全局坐标（厘米）
        返回：
            (pan_angle, tilt_angle, hemisphere) 角度和半球模式
        """
        # 坐标系转化
        delta = (
            target_pos[0] - self.g_pos[0],
            target_pos[1] - self.g_pos[1],
            self.g_pos[2] - target_pos[2],
        )

        # 检查目标有效性
        if delta[2] < 0:
            raise ValueError("Target above gimbal!")
        if np.linalg.norm(delta) < self.min_distance:
            raise ValueError("Target too close!")

        # 优先使用缓存计算结果
        rounded_pos = tuple(round(p / 100) * 100 for p in target_pos)
        if rounded_pos in self.kinematic_cache:
            pan, tilt, hem = self.kinematic_cache[rounded_pos]
        else:
            pan, tilt, hem = self._calculate_angles(delta)

        # 应用机械约束
        pan = np.clip(pan, *self.pan_range)
        tilt = np.clip(tilt, *self.tilt_range)

        return pan, tilt, hem

    def normal_move(self,target_pan, target_tilt,target_hem=None,time_sleep=0.1):
        # 正常移动，一步到位式
        # 发送指令
        self._send_angles(target_pan, target_tilt)
        # 更新状态
        self.last_pan, self.last_tilt = self.current_pan, self.current_tilt
        self.current_pan, self.current_tilt = target_pan, target_tilt
        self.hemisphere = target_hem
        time.sleep(time_sleep)

    def smooth_move(self, target_pan, target_tilt, target_hem=None, speed=None):
        """
        平滑移动到目标位置

        参数：
            target_pan : 目标水平角（度）
            target_tilt : 目标俯仰角（度）
            target_hem : 目标半球模式（可选）
            speed : 最大运动速度（度/秒，可选）
        """
        target_hem = target_hem or self.hemisphere

        # 半球切换时的特殊处理
        if target_hem != self.hemisphere:
            # self._transition_hemisphere(target_pan, target_tilt, target_hem, speed)
            self.normal_move(target_pan, target_tilt, target_hem)
            return

        # 正常移动
        while not self._reach_target(target_pan, target_tilt):
            # 动态速度控制
            step_speed = speed if speed is not None else self._adaptive_speed(target_pan, target_tilt)
            step = step_speed * 0.05  # 假设20Hz控制频率

            # 更新角度（带运动记录）
            new_pan = self.current_pan + np.clip(target_pan - self.current_pan, -step, step)
            new_tilt = self.current_tilt + np.clip(target_tilt - self.current_tilt, -step, step)

            # 应用间隙补偿
            comp_pan, comp_tilt = self._add_backlash_compensation(new_pan, new_tilt)

            # 更新状态
            self.last_pan, self.last_tilt = self.current_pan, self.current_tilt
            self.current_pan, self.current_tilt = new_pan, new_tilt

            # 发送指令
            self._send_angles(comp_pan, comp_tilt)
            time.sleep(0.05)

    # def _transition_hemisphere(self, target_pan, target_tilt, target_hem, speed=None):
    #     """半球切换过渡处理"""
    #     # 默认速度策略
    #     lift_speed = speed if speed is not None else 30
    #     rotate_speed = speed if speed is not None else 60
    #     descend_speed = speed if speed is not None else 20
    #
    #     # 第一阶段：抬升俯仰角
    #     self.smooth_move(self.current_pan, 150, speed=lift_speed)
    #
    #     # 第二阶段：快速转向
    #     self.smooth_move(target_pan, 150, speed=rotate_speed)
    #
    #     # 第三阶段：降下俯仰角
    #     self.smooth_move(target_pan, target_tilt, speed=descend_speed)

    def _adaptive_speed(self, target_pan, target_tilt):
        """动态速度调整"""
        pan_diff = abs(target_pan - self.current_pan)
        tilt_diff = abs(target_tilt - self.current_tilt)

        if max(pan_diff, tilt_diff) > 90:
            return 25  # 快速移动
        elif max(pan_diff, tilt_diff) > 30:
            return 15
        else:
            return 5  # 精细调整

    def _add_backlash_compensation(self, new_pan, new_tilt):
        """齿轮间隙补偿"""
        # 检测方向变化
        if abs(new_pan - self.last_pan) > 5:
            self.pan_comp = self.backlash_comp if new_pan > self.last_pan else -self.backlash_comp
        if abs(new_tilt - self.last_tilt) > 5:
            self.tilt_comp = self.backlash_comp if new_tilt > self.last_tilt else -self.backlash_comp

        return new_pan + self.pan_comp, new_tilt + self.tilt_comp

    def _reach_target(self, target_pan, target_tilt, tolerance=0.5):
        """检查是否到达目标"""
        return (abs(self.current_pan - target_pan) < tolerance and
                abs(self.current_tilt - target_tilt) < tolerance)

    def _send_angles(self, pan, tilt):
        client.publish(
            "001",
            payload=json.dumps({
                "panAngle": pan,
                "tiltAngle": tilt
            })
        )

    def _watchdog(self):
        """硬件保护看门狗"""
        while self.watchdog_running:
            # current = get_current()  # 需硬件实现
            # if current > self.max_current:
            #     self.emergency_stop()
            time.sleep(0.1)

    def emergency_stop(self):
        """紧急停止"""
        self.watchdog_running = False
        print("EMERGENCY STOP ACTIVATED!")
        # 硬件紧急停止代码


def main():
    client.loop_start()
    # 初始化云台（安装在教室(250,250,280)cm位置）
    gimbal = OmnidirectionalGimbal(gimbal_pos=(250, 250, 280))
    # # 直线跟踪测试点
    # test_points = [
    #     (50, 250, 60),
    #     (250, 250, 60),
    #     (450, 250, 60),
    #     (250, 250, 60),
    # ]
    # 环形跟踪测试点
    test_points = [
        (250, 0, 60),
        (125, 80, 60),
        (0, 250, 60),
        (125, 420, 60),
        (250, 500, 60),
        (375, 420, 60),
        (500, 250, 60),
        (375, 80, 60),
    ]
    idx = 0
    while True:
        try:
            pan, tilt, hem = gimbal.point_at(test_points[idx])
            print(f"PAN={pan:.1f}°, TILT={tilt:.1f}°, {hem} hemisphere")
            # gimbal.smooth_move(pan, tilt, hem)
            gimbal.normal_move(pan, tilt, hem, 0.4)
            idx = (idx+1)%len(test_points)
        except ValueError as e:
            print(f"Cannot reach: {str(e)}")

main()