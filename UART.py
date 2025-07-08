# PC端
import serial
ser = serial.Serial('COM3', 115200)  # 根据实际端口修改
while True:
    data = ser.readline().decode().strip()
    print(data)  # 解析JSON或自定义格式

# # Atlas端
# import serial
# ser = serial.Serial('/dev/ttyS2', 115200, timeout=1)  # 对应UART2
#
# while True:
#     data = ser.readline().decode().strip()
#     if data.startswith("POS"):
#         _, tag_id, x, y = data.split(',')
#         print('tag_id:', tag_id, 'x:', x, 'y:', y)