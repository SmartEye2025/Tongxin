from camera.mqtt_client import client
from camera.camera import Camera
from camera.speaker import Speaker
from camera.uwb import UWB

# 开启mqtt事件循环
client.loop_start()
