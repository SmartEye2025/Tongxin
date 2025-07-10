<template>
  <div class="data-analytics">
    <h2>学生注意力数据分析</h2>

    <!-- 筛选条件 -->
    <div class="filters">
      <div class="filter-group">
        <label>时间范围:</label>
        <select v-model="selectedRange">
          <option v-for="item in availableRanges" :key="item.value" :value="item.value">{{item.label}}</option>
        </select>
      </div>
      <div class="filter-group" v-if="selectedRange === 'custom'">
        <label>开始日期:</label>
        <input type="date" v-model="startDate">
        <label>结束日期:</label>
        <input type="date" v-model="endDate">
      </div>

      <button @click="applyFilters" class="apply-btn">应用筛选</button>
    </div>

    <!-- 数据概览 -->
    <div class="data-overview">
      <div class="stat-card">
        <div class="stat-title">平均专注时长</div>
        <div class="stat-value">{{ stats.avgFocusTime }}分钟</div>
        <div class="stat-change" :class="{'positive': stats.focusChange >= 0, 'negative': stats.focusChange < 0}">
          {{ stats.focusChange >= 0 ? '+' : '' }}{{ stats.focusChange }}%
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-title">离座次数</div>
        <div class="stat-value">{{ stats.leaveSeatCount }}</div>
        <div class="stat-change" :class="{'positive': stats.leaveChange <= 0, 'negative': stats.leaveChange > 0}">
          {{ stats.leaveChange <= 0 ? '' : '+' }}{{ stats.leaveChange }}%
        </div>
      </div>

      <div class="stat-card">
        <div class="stat-title">干预成功率</div>
        <div class="stat-value">{{ stats.interventionSuccessRate }}%</div>
        <div class="stat-change" :class="{'positive': stats.successChange >= 0, 'negative': stats.successChange < 0}">
          {{ stats.successChange >= 0 ? '+' : '' }}{{ stats.successChange }}%
        </div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="charts">
      <FocusChart/>
      <BehaviorChart/>
    </div>

    <!-- 学生排名 -->
    <div class="student-ranking">
      <h3>学生专注度排名</h3>
      <table>
        <thead>
          <tr>
            <th>排名</th>
            <th>学生</th>
            <th>离座次数</th>
            <th>专注时长</th>
            <th>进步情况</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(student, index) in rankedStudents" :key="student.student_id">
            <td>{{ index + 1 }}</td>
            <td>{{ student.name }}</td>
            <td>{{ student.leaveTimes }}</td>
            <td>{{ student.focusTime }}分钟</td>
            <td>
              <span class="progress" :class="{'up': student.progress > 0, 'down': student.progress < 0}">
                {{ student.progress > 0 ? '↑' : '↓' }} {{ Math.abs(student.progress) }}%
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import BehaviorChart from "@/components/BehaviorChart.vue";
import FocusChart from "@/components/FocusChart.vue";
import { timeRangeStore } from '@/stores/timeRangeStore';
import { mapState, mapActions } from 'pinia';

export default {
  data(){
    return {
      selectedRange: 'week',
      startDate:'',
      endDate:'',
      stats:{
        avgFocusTime: 32,
        focusChange: 5.2,
        leaveSeatCount: 18,
        leaveChange: -3.1,
        interventionSuccessRate: 82,
        successChange: 2.4
      },
      rankedStudents:[
        { id: 'S1001', name: '小明', leaveTimes: 0, focusTime: 45, progress: 8.2 },
        { id: 'S1002', name: '小红', leaveTimes: 0, focusTime: 38, progress: 5.6 },
        { id: 'S1003', name: '小华', leaveTimes: 2, focusTime: 35, progress: 12.1 },
        { id: 'S1004', name: '小丽', leaveTimes: 0, focusTime: 32, progress: -2.3 },
        { id: 'S1005', name: '小强', leaveTimes: 1, focusTime: 28, progress: 3.7 }
      ]
    }
  },
  methods:{
    ...mapActions(timeRangeStore, ['setRange']),
    applyFilters() {
      timeRangeStore().range = this.selectedRange;
      // 模拟数据更新
      this.stats = {
        avgFocusTime: Math.floor(Math.random() * 20) + 25,
        focusChange: (Math.random() * 10 - 2).toFixed(1),
        leaveSeatCount: Math.floor(Math.random() * 15) + 5,
        leaveChange: (Math.random() * 8 - 4).toFixed(1),
        interventionSuccessRate: Math.floor(Math.random() * 20) + 75,
        successChange: (Math.random() * 5).toFixed(1)
      };
    },
  },
  components:{
    FocusChart,
    BehaviorChart
  },
  computed: {
    ...mapState(timeRangeStore, ['availableRanges']),
  },
  mounted() {
    this.selectedRange = timeRangeStore().range;
  },
}
</script>

<style scoped>
.data-analytics {
  padding: 20px;
}

h2 {
  margin-top: 0;
  color: #303133;
  padding-bottom: 15px;
  border-bottom: 1px solid #ebeef5;
}

.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  align-items: center;
  margin-bottom: 20px;
  padding: 15px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-group label {
  font-weight: 500;
  color: #606266;
}

.filter-group select, .filter-group input {
  padding: 8px 12px;
  border: 1px solid #DCDFE6;
  border-radius: 4px;
}

.apply-btn {
  padding: 8px 16px;
  background: #409EFF;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  margin-left: auto;
}

.data-overview {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 20px;
}

.stat-card {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  text-align: center;
}

.stat-title {
  font-size: 1em;
  color: #606266;
  margin-bottom: 10px;
}

.stat-value {
  font-size: 1.8em;
  font-weight: bold;
  color: #303133;
  margin-bottom: 5px;
}

.stat-change {
  font-size: 0.9em;
}

.positive {
  color: #67C23A;
}

.negative {
  color: #F56C6C;
}

.charts {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 20px;
}

.chart-container {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.chart-container h3 {
  margin-top: 0;
  color: #303133;
}

.chart-placeholder {
  height: 250px;
  background: #f5f7fa;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
}

.student-ranking {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.student-ranking h3 {
  margin-top: 0;
  color: #303133;
}

table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 15px;
}

th, td {
  padding: 12px 15px;
  text-align: left;
  border-bottom: 1px solid #ebeef5;
}

th {
  background-color: #f5f7fa;
  font-weight: 600;
  color: #303133;
}

.progress {
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.85em;
}

.progress.up {
  background: #f0f9eb;
  color: #67C23A;
}

.progress.down {
  background: #fef0f0;
  color: #F56C6C;
}
</style>
