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

<script>
import { classStore } from "@/stores/classStore.js";
import { mapState } from 'pinia'

export default {
  name: "VideoPlayer",
  data() {
    return {
      isFullscreen: false,
      connectionStatus: "connecting",
      activeBlobUrl: null, // 跟踪当前Blob URL以便释放
      img: null, // 用于加载视频帧的Image对象
      originalSize: {
        width: 800,
        height: 450,
      },
      statusMessages: {
        connecting: "正在连接视频流...",
        connected: "实时连接中",
        disconnected: "连接已断开",
        error: "连接错误",
      },
      socket: null, // WebSocket 实例
    };
  },
  computed: {
      ...mapState(classStore, ['enableHotMap','enableAutoRemind','remindIntensity','remindStudentId']),
  },
  methods: {
    initWebSocket() {
      this.connectionStatus = "connecting";
      const canvas = this.$refs.videoCanvas;
      const ctx = canvas.getContext("2d");
      this.img = new Image();

      try {
        // this.socket = new WebSocket(`ws://192.168.1.2:8001/ws/video/`);
        this.socket = new WebSocket(`ws://localhost:8001/ws/video/`);

        this.socket.onopen = () => {
          this.connectionStatus = "connected";
        };

        this.socket.onmessage = async (event) => {
          if (event.data instanceof Blob) {
            // 释放之前创建的Blob URL
            if (this.activeBlobUrl) URL.revokeObjectURL(this.activeBlobUrl);
            this.activeBlobUrl = URL.createObjectURL(event.data);

            // 使用Promise确保图像加载完成
            await new Promise((resolve) => {
              this.img.onload = resolve;
              this.img.onerror = () => {
                console.error("帧加载失败");
                resolve();
              };
              this.img.src = this.activeBlobUrl;
            });

            // 双缓冲渲染
            requestAnimationFrame(() => {
              const ratio = Math.min(
                canvas.width / this.img.width,
                canvas.height / this.img.height
              );
              const drawWidth = this.img.width * ratio;
              const drawHeight = this.img.height * ratio;
              const offsetX = (canvas.width - drawWidth) / 2;
              const offsetY = (canvas.height - drawHeight) / 2;

              ctx.clearRect(0, 0, canvas.width, canvas.height);
              ctx.imageSmoothingQuality = "high";
              ctx.drawImage(this.img, offsetX, offsetY, drawWidth, drawHeight);
            });
          } else {
            // 文本数据：检测结果
            const { type, data } = JSON.parse(event.data);
            if (type === "detection") {
              classStore().setDetectResult(data);
            }
          }
        };

        this.socket.onclose = () => {
          this.connectionStatus = "disconnected";
        };

        this.socket.onerror = (error) => {
          console.error("WebSocket 错误:", error);
          this.connectionStatus = "error";
        };
      } catch (error) {
        console.error("初始化 WebSocket 失败:", error);
        this.connectionStatus = "error";
      }
    },
    toggleFullscreen() {
      if (!document.fullscreenElement) {
        this.$refs.playerContainer
          .requestFullscreen()
          .then(() => {
            this.isFullscreen = true;
            this.$refs.videoCanvas.width = window.innerWidth;
            this.$refs.videoCanvas.height = window.innerHeight;
          })
          .catch((err) => console.error("全屏错误:", err));
      } else {
        document
          .exitFullscreen()
          .then(() => {
            this.isFullscreen = false;
            this.$refs.videoCanvas.width = this.originalSize.width;
            this.$refs.videoCanvas.height = this.originalSize.height;
          })
          .catch((err) => console.error("退出全屏错误:", err));
      }
    },
  },
  watch:{
    // 监听变量变化
    enableHotMap(newVal) {
      if (this.connectionStatus === "connected"){
        this.socket.send(JSON.stringify({
          type: 'setting1',
          enableHotMap: newVal,
        }));
      }
    },
    enableAutoRemind(newVal) {
      if (this.connectionStatus === "connected"){
        this.socket.send(JSON.stringify({
          type: 'setting2',
          enableAutoRemind: newVal,
        }));
      }
    },
    remindStudentId(newVal) {
      if (this.connectionStatus === "connected"){
        console.log('发送提醒：',newVal);
        this.socket.send(JSON.stringify({
          type: 'control',
          studentList: newVal.value,
        }));
      }
    },
  },
  mounted() {
    // 初始化canvas尺寸
    this.$refs.videoCanvas.width = this.originalSize.width;
    this.$refs.videoCanvas.height = this.originalSize.height;
    this.initWebSocket();
  },
  beforeUnmount() {
    if (this.socket) {
      this.socket.close();
    }
    if (this.activeBlobUrl) {
      URL.revokeObjectURL(this.activeBlobUrl); // 清理Blob URL
    }
  },
};
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
