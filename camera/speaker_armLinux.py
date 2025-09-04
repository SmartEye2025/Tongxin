import os
import time
from bluepy import btle  # 替代标准 bluetooth 库
import pygame
import subprocess


class Speaker:
    def __init__(self, device_name='MH-M18', audio='media/remind_sample.mp3'):
        self.device = None
        self.device_name = device_name
        self.audio = audio
        self.connected = False
        self.peripheral = None  # 蓝牙设备对象
        self.is_playing = False
        self.student_id = None

        # Atlas 200I 音频配置
        os.environ['SDL_AUDIODRIVER'] = 'alsa'  # 使用ALSA音频驱动
        os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'  # 隐藏Pygame欢迎信息

    def connect(self):
        """连接蓝牙设备并初始化音频"""
        if self.connected:
            print("已连接，请先断开")
            return

        try:
            print("正在扫描蓝牙设备...")

            # 使用bluepy扫描设备
            scanner = btle.Scanner()
            devices = scanner.scan(5.0)  # 扫描5秒

            found = False
            for dev in devices:
                for (adtype, desc, value) in dev.getScanData():
                    if self.device_name in value:
                        self.device = dev.addr
                        found = True
                        break
                if found:
                    break

            if not found:
                raise RuntimeError(f"未找到名称包含 '{self.device_name}' 的设备")

            print(f"找到设备: {self.device_name} ({self.device})")

            # 初始化音频系统
            self._init_audio()

            # 连接蓝牙设备（如果需要数据传输）
            # self.peripheral = btle.Peripheral(self.device)

            self.connected = True
            print("连接成功！")

        except Exception as e:
            print(f"连接失败: {e}")
            self._cleanup()

    def _init_audio(self):
        """初始化音频系统"""
        # 检查音频设备
        result = subprocess.run(['aplay', '-l'], capture_output=True, text=True)
        if 'no soundcards found' in result.stderr.lower():
            raise RuntimeError("未检测到音频设备")

        # 初始化Pygame音频
        pygame.mixer.pre_init(
            frequency=44100,
            size=-16,
            channels=2,
            buffer=4096  # 较小的缓冲区减少延迟
        )
        pygame.init()
        pygame.mixer.init()

        # 加载音频文件前检查文件是否存在
        if not os.path.exists(self.audio):
            raise FileNotFoundError(f"音频文件 {self.audio} 不存在")

        pygame.mixer.music.load(self.audio)

    def disconnect(self):
        """断开连接并释放资源"""
        if not self.connected:
            print("未连接任何设备")
            return

        try:
            self.stop()

            # 释放音频资源
            if pygame.mixer.get_init():
                pygame.mixer.music.unload()
                pygame.mixer.quit()
                pygame.quit()

            # 断开蓝牙连接
            if self.peripheral:
                self.peripheral.disconnect()
                self.peripheral = None

            self.connected = False
            self.device = None
            print("已断开连接")

        except Exception as e:
            print(f"断开连接时出错: {e}")
            self._cleanup()

    def play(self, student_id, loop=False):
        """播放音频"""
        if not self.connected:
            print("请先连接音响设备")
            return

        if self.student_id:
            print(f"当前正在提醒其他学生：{self.student_id}")
            return

        try:
            if not self.is_playing:
                loops = -1 if loop else 0
                pygame.mixer.music.play(loops=loops)

                if loop:
                    self.is_playing = True
                    self.student_id = student_id
                else:
                    # 非循环模式下等待播放结束
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)

                print("播放中..." + "(循环模式)" if loop else "")
            else:
                print("已在播放中")

        except Exception as e:
            print(f"播放失败: {e}")
            self._cleanup()

    def pause(self, student_id):
        """暂停播放"""
        if not self.connected:
            print("请先连接设备")
            return

        if self.student_id:
            print(f"当前正在提醒其他学生：{self.student_id}")
            return

        try:
            if self.is_playing:
                pygame.mixer.music.pause()
                self.is_playing = False
                self.student_id = None
                print("已暂停")
            else:
                print("已处于暂停状态")

        except Exception as e:
            print(f"暂停失败: {e}")
            self._cleanup()

    def stop(self):
        """完全停止播放"""
        if not self.connected:
            print("请先连接设备")
            return

        if self.is_playing or pygame.mixer.music.get_pos() > 0:
            pygame.mixer.music.stop()
            self.is_playing = False
            self.student_id = None
            print("播放已停止")
        else:
            print("当前没有在播放")

    def _cleanup(self):
        """强制清理资源"""
        try:
            if pygame.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.quit()
                pygame.quit()
            if self.peripheral:
                self.peripheral.disconnect()
        except Exception:
            pass
        finally:
            self.connected = False
            self.is_playing = False

    def __del__(self):
        """析构时自动清理"""
        self._cleanup()

try:
    speaker = Speaker()
    speaker.connect()
except Exception as e:
    print('蓝牙连接错误', e)