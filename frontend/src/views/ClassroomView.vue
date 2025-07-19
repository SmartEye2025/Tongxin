<template>
  <div class="calibration-system">
    <!-- 标题和操作区 -->
    <div class="header">
      <h2>教室坐标标定系统</h2>
      <div class="controls">
        <v-btn color="primary" @click="saveCalibration">保存标定</v-btn>
        <v-btn color="secondary" @click="resetAll">重置</v-btn>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="content">
      <!-- 左侧：坐标输入表单 -->
      <div class="input-panel">
        <div class="base-station">
          <h3>定位基站坐标 (cm)</h3>
          <v-text-field v-model.number="baseStations.A.x" label="基站A X坐标" type="number"></v-text-field>
          <v-text-field v-model.number="baseStations.A.y" label="基站A Y坐标" type="number"></v-text-field>

          <v-text-field v-model.number="baseStations.B.x" label="基站B X坐标" type="number"></v-text-field>
          <v-text-field v-model.number="baseStations.B.y" label="基站B Y坐标" type="number"></v-text-field>

          <v-text-field v-model.number="baseStations.C.x" label="基站C X坐标" type="number"></v-text-field>
          <v-text-field v-model.number="baseStations.C.y" label="基站C Y坐标" type="number"></v-text-field>

          <v-text-field v-model.number="baseZ" label="基站共同Z坐标" type="number"></v-text-field>
        </div>

        <div class="servo-panel">
          <h3>舵机云台坐标 (cm)</h3>
          <v-text-field v-model.number="servoOrigin.x" label="云台原点 X坐标" type="number"></v-text-field>
          <v-text-field v-model.number="servoOrigin.y" label="云台原点 Y坐标" type="number"></v-text-field>
          <v-text-field v-model.number="servoOrigin.z" label="云台原点 Z坐标" type="number"></v-text-field>
        </div>
      </div>

      <!-- 右侧：坐标可视化 -->
      <div class="visualization">
        <h3>教室平面图 (比例尺: 1px = 1cm)</h3>
        <div class="classroom-map" ref="mapContainer">
          <!-- 基站标记 -->
          <div
            v-for="(station, id) in baseStations"
            :key="id"
            class="base-station-marker"
            :style="{
              left: `${station.x}px`,
              top: `${station.y}px`,
              backgroundColor: markerColors[id]
            }"
            :title="`基站${id} (${station.x},${station.y})`"
          >{{ id }}</div>

          <!-- 云台标记 -->
          <div
            class="servo-marker"
            :style="{
              left: `${servoOrigin.x}px`,
              top: `${servoOrigin.y}px`
            }"
            :title="`云台原点 (${servoOrigin.x},${servoOrigin.y})`"
          >云台</div>

          <!-- 坐标轴 -->
          <div class="axis x-axis"></div>
          <div class="axis y-axis"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref,onMounted } from 'vue';
import request from "@/utils/request.js";

// 基站坐标数据
const baseStations = ref({
    A: { x: 250, y: 0 },
    B: { x: 500, y: 500 },
    C: { x: 0, y: 500 }
});
// 基站共同Z坐标
const baseZ = ref(60)
// 舵机云台原点坐标
const servoOrigin = ref({ x: 250, y: 250, z: 280 });
// 标记颜色
const markerColors = {
  A: '#FF5252',
  B: '#4CAF50',
  C: '#2196F3'
};

// 保存标定数据
const saveCalibration = () => {
  const calibrationData = {
    class_id:'001',
    baseStations: baseStations.value,
    baseZ: baseZ.value,
    servoOrigin: servoOrigin.value,
  };
  request.post('/upload_calibration/',calibrationData).then(response => {
    if (response.success) console.log('标定数据已保存:', calibrationData);
  })
};

// 重置所有坐标
const resetAll = () => {
  baseStations.value = {
    A: { x: 250, y: 0 },
    B: { x: 500, y: 500 },
    C: { x: 0, y: 500 }
  };
  baseZ.value = 60;
  servoOrigin.value = { x: 250, y: 250, z: 280};
};

onMounted(() => {
  const markers = document.querySelectorAll('.base-station-marker, .servo-marker');
  request.get('/get_calibration/').then(response => {
    if (response.success) {
      console.log(response);
      baseStations.value = response.baseStations;
      baseZ.value = response.baseZ;
      servoOrigin.value = response.servoOrigin;
      markers.forEach(marker => {
        marker.addEventListener('mousedown', startDrag);
      });

      function startDrag(e) {
        const marker = e.target;
        const isBaseStation = marker.classList.contains('base-station-marker');
        const offsetX = e.clientX - marker.getBoundingClientRect().left;
        const offsetY = e.clientY - marker.getBoundingClientRect().top;

        function moveHandler(e) {
          const mapRect = document.querySelector('.classroom-map').getBoundingClientRect();
          let x = e.clientX - mapRect.left - offsetX;
          let y = e.clientY - mapRect.top - offsetY;

          // 边界检查
          x = Math.max(0, Math.min(x, mapRect.width));
          y = Math.max(0, Math.min(y, mapRect.height));

          marker.style.left = `${x}px`;
          marker.style.top = `${y}px`;

          // 更新数据
          if (isBaseStation) {
            const id = marker.textContent;
            baseStations.value[id].x = Math.round(x);
            baseStations.value[id].y = Math.round(y);
          } else {
            servoOrigin.value.x = Math.round(x);
            servoOrigin.value.y = Math.round(y);
          }
        }

        function endDrag() {
          document.removeEventListener('mousemove', moveHandler);
          document.removeEventListener('mouseup', endDrag);
        }

        document.addEventListener('mousemove', moveHandler);
        document.addEventListener('mouseup', endDrag);
      }
    }
  })
});
</script>

<style scoped>
.calibration-system {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.content {
  display: flex;
  gap: 30px;
}

.input-panel {
  flex: 1;
  background: #f5f5f5;
  padding: 20px;
  border-radius: 8px;
}

.visualization {
  flex: 2;
}

.classroom-map {
  position: relative;
  width: 800px;
  height: 800px;
  background-color: #f9f9f9;
  border: 1px solid #ddd;
  margin-top: 10px;
}

.base-station-marker, .servo-marker {
  position: absolute;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: bold;
  transform: translate(-50%, -50%);
  cursor: move;
  user-select: none;
}

.base-station-marker {
  box-shadow: 0 0 0 3px rgba(0,0,0,0.1);
}

.servo-marker {
  background-color: #9C27B0;
  width: 40px;
  height: 40px;
}

.axis {
  position: absolute;
  background-color: rgba(0,0,0,0.2);
}

.x-axis {
  bottom: 0;
  left: 0;
  width: 100%;
  height: 1px;
}

.y-axis {
  top: 0;
  left: 0;
  width: 1px;
  height: 100%;
}
</style>
