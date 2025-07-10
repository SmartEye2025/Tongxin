<template>
  <div class="focus-chart-container">
    <h3 class="chart-title">课堂专注力统计</h3>
    <div class="chart-wrapper">
      <canvas ref="barCanvas"></canvas>
    </div>
  </div>
</template>

<script>
import { Chart, registerables } from 'chart.js';
import { timeRangeStore } from '@/stores/timeRangeStore'
import { mapState } from 'pinia'

Chart.register(...registerables);

export default {
  name: 'FocusChart',
  data() {
    return {
      chart: null,
      chartData: {
        labels: [],
        datasets: [
          {
            label: '专注时长(小时)',
            backgroundColor: 'rgba(54, 162, 235, 0.5)',
            borderColor: 'rgba(54, 162, 235, 1)',
            borderWidth: 1,
            data: []
          },
          {
            label: '分心次数',
            backgroundColor: 'rgba(255, 99, 132, 0.5)',
            borderColor: 'rgba(255, 99, 132, 1)',
            borderWidth: 1,
            data: []
          }
        ]
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
    renderChart() {
      const ctx = this.$refs.barCanvas.getContext('2d');
      this.chart = new Chart(ctx, {
        type: 'bar',
        data: this.chartData,
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            y: {
              beginAtZero: true,
              title: {
                display: true,
                text: '数值'
              }
            },
            x: {
              title: {
                display: true,
                text: '时间/学生'
              }
            }
          },
          plugins: {
            tooltip: {
              callbacks: {
                label: (context) => {
                  let label = context.dataset.label || '';
                  if (label) {
                    label += ': ';
                  }
                  if (context.parsed.y !== null) {
                    label += context.dataset.label.includes('时长')
                      ? `${context.parsed.y} 小时`
                      : `${context.parsed.y} 次`;
                  }
                  return label;
                }
              }
            },
            legend: {
              position: 'top'
            }
          }
        }
      });
    },
    async loadData(range) {
      try {
        // 模拟数据 - 实际项目中替换为API调用
        const mockData = this.generateMockData(range);
        console.log(mockData);
        this.chartData.labels = mockData.labels;
        this.chartData.datasets[0].data = mockData.focusTimes;
        this.chartData.datasets[1].data = mockData.distractionCounts;
        if (this.chart) {
          this.updateChart();
        } else {
          this.renderChart();
        }
      } catch (error) {
        console.error('获取专注力数据失败:', error);
      }
    },
    updateChart() {
      this.chart.data.labels = this.chartData.labels;
      this.chart.data.datasets[0].data = this.chartData.datasets[0].data;
      this.chart.data.datasets[1].data = this.chartData.datasets[1].data;
      this.chart.update();
    },
    generateMockData(range) {
      // 根据时间范围生成不同的模拟数据
      const labels = [];
      const focusTimes = [];
      const distractionCounts = [];

      if (range === 'day') {
        // 今日数据 - 按小时
        for (let i = 8; i <= 17; i++) {
          if(11<i&&i<14) continue;
          labels.push(`${i}:00`);
          focusTimes.push((Math.random()*0.6+0.2).toFixed(1));
          distractionCounts.push(Math.floor(Math.random() * 5));
        }
      } else if (range === 'week') {
        // 本周数据 - 按天
        const days = ['周一', '周二', '周三', '周四', '周五'];
        days.forEach(day => {
          labels.push(day);
          focusTimes.push((Math.random() * 5 + 2.5).toFixed(1));
          distractionCounts.push(Math.floor(Math.random() * 15) + 5);
        });
      } else {
        // 本月数据 - 按周
        for (let i = 1; i <= 4; i++) {
          labels.push(`第${i}周`);
          focusTimes.push((Math.random() * 25 + 8).toFixed(1));
          distractionCounts.push(Math.floor(Math.random() * 50) + 20);
        }
      }

      return { labels, focusTimes, distractionCounts };
    }
  },
};
</script>

<style scoped>
.focus-chart-container {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  height: 100%;
  display: flex;
  flex-direction: column;
}

.chart-title {
  margin-top: 0;
  margin-bottom: 16px;
  text-align: center;
}

.chart-wrapper {
  flex: 1;
  min-height: 300px;
  position: relative;
}
</style>
