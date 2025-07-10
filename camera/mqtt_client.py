import json
import paho.mqtt.client as mqtt

MQTT_HOST = '43.138.252.29'
MQTT_PORT = 1883

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print('Connected successfully')
        client.subscribe('001')  # 订阅主题
    else:
        print('Bad connection. Code:', rc)

def on_message(client, userdata, msg):
    payload = json.loads(msg.payload)
    print(f"Received message on topic: {msg.topic} with payload: {payload['id']}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_HOST, MQTT_PORT, 60)
# 启用自动重连（延迟 1~5 秒）
client.reconnect_delay_set(min_delay=1, max_delay=5)