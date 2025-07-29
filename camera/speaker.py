import bluetooth
import pygame


class Speaker:
    def __init__(self, device_name='MH-M18', audio='media/remind_sample.mp3'):
        self.device = None
        self.device_name = device_name
        self.audio = audio
        self.connected = False
        self.socket = None  # 蓝牙Socket（如果需要数据传输）
        self.is_playing = False  # 播放状态跟踪
        self.student_id = None  # 记录当前正在提醒的学生的id

    def connect(self):
        """连接蓝牙设备并初始化音频"""
        if self.connected:
            print("已连接，请先断开")
            return

        try:
            # 1. 扫描设备
            print("正在扫描蓝牙设备...")
            devices = bluetooth.discover_devices(duration=5, lookup_names=True)
            if not devices:
                raise RuntimeError("未找到任何蓝牙设备")
            # 2. 匹配目标设备
            self.device = next(
                (addr for addr, name in devices if self.device_name in name),
                None
            )
            if not self.device:
                raise RuntimeError(f"未找到名称包含 '{self.device_name}' 的设备")

            print(f"找到设备: {self.device_name} ({self.device})")

            # 3. 初始化音频
            pygame.init()
            pygame.mixer.init()
            pygame.mixer.music.load(self.audio)
            self.connected = True
            print("连接成功！")

        except Exception as e:
            print(f"连接失败: {e}")
            self._cleanup()

    def disconnect(self):
        """断开连接并释放资源"""
        if not self.connected:
            print("未连接任何设备")
            return

        try:
            # 停止播放
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
                self.is_playing = False

            # 释放音频资源
            pygame.mixer.music.unload()
            pygame.mixer.quit()
            pygame.quit()

            # 关闭蓝牙Socket（如果已打开）
            if self.socket:
                self.socket.close()
                self.socket = None

            self.connected = False
            self.device = None
            print("已断开连接")

        except Exception as e:
            print(f"断开连接时出错: {e}")
            self._cleanup()

    def play(self,student_id, loop=False):
        if not self.connected:
            print("请先连接音响设备")
            return
        # 检查当前是否有正在提醒的学生
        if self.student_id:
            print(f"当前正在提醒其他学生：{self.student_id}")
            return
        try:
            if not self.is_playing:
                pygame.mixer.music.play(loops=-1 if loop else 0)  # loops=-1 表示无限循环
                if not loop:
                    self.student_id = None
                else:
                    self.is_playing = True
                    self.student_id = student_id
                print("播放中..." + "(循环模式)" if loop else "")
            else:
                print("已在播放中")

        except Exception as e:
            print(f"播放失败: {e}")
            self._cleanup()

    def pause(self,student_id):
        """暂停播放"""
        if not self.connected:
            print("请先连接设备")
            return

        # 检查当前是否有正在提醒的学生
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
        """完全停止播放（重置播放位置）"""
        if not self.connected:
            print("请先连接设备")
            return

        if self.is_playing or pygame.mixer.music.get_pos() > 0:
            pygame.mixer.music.stop()  # 停止并重置位置
            self.is_playing = False
            self.student_id = None
            print("播放已停止")
        else:
            print("当前没有在播放")

    def _cleanup(self):
        """内部方法：强制清理资源"""
        try:
            if pygame.get_init():
                pygame.mixer.music.stop()
                pygame.mixer.quit()
                pygame.quit()
            if self.socket:
                self.socket.close()
        except:
            pass
        finally:
            self.connected = False
            self.is_playing = False

    def __del__(self):
        """析构时自动清理"""
        self._cleanup()


speaker = Speaker()
speaker.connect()