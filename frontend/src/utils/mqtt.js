import mqtt from 'mqtt';

// MQTT 连接配置
const MQTT_OPTIONS = {
  host: '43.138.252.29', // MQTT 服务器地址（可以是 IP 或域名）
  port: 1883,            // WebSocket 端口（默认 8083）
  protocol: 'mqtt',        // 使用 WebSocket 协议
  clientId: `mqtt_${Math.random().toString(16).slice(2, 8)}`, // 随机客户端 ID
  username: '',          // 用户名（如果需要）
  password: '',          // 密码（如果需要）
  clean: true,           // 清除会话
  reconnectPeriod: 1000, // 自动重连间隔（ms）
};

let mqttClient = null;

// 连接 MQTT 服务器
export function connectMqtt(onConnect, onMessage, onError) {
  if (mqttClient && mqttClient.connected) {
    console.log('MQTT 已连接');
    return;
  }

  mqttClient = mqtt.connect(MQTT_OPTIONS);

  // 连接成功回调
  mqttClient.on('connect', () => {
    console.log('MQTT 连接成功');
    if (onConnect) onConnect(mqttClient);
  });

  // 接收消息回调
  mqttClient.on('message', (topic, message) => {
    console.log(`收到消息: ${topic} => ${message.toString()}`);
    if (onMessage) onMessage(topic, message.toString());
  });

  // 错误回调
  mqttClient.on('error', (err) => {
    console.error('MQTT 连接错误:', err);
    if (onError) onError(err);
  });

  // 关闭回调
  mqttClient.on('close', () => {
    console.log('MQTT 连接关闭');
  });
}

// 订阅主题
export function subscribeTopic(topic, qos = 0) {
  if (mqttClient && mqttClient.connected) {
    mqttClient.subscribe(topic, { qos }, (err) => {
      if (err) {
        console.error('订阅失败:', err);
      } else {
        console.log(`订阅成功: ${topic}`);
      }
    });
  } else {
    console.error('MQTT 未连接');
  }
}

// 发布消息
export function publishMessage(topic, message, qos = 0) {
  if (mqttClient && mqttClient.connected) {
    mqttClient.publish(topic, message, { qos }, (err) => {
      if (err) {
        console.error('发送失败:', err);
      } else {
        console.log(`发送成功: ${topic} => ${message}`);
      }
    });
  } else {
    console.error('MQTT 未连接');
  }
}

// 断开连接
export function disconnectMqtt() {
  if (mqttClient && mqttClient.connected) {
    mqttClient.end();
    mqttClient = null;
    console.log('MQTT 已断开');
  }
}
