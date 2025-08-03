import os
import time
import queue
import serial
from threading import Thread, Event


# 全局数据队列
location_queue = queue.Queue(maxsize=10)


class UWB:
    def __init__(self, port='/dev/ttyAMA0', baudrate=115200):
        """
        初始化UWB模块
        :param port: 串口设备路径 (Atlas 200I常用: /dev/ttyAMA0, /dev/ttyUSB0)
        :param baudrate: 波特率
        """
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self._stop_event = Event()
        self._thread = None

        # 检查串口设备是否存在
        if not os.path.exists(self.port):
            print(f"串口设备 {self.port} 不存在")
            raise FileNotFoundError(f"串口设备 {self.port} 不存在")

        try:
            # 初始化串口 (Linux特定配置)
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False
            )

            # 启动读取线程
            self._thread = Thread(target=self.serial_thread, daemon=True)
            self._thread.start()

            print(f"串口 {self.port} 初始化成功，波特率 {self.baudrate}")

        except Exception as e:
            print(f"串口初始化失败: {str(e)}")
            self._cleanup()
            raise

    def _cleanup(self):
        """清理资源"""
        self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
                print("串口已关闭")
            except Exception as e:
                print(f"关闭串口时出错: {str(e)}")

    def __del__(self):
        """析构函数"""
        self._cleanup()

    def serial_thread(self):
        """串口数据读取线程"""
        print("串口读取线程启动")

        while not self._stop_event.is_set():
            try:
                if self.ser.in_waiting > 0:
                    raw_data = self.ser.read(29)  # 读取固定长度数据

                    if len(raw_data) >= 29:
                        # 解析数据
                        try:
                            tag_id = (raw_data[3] << 8) | raw_data[4]
                            x = (raw_data[7] << 8) | raw_data[8]
                            y = (raw_data[9] << 8) | raw_data[10]
                            z = (raw_data[11] << 8) | raw_data[12]

                            # 转换为有符号Int16
                            x = x if x < 32768 else x - 65536
                            y = y if y < 32768 else y - 65536
                            z = z if z < 32768 else z - 65536

                            # 放入队列
                            if location_queue.full():
                                location_queue.get_nowait()

                            location_queue.put({
                                'id': tag_id,
                                'x': x,
                                'y': y,
                                'z': z,
                                'timestamp': time.time()
                            })

                            # logger.debug(f"收到数据: ID={tag_id}, X={x}, Y={y}, Z={z}")

                        except Exception as parse_error:
                            print(f"数据解析错误: {str(parse_error)}")
                            print(f"原始数据: {raw_data.hex()}")

                # 短暂休眠减少CPU占用
                time.sleep(0.01)

            except serial.SerialException as se:
                print(f"串口通信错误: {str(se)}")
                self._cleanup()
                break
            except Exception as e:
                print(f"线程运行错误: {str(e)}")
                self._cleanup()
                break

        print("串口读取线程退出")

try:
    uwb = UWB()
except Exception as e:
    print('串口启动错误',e)