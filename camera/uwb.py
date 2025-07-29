from threading import Thread
import queue
import serial


location_queue = queue.Queue(maxsize=10)

class UWB:
    def __init__(self):
        try:
            # ------ 初始化串口 ------
            self.ser = serial.Serial('COM5', baudrate=115200, timeout=1)
            Thread(target=self.serial_thread, daemon=True).start()
            print('串口进程已启动')

        except Exception as e:
            print('串口启动失败:',e)

    def __del__(self):
        # 关闭串口
        if hasattr(self, 'ser') and self.ser and self.ser.is_open:
            self.ser.close()
            print("串口已关闭")

    # 读取串口数据线程
    def serial_thread(self):
        while True:  # 使用标志位控制循环
            if self.ser.in_waiting > 0:
                raw_data = self.ser.read(29)  # 读取足够长的数据（至少29字节）
                if len(raw_data) >= 29:
                    try:
                        # 解析定位标签编号
                        id = (raw_data[3] << 8) | raw_data[4]
                        # 解析 x, y, z（假设数据从第7字节开始，索引6~11）
                        x = (raw_data[7] << 8) | raw_data[8]
                        y = (raw_data[9] << 8) | raw_data[10]
                        z = (raw_data[11] << 8) | raw_data[12]
                        # 转换为有符号 Int16（处理负数）
                        x = x if x < 32768 else x - 65536
                        y = y if y < 32768 else y - 65536
                        z = z if z < 32768 else z - 65536
                        # print(f"id:{id},x:{x}, y:{y}, z:{z}")
                        # 非阻塞传递结果
                        if location_queue.full():
                            old_data = location_queue.get()
                            del old_data  # 显示释放内存
                        location_queue.put([id, x, y, z])
                    except Exception as e:
                        print("解析错误:", e)

uwb = UWB()