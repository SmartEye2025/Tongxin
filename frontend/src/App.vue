<template>
  <VideoPlayer></VideoPlayer>
  <BehaviorChart></BehaviorChart>
</template>

<script setup>
import VideoPlayer from "./components/VideoPlayer.vue";
import BehaviorChart from "./components/BehaviorChart.vue";
</script>

<style>
:root {
  --primary-color: #4285F4;
  --secondary-color: #34A853;
  --warning-color: #FBBC05;
  --danger-color: #EA4335;
}

.v-application {
  font-family: 'Roboto', 'PingFang SC', 'Microsoft YaHei', sans-serif;
}

/* 自定义滚动条 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* 过渡动画 */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s;
}
.fade-enter, .fade-leave-to {
  opacity: 0;
}
</style>
