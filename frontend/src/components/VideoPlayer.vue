<template>
  <div class="video-container">
    <div class="video-wrapper">
      <img :src="videoSrc" alt="实时视频流" />
      <canvas ref="canvasElement" class="overlay-canvas"></canvas>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const videoSrc = ref('');
const ws = new WebSocket('ws://localhost:8000/ws/video/');

ws.onmessage = (event) => {
  videoSrc.value = `data:image/jpeg;base64,${event.data}`;
};
</script>

<style scoped>
.video-container {
  position: relative;
  max-width: 800px;
  margin: 0 auto;
}

.video-wrapper {
  position: relative;
}

.overlay-canvas {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
}

img {
  width: 100%;
  height: auto;
  display: block;
}

.controls {
  margin-top: 16px;
  text-align: center;
}
</style>
