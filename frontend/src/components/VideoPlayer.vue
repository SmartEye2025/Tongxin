<template>
  <div class="video-player" :class="{ 'fullscreen': isFullscreen }" ref="playerContainer">
    <!-- 视频显示区域 -->
    <div class="video-container">
      <canvas ref="videoCanvas" class="video-display"></canvas>

      <!-- 连接状态指示器 -->
      <div class="status-overlay" :class="connectionStatus">
        <div class="spinner" v-if="connectionStatus === 'connecting'"></div>
        <span class="status-text">
          {{ statusMessages[connectionStatus] }}
        </span>
      </div>
    </div>

    <!-- 简洁的控制栏 -->
    <div class="control-bar">
      <button @click="toggleFullscreen" class="control-btn" title="全屏">
        <i class="icon-fullscreen"></i>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import {classroomStore} from "@/stores/classroomStore.js";

const playerContainer = ref(null);
const videoCanvas = ref(null);
const isFullscreen = ref(false);
const connectionStatus = ref('connecting');
const img = new Image();

// 原始尺寸设置
const originalSize = {
  width: 800,
  height: 450
};

const statusMessages = {
  connecting: '正在连接视频流...',
  connected: '实时连接中',
  disconnected: '连接已断开',
  error: '连接错误'
};

// WebSocket 连接
let socket = null;

const initWebSocket = () => {
  connectionStatus.value = 'connecting';
  const canvas = videoCanvas.value;
  const ctx = canvas.getContext('2d');

  try {
    socket = new WebSocket(`ws://localhost:8001/ws/video/`);

    socket.onopen = () => {
      connectionStatus.value = 'connected';
    };

    socket.onmessage = (event) => {
      img.src = 'data:image/jpeg;base64,' + event.data;
      classroomStore().setImg('data:image/jpeg;base64,' + event.data)
      // img.onload = () => ctx.drawImage(img, 0, 0, 640, 360);

      // 计算最佳缩放比例
      const ratio = Math.min(
          canvas.width / img.width,
          canvas.height / img.height
      );
      const drawWidth = img.width * ratio;
      const drawHeight = img.height * ratio;
      const offsetX = (canvas.width - drawWidth) / 2;
      const offsetY = (canvas.height - drawHeight) / 2;

      // 绘制帧
      // ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.imageSmoothingQuality = 'high';
      img.onload = () => ctx.drawImage(img, offsetX, offsetY, drawWidth, drawHeight);
    };

    socket.onclose = () => {
      connectionStatus.value = 'disconnected';
    };

    socket.onerror = (error) => {
      console.error('WebSocket 错误:', error);
      connectionStatus.value = 'error';
    };

  } catch (error) {
    console.error('初始化 WebSocket 失败:', error);
    connectionStatus.value = 'error';
  }
};

// 切换全屏
const toggleFullscreen = () => {
  if (!document.fullscreenElement) {
    playerContainer.value.requestFullscreen()
      .then(() => {
        isFullscreen.value = true;
        // 全屏时canvas尺寸自动调整
        videoCanvas.value.width = window.innerWidth;
        videoCanvas.value.height = window.innerHeight;
      })
      .catch(err => console.error('全屏错误:', err));
  } else {
    document.exitFullscreen()
      .then(() => {
        isFullscreen.value = false;
        // 恢复原始尺寸
        videoCanvas.value.width = originalSize.width;
        videoCanvas.value.height = originalSize.height;
      })
      .catch(err => console.error('退出全屏错误:', err));
  }
};

// 生命周期钩子
onMounted(() => {
  // 初始化canvas尺寸
  videoCanvas.value.width = originalSize.width;
  videoCanvas.value.height = originalSize.height;

  initWebSocket();
});

onUnmounted(() => {
  if (socket) {
    socket.close();
  }
});
</script>

<style scoped>
.video-player {
  position: relative;
  width: 800px;
  height: 450px;
  margin: 0 auto;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  background-color: #000;
  transition: all 0.3s ease;
}

.video-player.fullscreen {
  width: 100vw !important;
  height: 100vh !important;
  border-radius: 0;
}

.video-container {
  position: absolute;
  width: 100%;
  height: 100%;
  background-color: #111;
}

.video-display {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.status-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background-color: rgba(0, 0, 0, 0.5);
  color: white;
  transition: opacity 0.3s ease;
}

.status-overlay.connected {
  opacity: 0;
  pointer-events: none;
}

.status-overlay:hover:not(.connected) {
  background-color: rgba(0, 0, 0, 0.7);
}

.status-text {
  margin-top: 12px;
  font-size: 16px;
  font-weight: 500;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid rgba(255, 255, 255, 0.1);
  border-radius: 50%;
  border-top-color: #42b983;
  animation: spin 1s linear infinite;
}

.control-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.7), transparent);
  color: white;
  opacity: 0;
  transition: opacity 0.3s ease;
}

.video-player:hover .control-bar {
  opacity: 1;
}

.control-btn {
  background: none;
  border: none;
  color: white;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.control-btn:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.icon-fullscreen {
  display: inline-block;
  width: 20px;
  height: 20px;
  background: currentColor;
  mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z'/%3E%3C/svg%3E") no-repeat center;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* 响应式调整 */
@media (max-width: 700px) {
  .video-player {
    width: 100%;
    height: calc(100vw * 9 / 16); /* 保持16:9比例 */
  }
}
</style>
