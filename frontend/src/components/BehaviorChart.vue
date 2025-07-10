<template>
  <div class="chart-container">
    <h3>学生行为统计</h3>
<!--    <div class="time-range-selector">-->
<!--      <v-btn small @click="loadData('today')" :color="range === 'today' ? 'primary' : ''">今日</v-btn>-->
<!--      <v-btn small @click="loadData('week')" :color="range === 'week' ? 'primary' : ''">本周</v-btn>-->
<!--      <v-btn small @click="loadData('all')" :color="range === 'all' ? 'primary' : ''">全部</v-btn>-->
<!--    </div>-->

    <div class="chart-wrapper">
      <canvas id="doughnutChart"></canvas>
    </div>
  </div>
</template>

<script>
import Chart from 'chart.js/auto';
import { classStore } from '@/stores/classStore.js';
import { timeRangeStore } from '@/stores/timeRangeStore'
import { mapState } from 'pinia'


export default {
  name: 'BehaviorChart',
  data() {
    return {
      chart: null,
      stats: {
        '站立': 4,
        '离座': 5,
        '跑动': 2,
        '东张西望':11,
        '下蹲':2
      }
    };
  },
  computed: {
    ...mapState(timeRangeStore, ['range', 'timeRangeLabel'])
  },
  watch: {
    range: {
      handler: 'loadData'  //要执行的函数
    }
  },
  mounted() {
    this.loadData(this.range);
  },
  beforeUnmount() {
    if (this.chart) {
      this.chart.destroy();
    }
  },
  methods: {
    async loadData(range) {
      try {
        this.stats = classStore().getBehaviorData(range)
        if (this.chart) {
          this.updateChart();
        } else {
          this.renderChart();
        }
      } catch (error) {
        console.error('获取统计数据失败:', error);
      }
    },
    renderChart() {
      const ctx = document.getElementById('doughnutChart').getContext('2d');

      this.chart = new Chart(ctx, {
        type: 'doughnut',
        data: {
          labels: Object.keys(this.stats),
          datasets: [{
            data: Object.values(this.stats),
            backgroundColor: [
              'rgba(54, 162, 235, 0.7)',
              'rgba(255, 206, 86, 0.7)',
              'rgba(255, 99, 132, 0.7)',
              'rgba(149,207,0,0.7)',
              'rgba(193,128,255,0.7)',
            ],
            borderColor: [
              'rgba(54, 162, 235, 1)',
              'rgba(255, 206, 86, 1)',
              'rgba(255, 99, 132, 1)',
              'rgba(149,207,0,1)',
              'rgba(193,128,255,1)',

            ],
            borderWidth: 1
          }]
        },
        options: {
          responsive: true,
          plugins: {
            legend: {
              position: 'bottom',
            },
            tooltip: {
              callbacks: {
                label: function(context) {
                  const label = context.label || '';
                  const value = context.raw || 0;
                  const total = context.dataset.data.reduce((a, b) => a + b, 0);
                  const percentage = Math.round((value / total) * 100);
                  return `${label}: ${value} (${percentage}%)`;
                }
              }
            }
          }
        }
      });
    },
    updateChart() {
      this.chart.data.labels = Object.keys(this.stats);
      this.chart.data.datasets[0].data = Object.values(this.stats);
      this.chart.update();
    },
  },
};
</script>

<style scoped>
.chart-container {
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

h3 {
  margin-top: 0;
  margin-bottom: 16px;
  text-align: center;
}

.time-range-selector {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-bottom: 16px;
}

.chart-wrapper {
  margin-top: 30px;
  position: relative;
  height: 300px;
  display: flex;
  justify-content: center;
}
</style>
