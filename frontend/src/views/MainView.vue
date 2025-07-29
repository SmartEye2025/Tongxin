<template>
  <div class="main-content">
    <div class="welcome-section">
      <h1>欢迎使用 “瞳心” 智慧课堂系统</h1>
      <p class="subtitle">慧眼洞察，智联童心，科技伴成长 </p>
    </div>

    <!-- 功能卡片网格 -->
    <div class="features-grid">
      <div v-for="feature in features" :key="feature.id" @click="navigate(feature.page)" class="feature-card">
        <div class="feature-icon">{{ feature.icon }}</div>
        <h3>{{ feature.title }}</h3>
        <p>{{ feature.desc }}</p>
      </div>
    </div>

    <!-- 通知和统计区域 -->
    <div class="dashboard-section">
      <div class="notifications">
        <h2>最新通知</h2>
        <ul>
          <li v-for="note in notifications" :key="note.id">
            <span class="note-text">{{ note.text }}</span>
            <span class="note-time">{{ note.time }}</span>
          </li>
        </ul>
      </div>

      <div class="stats">
        <h2>课堂数据</h2>
        <div class="stats-grid">
          <div class="stat-item">
            <div class="stat-value">数学</div>
            <div class="stat-label">进行中课程</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">43</div>
            <div class="stat-label">学生总数</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">96%</div>
            <div class="stat-label">到课率</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      features:[
        { id: 1, title: '标定坐标', icon: '📚', desc: '标定教室坐标体系', page:'/classroom' },
        { id: 2, title: '学生管理', icon: '👨‍🎓', desc: '管理学生信息与分组', page:'/students' },
        { id: 3, title: '数据统计', icon: '📊', desc: '学生注意力数据分析报表', page:'/analytics' },
      ],
      notifications:[
        { id: 1, text: '系统将于本周五凌晨进行维护升级', time: '2小时前' },
        { id: 2, text: '新增AI作业批改功能已上线', time: '1天前' },
        { id: 3, text: '暑期教师培训计划已发布', time: '3天前' }
      ]
    }
  },
  methods: {
    navigate(page) {
      this.$router.push(page)
    }
  }
}
</script>

<style scoped>
.main-content {
  flex: 1;
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

.welcome-section {
  text-align: center;
  margin-bottom: 3rem;
  padding: 2rem;
  background: linear-gradient(135deg, #ecf5ff 0%, #ffffff 100%);
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.welcome-section h1 {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
  color: #303133;
}

.subtitle {
  font-size: 1.2rem;
  color: #606266;
  margin-bottom: 2rem;
}

.quick-actions {
  display: flex;
  justify-content: center;
  gap: 1rem;
  margin-top: 1.5rem;
}

.primary-btn, .secondary-btn {
  padding: 0.8rem 1.5rem;
  border-radius: 6px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s;
  border: none;
}

.primary-btn {
  background-color: #409EFF;
  color: white;
}

.primary-btn:hover {
  background-color: #66b1ff;
  transform: translateY(-2px);
}

.secondary-btn {
  background-color: white;
  color: #409EFF;
  border: 1px solid #409EFF;
}

.secondary-btn:hover {
  background-color: #ecf5ff;
}

/* 功能卡片样式 */
.features-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.5rem;
  margin-bottom: 3rem;
}

.feature-card {
  background: white;
  border-radius: 10px;
  padding: 1.5rem;
  text-align: center;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.05);
  transition: transform 0.3s, box-shadow 0.3s;
}

.feature-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1);
}

.feature-icon {
  font-size: 2.5rem;
  margin-bottom: 1rem;
}

.feature-card h3 {
  margin: 0.5rem 0;
  color: #303133;
}

.feature-card p {
  color: #606266;
  font-size: 0.95rem;
  margin: 0;
}

/* 通知和统计区域 */
.dashboard-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
  margin-top: 2rem;
}

.notifications, .stats {
  background: white;
  border-radius: 10px;
  padding: 1.5rem;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.05);
}

.notifications h2, .stats h2 {
  margin-top: 0;
  color: #303133;
  padding-bottom: 0.8rem;
  border-bottom: 1px solid #ebeef5;
}

.notifications ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.notifications li {
  padding: 0.8rem 0;
  border-bottom: 1px solid #f5f7fa;
  display: flex;
  justify-content: space-between;
}

.note-text {
  color: #606266;
}

.note-time {
  color: #909399;
  font-size: 0.85rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

.stat-item {
  text-align: center;
  padding: 1rem;
  background-color: #f5f7fa;
  border-radius: 8px;
}

.stat-value {
  font-size: 2rem;
  font-weight: bold;
  color: #409EFF;
}

.stat-label {
  color: #909399;
  font-size: 0.9rem;
}
</style>
