<template>
  <v-container fluid class="classroom-view">
    <v-row>
      <v-col cols="8">
        <camera-view
          :students="studentsWithPosition"
          :ws-url="wsUrl"
          @student-click="handleStudentClick"
        />
      </v-col>

      <v-col cols="4">
        <v-card class="sidebar">
          <v-tabs v-model="tab" grow>
            <v-tab>学生列表</v-tab>
            <v-tab>异常行为</v-tab>
            <v-tab>课堂统计</v-tab>
          </v-tabs>

          <v-tabs-items v-model="tab">
            <v-tab-item>
              <student-list
                :students="students"
                @select="focusStudent"
              />
            </v-tab-item>

            <v-tab-item>
              <alert-panel :alerts="abnormalBehaviors" />
            </v-tab-item>

            <v-tab-item>
              <class-stats :stats="classStats" />
            </v-tab-item>
          </v-tabs-items>
        </v-card>
      </v-col>
    </v-row>

    <v-snackbar v-model="showAlert" :color="alertColor" top>
      {{ alertMessage }}
      <template v-slot:action="{ attrs }">
        <v-btn text v-bind="attrs" @click="showAlert = false">
          关闭
        </v-btn>
      </template>
    </v-snackbar>
  </v-container>
</template>

<script>
import CameraView from '@/components/VideoPlayer.vue'
import StudentList from '@/components/StudentList'
import AlertPanel from '@/components/AlertPanel'
import ClassStats from '@/components/ClassStats'

export default {
  components: {
    CameraView,
    StudentList,
    AlertPanel,
    ClassStats
  },
  data() {
    return {
      tab: 0,
      wsUrl: 'ws://localhost:8000/ws/video/',
      students: [],
      abnormalBehaviors: [],
      classStats: {},
      showAlert: false,
      alertMessage: '',
      alertColor: 'error'
    }
  },
  computed: {
    studentsWithPosition() {
      return this.students.map(s => ({
        ...s,
        x: s.position.x / 100, // 假设后端返回的是百分比
        y: s.position.y / 100
      }))
    }
  },
  created() {
    this.fetchClassData()
    this.setupWebSocket()
  },
  methods: {
    async fetchClassData() {
      try {
        const response = await this.$http.get('/api/classroom/current')
        this.students = response.data.students
        this.classStats = response.data.stats
      } catch (error) {
        console.error('获取课堂数据失败:', error)
      }
    },
    setupWebSocket() {
      const ws = new WebSocket('ws://localhost:8000/ws/alerts/')

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.type === 'behavior_alert') {
          this.handleBehaviorAlert(data)
        }
      }
    },
    handleBehaviorAlert(data) {
      this.abnormalBehaviors.unshift({
        ...data,
        timestamp: new Date()
      })

      // 更新学生状态
      const student = this.students.find(s => s.id === data.studentId)
      if (student) {
        student.isAbnormal = true
        student.status = data.behaviorType
      }

      // 显示通知
      this.alertMessage = `${student.name} ${this.getBehaviorText(data.behaviorType)}`
      this.showAlert = true

      // 5秒后恢复正常状态
      setTimeout(() => {
        if (student) student.isAbnormal = false
      }, 5000)
    },
    getBehaviorText(type) {
      const behaviors = {
        'leave_seat': '离开了座位',
        'sleep': '正在睡觉',
        'phone': '正在使用手机',
        'talk': '正在交头接耳'
      }
      return behaviors[type] || '有异常行为'
    },
    focusStudent(student) {
      // 可以添加聚焦逻辑，比如放大该学生区域
      console.log('Focus on:', student.name)
    },
    handleStudentClick(student) {
      this.$emit('student-selected', student)
    }
  }
}
</script>

<style scoped>
.classroom-view {
  height: 100vh;
  padding: 16px;
  background: #f5f5f5;
}

.sidebar {
  height: calc(100vh - 32px);
  display: flex;
  flex-direction: column;
}

.v-card {
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
</style>
