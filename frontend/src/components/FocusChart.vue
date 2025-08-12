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
import { analyseStore } from '@/stores/analyseStore.js'
import { mapState } from 'pinia'
import request from "@/utils/request.js";

Chart.register(...registerables);

export default {
  name: 'FocusChart',
  data() {
    return {
      chart: null,
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
    renderChart(chart_data) {
      const ctx = this.$refs.barCanvas.getContext('2d');
      this.chart = new Chart(ctx, {
        type: 'bar',
        data:{
          labels: chart_data.labels,
          datasets: [
            {
              label: '专注时长(分钟)',
              backgroundColor: 'rgba(54, 162, 235, 0.5)',
              borderColor: 'rgba(54, 162, 235, 1)',
              borderWidth: 1,
              data: chart_data.focusTimes
            },
            {
              label: '分心次数',
              backgroundColor: 'rgba(255, 99, 132, 0.5)',
              borderColor: 'rgba(255, 99, 132, 1)',
              borderWidth: 1,
              data: chart_data.distractionCounts
            }
          ]
        },
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
        const chart_data = await this.fetchData(range);
        console.log(chart_data);
        if (this.chart) {
          // this.chart.clear()
          this.chart.data.labels = chart_data.labels;
          this.chart.data.datasets[0].data = chart_data.focusTimes;
          this.chart.data.datasets[1].data = chart_data.distractionCounts;
          // setTimeout(() => {
          //   this.chart.update();
          // }, 500); // 延迟执行
          // this.chart.update();
        } else {
          this.renderChart(chart_data);
        }
      } catch (error) {
        console.error('渲染专注力数据失败:', error);
      }
    },
    async fetchData(range) {
      // 根据时间范围生成不同的模拟数据
      let labels = [];
      let focusTimes = [];
      let distractionCounts = [];
      const response = await request.get("/weekly_data/", {
        params: {
          time_range: range,
          class_id: '001',
          student_id: this.selectedId!=='-1' ? this.selectedId : null
        }
      });
      console.log('333',response);
      focusTimes = response.data.focus_time
      distractionCounts = response.data.distraction_count
      if (range === '本周' || range === '上周') {
        // 本周数据 - 按天
        labels = ['周一', '周二', '周三', '周四', '周五'];
      }
      else if (range === '本月') {
        // 本月数据 - 按周
        labels = ['第一周', '第二周', '第三周', '第四周'];
      }
      else{
        let str1 = range.split('|')[0];
        let str2 = range.split('|')[1];
        const startDate = new Date(str1);
        const endDate = new Date(str2);
        // 检查日期是否有效
        if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
          console.error("无效的日期格式，请使用 YYYY-MM-DD");
          return [];
        }
        // 确保 startDate <= endDate
        if (startDate > endDate) {
          console.error("开始日期不能晚于结束日期");
          return [];
        }
        let currentDate = new Date(startDate);

        while (currentDate <= endDate) {
          // 提取月和日（注意：月份从 0 开始，所以要 +1）
          const month = String(currentDate.getMonth() + 1).padStart(2, '0');
          const day = String(currentDate.getDate()).padStart(2, '0');
          labels.push(`${month}-${day}`);
          // 增加一天
          currentDate.setDate(currentDate.getDate() + 1);
        }
        labels = labels.slice(0,focusTimes.length);
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
