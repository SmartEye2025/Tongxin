<template>
  <div class="calibration-tool">
    <!-- 教室平面图 -->
    <div class="image-container" @click="handleImageClick">
      <img ref="classroomImg" :src="imgSrc" alt="教室平面图">
      <canvas ref="gridCanvas" class="overlay-canvas"></canvas>
      <!-- 标定点标记 -->
      <div v-for="(point, index) in calibrationPoints" :key="index"
           class="calibration-point"
           :style="{ left: `${point.imgX}px`, top: `${point.imgY}px` }">
        {{ index + 1 }}
      </div>
    </div>

    <!-- 坐标输入表单 -->
    <div class="coordinate-form">
      <h3 v-if="calibrationPoints.length==0">请在图中标定坐标点</h3>
      <div v-for="(point, index) in calibrationPoints" :key="index" class="point-input">
        <div style="display: flex">
          <h3>标定点 {{ index + 1 }}</h3>
          <button @click="removePoint(index)" class="delete-btn">×</button>
        </div>
        <div>
          <label style="width: auto">像素坐标: ({{ point.imgX.toFixed(2) }}, {{ point.imgY.toFixed(2) }})</label>
        </div>
        <div style="display: flex">
           <div>
            <label style="width: auto">物理X:</label>
            <input class="input-coor" v-model.number="point.physicalX" type="number" step="0.01">
          </div>
          <div>
            <label style="width: auto">物理Y:</label>
            <input class="input-coor" v-model.number="point.physicalY" type="number" step="0.01">
          </div>
        </div>
      </div>

      <!-- 计算变换矩阵 -->
      <button @click="computeHomography" :disabled="calibrationPoints.length < 4">
        计算变换矩阵 (至少需要4个点)
      </button>

<!--      &lt;!&ndash; 结果显示 &ndash;&gt;-->
<!--      <div v-if="H" class="result">-->
<!--        <h3>单应性矩阵 H:</h3>-->
<!--        <pre>{{ formattedMatrix }}</pre>-->
<!--        <button @click="copyMatrix">复制矩阵</button>-->
<!--      </div>-->
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue';
import { matrix, multiply,lusolve, inv } from 'mathjs';
import request from "@/utils/request.js";

// 标定点数据
const calibrationPoints = ref([]);
const H = ref(null);
const Hinv = ref(null);
const classroomImg = ref(null);
const imgSrc = ref('/src/assets/classroom.jpg');
// 绘制网格
const showGrid = ref(false);
const gridCanvas = ref(null);

// 点击图像获取像素坐标
const handleImageClick = (event) => {
  if (calibrationPoints.value.length >= 10) return; // 限制最大标定点数

  const rect = classroomImg.value.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;

  calibrationPoints.value.push({
    imgX: x,
    imgY: y,
    physicalX: 0,
    physicalY: 0
  });
};
// 删除标定点
const removePoint = (index) => {
  calibrationPoints.value.splice(index, 1);
  H.value = null; // 清空已计算的矩阵
  Hinv.value = null;
};

/**
 * 计算从像素坐标到物理坐标的变换矩阵
 * @param {Array} pixelPoints 像素坐标点数组 [[x1,y1], [x2,y2], ...] (至少4个点)
 * @param {Array} worldPoints 物理坐标点数组 [[X1,Y1], [X2,Y2], ...] (至少4个点)
 */
const computeHomography=() =>{
  if (calibrationPoints.value.length < 4) return;
  const pixelPoints = calibrationPoints.value.map(p => [p.imgX, p.imgY]);
  const worldPoints = calibrationPoints.value.map(p => [p.physicalX, p.physicalY]);

  // 构建矩阵A
  let A = [];
  let b = [];
  for (let i = 0; i < 4; i++) {
      const [x, y] = pixelPoints[i];
      const [X, Y] = worldPoints[i];
      A.push([x, y, 1, 0, 0, 0, -x*X, -y*X]);
      A.push([0, 0, 0, x, y, 1, -x*Y, -y*Y]);
      b.push(X);
      b.push(Y);
  }

  // 使用math.js解线性方程组 A * h = b
  const h = lusolve(A, b).flat();

  // 构建3x3单应性矩阵
  H.value = matrix([
      [h[0], h[1], h[2]],
      [h[3], h[4], h[5]],
      [h[6], h[7], 1]
  ]);

  // 计算逆矩阵
  Hinv.value = inv(H.value);
  H.value.toArray();
  Hinv.value.toArray();
  showGrid.value = true;
  // 上传后端
  uploadH();
}

// /**
//  * 从像素坐标转换到物理坐标
//  * @param {number} X 像素x坐标
//  * @param {number} Y 像素y坐标
//  * @returns {Array} 物理坐标 [X, Y]
//  */
// const pixelToWorld=(X, Y)=> {
//     if (!H.value) throw new Error("请先计算单应性矩阵");
//
//     const pixelVec = matrix([[X], [Y], [1]]);
//     const worldVec = multiply(H.value, pixelVec);
//
//     // 转换为非齐次坐标
//     const w = worldVec.get([2, 0]);
//     return [
//         worldVec.get([0, 0]) / w,
//         worldVec.get([1, 0]) / w
//     ];
// }

/**
 * 从物理坐标转换到像素坐标
 * @param {number} X 物理X坐标
 * @param {number} Y 物理Y坐标
 * @returns {Array} 像素坐标 [x, y]
 */
const worldToPixel=(X, Y)=> {
    if (!Hinv.value) throw new Error("请先计算单应性矩阵");

    const worldVec = matrix([[X], [Y], [1]]);
    const pixelVec = multiply(Hinv.value, worldVec);

    // 转换为非齐次坐标
    const w = pixelVec.get([2, 0]);
    return [
        pixelVec.get([0, 0]) / w,
        pixelVec.get([1, 0]) / w
    ];
}

// 绘制网格
const drawGrid = () => {
  if (!Hinv.value || !gridCanvas.value) return;
  const ctx = gridCanvas.value.getContext('2d');
  const canvasWidth = gridCanvas.value.width;
  const canvasHeight = gridCanvas.value.height;
  ctx.clearRect(0, 0, canvasWidth, canvasHeight);

  // 绘制网格
  ctx.strokeStyle = 'rgba(0, 150, 255, 0.7)';
  ctx.fillStyle = 'rgba(0,255,72,0.8)';
  ctx.lineWidth = 1;

  // 实际教室尺寸
  const classroomWidth = 12;
  const classroomHeight = 14;
  const step = 1; // 1米间隔

  // 绘制水平网格线
  for (let y = 0; y <= classroomHeight; y += step) {
    const [startX, startY] = worldToPixel(0, y);
    const [endX, endY] = worldToPixel(classroomWidth, y);
    ctx.beginPath();
    ctx.moveTo(startX, startY);
    ctx.lineTo(endX, endY);
    ctx.stroke();

    // 绘制刻度标签
    ctx.fillText(`${y}m`, startX - 20, startY);
  }

  // 绘制垂直网格线
  for (let x = 0; x <= classroomWidth; x += step) {
    const [startX, startY] = worldToPixel(x, 0);
    const [endX, endY] = worldToPixel(x, classroomHeight);
    ctx.beginPath();
    ctx.moveTo(startX, startY);
    ctx.lineTo(endX, endY);
    ctx.stroke();

    // 绘制刻度标签
    ctx.fillText(`${x}m`, startX-5, startY + 12);
  }
};

// // 格式化矩阵显示
// const formattedMatrix = computed(() => {
//   if (!H.value) return '请先计算变换矩阵';
//   H.value.toArray();
//   return `[${H.value[0].map(num => Number(num).toFixed(6)).join(', ')}]\n` +
//          `[${H.value[1].map(num => Number(num).toFixed(6)).join(', ')}]`;
// });
//
// // 复制矩阵到剪贴板
// const copyMatrix = () => {
//   navigator.clipboard.writeText(formattedMatrix.value);
// };

// 初始化canvas尺寸
const syncCanvasSize = () => {
  const img = classroomImg.value;
  gridCanvas.value.width = img.width || img.naturalWidth;
  gridCanvas.value.height = img.height || img.naturalHeight ;

  if (showGrid.value) drawGrid();
};
// 将标定结果发送到后端
const uploadH = async () => {
  const data = JSON.stringify({
      class_id: '001',
      matrix: H.value
    })
  const response = await request.post('/uploadH/',data)
  console.log(response)
};
// 从后端获取H矩阵
const getH = async () => {
  const response =  await request.get('/getH/')
  console.log(response)
  if (response.success) {
    H.value = response.matrix.data;
    Hinv.value = inv(H.value);
    showGrid.value = true;
  }
};
// 从后端获取实时帧
const get_frame = async () => {
  try {
    const response = await request.get('/get_frame/');
    if (response.data) {
      imgSrc.value = `data:image/jpeg;base64,${response.data}`;
    }
  } catch (error) {
    console.log('更新帧失败:', error);
  }
};

onMounted(() => {
  // 获取透视变换矩阵
  getH()
  // 获取当前视频帧
  get_frame()
  const img = classroomImg.value;
  if (img.complete) {
    syncCanvasSize();
  } else {
    img.onload = syncCanvasSize;
  }
});

// 监听变化
watch([showGrid, H], () => {
  if (showGrid.value && H.value) drawGrid();
});

</script>

<style scoped>
.calibration-tool {
  display: flex;
  gap: 20px;
  padding: 20px;
}

.image-container {
  height: fit-content;
  position: relative;
  border: 2px dashed #ccc;
  cursor: crosshair;
}

.image-container img {
  max-width: 960px;
  max-height: 540px;
}
.overlay-canvas {
  position: absolute;
  z-index: 20;
  top: 0;
  left: 0;
  pointer-events: none; /* 允许点击穿透 */
}
.calibration-point {
  position: absolute;
  width: 16px;
  height: 16px;
  background: #f44336;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transform: translate(-50%, -50%);
  font-weight: bold;
  font-size: 10px;
}

.coordinate-form {
  min-width: 300px;
  border-left: 1px solid #eee;
  padding-left: 20px;
}
.delete-btn {
  margin: 0 0 0 15px;
  padding: 0;
  color: red;
  white-space: nowrap;
  background: none;
  font-size: 1.2em;
}
.input-coor {
  width: 70px;
  border: 1px solid #ccc;
  border-radius: 5px;
  margin: 0 10px 0 10px;
  padding: 0 5px 0 5px;
}

.point-input {
  margin-bottom: 10px;
  padding: 10px;
  background: #f5f5f5;
  border-radius: 5px;
}

.point-input label {
  display: inline-block;
  width: 100px;
  font-weight: bold;
}

button {
  margin-top: 20px;
  padding: 10px 15px;
  background: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

button:disabled {
  background: #cccccc;
}

pre {
  background: #f0f0f0;
  padding: 10px;
  border-radius: 4px;
  overflow-x: auto;
}
</style>
