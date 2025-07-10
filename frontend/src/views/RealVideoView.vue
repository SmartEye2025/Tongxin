<template>
  <div class="monitor-container">
    <!-- 主内容区 -->
    <div class="main-content">
      <!-- 左侧视频监控区 -->
      <div class="video-section">
        <div class="video-wrapper">
          <VideoPlayer/>
        </div>
        <!-- 行为统计卡片 -->
        <v-card class="stats-card">
          <v-card-title>
            <v-icon left>mdi-chart-bar</v-icon>
            课堂行为统计
          </v-card-title>
          <v-card-text>
            <div class="stat-item">
              <span class="stat-label">离座行为:</span>
              <v-chip color="orange" text-color="white">{{ behaviorStats.offSeat }} 次</v-chip>
            </div>
            <div class="stat-item">
              <span class="stat-label">分心行为:</span>
              <v-chip color="red" text-color="white">{{ behaviorStats.distracted }} 次</v-chip>
            </div>
            <div class="stat-item">
              <span class="stat-label">瞌睡行为:</span>
              <v-chip color="blue" text-color="white">{{ behaviorStats.sleeping }} 次</v-chip>
            </div>
          </v-card-text>
        </v-card>
      </div>

      <!-- 右侧控制面板 -->
      <div class="control-section">
        <!-- 学生列表 -->
        <v-card class="student-list-card">
          <v-card-title>
            <v-icon left>mdi-account-group</v-icon>
            学生列表 ({{ students.length }}人)
          </v-card-title>
          <v-card-text>
            <v-text-field
              v-model="searchStudent"
              append-icon="mdi-magnify"
              label="搜索学生"
              single-line
              hide-details
            ></v-text-field>

            <v-list class="student-list">
              <v-list-item
                v-for="student in students"
                :class="{'active-student': currentStudent === student.id}"
                :key="student.id"
                :prepend-avatar="student.avatar || defaultAvatar"
                :title="student.name"
                :subtitle="`状态: ${getStatusText(student.status)}`"
                @click="selectStudent(student)"
              >
                <!-- 右侧震动按钮 -->
                <template v-slot:append>
                  <v-btn
                    icon="mdi-vibrate"
                    color="red"
                    @click.stop="sendVibration(student.id)"
                    :disabled="!student.deviceStatus"
                  />
                </template>
              </v-list-item>

<!--              <v-list-item-->
<!--                v-for="student in filteredStudents"-->
<!--                :key="student.id"-->
<!--                :class="{'active-student': currentStudent === student.id}"-->

<!--                @click="selectStudent(student)"-->
<!--              >-->

<!--                <v-list-item-content>-->
<!--                  <v-list-item-subtitle>-->
<!--                    <v-chip x-small :color="getStatusColor(student.status)" text-color="white">-->
<!--                      {{ getStatusText(student.status) }}-->
<!--                    </v-chip>-->
<!--                    <span class="ml-2">手环: {{ student.deviceStatus ? '在线' : '离线' }}</span>-->
<!--                  </v-list-item-subtitle>-->
<!--                </v-list-item-content>-->

<!--                <v-list-item-action>-->
<!--                  <v-btn-->
<!--                    icon-->
<!--                    color="red"-->
<!--                    @click.stop="sendVibration(student.id)"-->
<!--                    :disabled="!student.deviceStatus"-->
<!--                  >-->
<!--                    <v-icon>mdi-vibrate</v-icon>-->
<!--                  </v-btn>-->
<!--                </v-list-item-action>-->
<!--              </v-list-item>-->
            </v-list>
          </v-card-text>
        </v-card>

        <!-- 控制面板 -->
        <v-card class="control-card">
          <v-card-title>
            <v-icon left>mdi-cog</v-icon>
            课堂控制
          </v-card-title>
          <v-card-text>
            <div class="control-item">
              <v-switch
                v-model="autoRemindEnabled"
                label="自动提醒"
                color="primary"
              ></v-switch>
              <v-slider
                v-model="remindIntensity"
                label="提醒强度"
                min="1"
                max="3"
                step="1"
                ticks
                :disabled="!autoRemindEnabled"
              ></v-slider>
            </div>

            <div class="control-item">
              <v-select
                v-model="selectedBehavior"
                :items="behaviorTypes"
                label="重点关注行为"
                multiple
                chips
              ></v-select>
            </div>

            <v-btn
              block
              color="primary"
              @click="sendClassReminder"
              :disabled="!selectedStudents.length"
            >
              <v-icon left>mdi-bell-ring</v-icon>
              集体提醒 ({{ selectedStudents.length }}人)
            </v-btn>
          </v-card-text>
        </v-card>
      </div>
    </div>

    <!-- 底部状态栏 -->
    <div class="status-bar">
      <v-chip class="ma-2" :color="mqttConnected ? 'green' : 'red'" text-color="white">
        <v-icon left>mdi-watch-vibrate</v-icon>
        手环连接: {{ mqttConnected ? '已连接' : '断开' }}
      </v-chip>
      <v-chip class="ma-2" :color="analysisActive ? 'green' : 'orange'" text-color="white">
        <v-icon left>mdi-robot</v-icon>
        行为分析: {{ analysisActive ? '运行中' : '已暂停' }}
      </v-chip>
      <v-spacer></v-spacer>
      <span class="update-time">
        最后更新: {{ lastUpdateTime }}
      </span>
    </div>

    <!-- 提醒发送确认对话框 -->
    <v-dialog v-model="confirmDialog" max-width="400">
      <v-card>
        <v-card-title>确认发送提醒</v-card-title>
        <v-card-text>
          确定要向 {{ currentStudentName }} 发送手环震动提醒吗？
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="confirmDialog = false">取消</v-btn>
          <v-btn color="primary" @click="confirmRemind">确认发送</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="show_snackbar" timeout="1500">
      {{ snackbar_message }}
    </v-snackbar>
  </div>
</template>

<script>
import { mapState } from 'pinia'
import { classroomStore } from '@/stores/classroomStore'
import VideoPlayer from "@/components/VideoPlayer.vue";
import request from "@/utils/request.js";

export default {
  data() {
    return {
      videoActive: false,
      analysisActive: false,
      searchStudent: '',
      currentStudent: null,
      currentStudentName: '',
      confirmDialog: false,
      // 开启/关闭自动提醒
      autoRemindEnabled:true,
      remindIntensity: 2,
      selectedStudents: [],
      // mqtt连接
      mqttConnected: true,
      mqtt_messages: [],
      client: null,
      lastUpdateTime: '刚刚',
      defaultAvatar: 'https://cdn.vuetifyjs.com/images/lists/1.jpg',
      // 重点关注行为
      selectedBehavior: ['off_seat','sleeping'],
      behaviorTypes: [
        { title: '离座行为', value: 'off_seat' },
        { title: '分心行为', value: 'distracted' },
        { title: '瞌睡行为', value: 'sleeping' }
      ],
      show_snackbar:false,
      snackbar_message:'',
    }
  },
  components:{VideoPlayer},
  computed: {
    ...mapState(classroomStore, ['students', 'behaviorStats']),
    filteredStudents() {
      return this.students.filter(student =>
        student.name.includes(this.searchStudent) ||
        student.id.toString().includes(this.searchStudent)
      )
    }
  },
  methods: {
    async sendReminder(studentId) {
      console.log('sendReminder')
      const send_data={
        topic:'remind/vibration',
        msg:{
          student_id:studentId
        }
      }
      await request.post('/send_mqtt/',send_data)
    },
    // 选择学生
    selectStudent(student) {
      this.currentStudent = student.id
      this.currentStudentName = student.name
      this.selectedStudents = this.selectedStudents.includes(student.id)
        ? this.selectedStudents.filter(id => id !== student.id)
        : [...this.selectedStudents, student.id]
    },

    // 发送震动提醒
    sendVibration(studentId) {
      const student = this.students.find(s => s.id === studentId)
      this.currentStudent = studentId
      this.currentStudentName = student.name
      this.confirmDialog = true
    },

    // 确认发送提醒
    confirmRemind() {
      this.sendReminder(this.currentStudent)
      // 模拟发送效果
      const studentIndex = this.students.findIndex(s => s.id === this.currentStudent)
      if (studentIndex !== -1) {
        this.students[studentIndex].status = 'normal'
        this.students[studentIndex].lastBehavior = null
      }
      this.confirmDialog = false
      this.snackbar_message=`已向 ${this.currentStudentName} 发送提醒`
      this.show_snackbar = true
    },

    // 集体提醒
    sendClassReminder() {
      this.selectedStudents.forEach(studentId => {
        this.sendReminder(studentId)
      })
      this.snackbar_message = `已向 ${this.selectedStudents.length} 名学生发送提醒`
      this.show_snackbar = true
      this.selectedStudents = []
    },

    // 刷新数据
    refreshData() {
      this.lastUpdateTime = new Date().toLocaleTimeString()
      this.$toast.info('数据已刷新')
    },

    // 状态颜色
    getStatusColor(status) {
      switch(status) {
        case 'off_seat': return 'orange'
        case 'distracted': return 'red'
        case 'sleeping': return 'blue'
        default: return 'green'
      }
    },

    // 状态文本
    getStatusText(status) {
      switch(status) {
        case 'off_seat': return '离座'
        case 'distracted': return '分心'
        case 'sleeping': return '瞌睡'
        default: return '正常'
      }
    }
  },
  mounted() {
    // 模拟MQTT连接
    setInterval(() => {
      this.mqttConnected = Math.random() > 0.1 // 90%概率显示连接正常
    }, 5000)

    // 模拟行为检测
    setInterval(() => {
      if (this.analysisActive && this.autoRemindEnabled) {
        const randomStudent = this.students[
          Math.floor(Math.random() * this.students.length)
        ]

        if (randomStudent.deviceStatus && Math.random() > 0.7) {
          const behaviors = ['off_seat', 'distracted', 'sleeping']
          const randomBehavior = behaviors[Math.floor(Math.random() * behaviors.length)]

          randomStudent.status = randomBehavior
          randomStudent.lastBehavior = {
            type: randomBehavior,
            time: new Date().toLocaleTimeString()
          }

          this.virtualBehaviorStats[randomBehavior]++

          if (this.autoRemindEnabled) {
            this.sendReminder(randomStudent.id)
          }
        }
      }
    }, 3000)

    // 初始化更新时间
    this.lastUpdateTime = new Date().toLocaleTimeString()
  },
  beforeUnmount() {
    cancelAnimationFrame(this.videoAnimationFrame)
    clearInterval(this.mqttInterval)
    clearInterval(this.behaviorInterval)
  }
}
</script>

<style scoped>
.monitor-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: #f5f5f5;
}

.main-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.video-section {
  flex: 2;
  display: flex;
  flex-direction: column;
  padding: 16px;
}

.video-wrapper {
  position: relative;
  width: fit-content;
  background-color: #f4efef;
  border-radius: 8px;
  overflow: hidden;
}

.control-section {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  background-color: white;
  border-left: 1px solid #e0e0e0;
}

.student-list-card,
.control-card {
  margin-bottom: 16px;
}

.student-list {
  max-height: 400px;
  overflow-y: auto;
  margin-top: 8px;
}

.active-student {
  background-color: #e3f2fd;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 12px 0;
}

.stat-label {
  font-weight: 500;
}

.control-item {
  margin-bottom: 16px;
}

.status-bar {
  display: flex;
  align-items: center;
  padding: 8px 16px;
  background-color: white;
  border-top: 1px solid #e0e0e0;
}

.update-time {
  color: #666;
  font-size: 0.9em;
}

.stats-card {
  margin-top: 16px;
  max-width: 800px;
}
</style>
