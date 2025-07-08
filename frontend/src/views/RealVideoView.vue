<template>
  <div class="main-content">
    <VideoPlayer/>
    <BehaviorChart/>
  </div>
</template>

<script setup>
import VideoPlayer from "@/components/VideoPlayer.vue";
import BehaviorChart from "@/components/BehaviorChart.vue";
</script>

<style>
.main-content {
  flex: 1;
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}
</style>
