<template>
  <div class="chart-container">
    <h3>学生行为统计</h3>
    <div class="chart-wrapper">
      <canvas id="doughnutChart"></canvas>
    </div>
  </div>
</template>

<script>
import Chart from 'chart.js/auto';
import {analyseStore} from '@/stores/analyseStore.js'
import {mapState} from 'pinia'
import request from "@/utils/request.js";


export default {
  name: 'BehaviorChart',
  data() {
    return {
      chart: null,
      stats: {
        '多动': 0,
        '东张西望': 0,
        '离座': 0,
        '瞌睡': 0,
        '起立': 0,
      }
    };
  },
  computed: {
    ...mapState(analyseStore, ['range'])
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
      console.log(range)
      try {
        const response = await request.get("/distraction_types/", {
          params: {
            time_range: range,
            class_id: '001',
            student_id: analyseStore().selectedId!=='-1' ? analyseStore().selectedId : null
          }
        });
        console.log('222',response);
        response.data.forEach(item => {
          this.stats[item.type] = item.count;
        })
        if (this.chart) {
          this.updateChart();
        } else {
          this.renderChart();
        }
      } catch (error) {
        console.error('渲染统计数据失败:', error);
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
                label: function (context) {
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
