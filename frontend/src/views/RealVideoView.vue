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
            课堂行为统计
          </v-card-title>
          <v-card-text>
            <div class="stat-item" v-for="(value,key) in behaviorStats" :key="key">
              <span class="stat-label">{{getStatusText(key)}}:</span>
              <v-chip :color="getStatusColor(key)" text-color="white">{{ value }} 次</v-chip>
            </div>
          </v-card-text>
          <v-btn class="stats-card-btn" @click="hotMap=!hotMap">
            {{ hotMap ? "隐藏热力图" : "显示热力图" }}
          </v-btn>
        </v-card>
      </div>

      <!-- 右侧控制面板 -->
      <div class="control-section">
        <!-- 学生列表 -->
        <v-card class="student-list-card">
          <v-card-title>
            <v-icon left>mdi-account-group</v-icon>
            学生状态监控 ({{ students.length }}人)
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
                :key="student.id"
                @click="selectStudent(student)"
                :active="selectedStudents.includes(student.id)"
              >
                <template v-slot:prepend>
                  <v-avatar :image="student.avatar || defaultAvatar">
                  </v-avatar>
                </template>
                <v-list-item-title>
                  {{ student.name }}
                </v-list-item-title>
                <v-list-item-subtitle>
                  <v-chip
                    size="small"
                    :color="getStatusColor(student.status)"
                    class="mr-1"
                  >
                    {{getStatusText(student.status)}}
                  </v-chip>
                  <span>位置: ({{ student.x }}, {{ student.y }})</span>
                </v-list-item-subtitle>
                <!-- 右侧提醒按钮 -->
                <template v-slot:append>
                  <v-btn color="blue" @click.stop="sendVibration(student.id)">
                    提醒
                  </v-btn>
                </template>
              </v-list-item>
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
                v-model="autoRemind"
                label="自动提醒"
                color="primary"
              ></v-switch>
              <v-slider
                v-model="intensity"
                label="提醒强度"
                min="1"
                max="3"
                step="1"
                ticks
                :disabled="!autoRemind"
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
          确定要向 {{ currentStudentName }} 发送提醒吗？
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
import { mapState, mapActions } from 'pinia'
import { classStore } from '@/stores/classStore.js'
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
      socket:null,
      statusMessages: {
        connecting: '正在连接...',
        connected: '实时连接中',
        disconnected: '连接已断开',
        error: '连接错误'
      },
    }
  },
  components:{VideoPlayer},
  computed: {
    ...mapState(classStore, ['students', 'behaviorStats','enableHotMap','enableAutoRemind','remindIntensity']),
    // 可写计算属性
    hotMap: {
      get() {
        return this.enableHotMap
      },
      set(value) {
        this.updateSetting({ key: 'enableHotMap', value })
      }
    },
    autoRemind: {
      get() {
        return this.enableAutoRemind
      },
      set(value) {
        this.updateSetting({ key: 'enableAutoRemind', value })
      }
    },
    intensity: {
      get() {
        return this.remindIntensity
      },
      set(value) {
        this.updateSetting({ key: 'remindIntensity', value })
      }
    },
  },
  methods: {
    ...mapActions(classStore, ['updateSetting']),
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
      this.updateSetting({ key: 'remindStudentId', studentId })
      const student = this.students.find(s => s.id === studentId)
      this.currentStudent = studentId
      this.currentStudentName = student.name
      this.confirmDialog = true
    },

    // 确认发送提醒
    confirmRemind() {
      this.sendReminder(this.currentStudent)

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

    // 状态颜色
    getStatusColor(status) {
      switch(status) {
        case 'offSeat': return 'red'
        case 'run': return 'red'
        case 'lookAround': return 'orange'
        case 'stand': return 'orange'
        case 'sleeping': return 'red'
        default: return 'green'
      }
    },

    // 状态文本
    getStatusText(status) {
      switch(status) {
        case 'offSeat': return '离座'
        case 'run': return '跑动'
        case 'lookAround': return '东张西望'
        case 'stand': return '站立'
        case 'sleeping': return '瞌睡'
        default: return '正常'
      }
    },
  },
  mounted() {
    // // 模拟MQTT连接
    // setInterval(() => {
    //   this.mqttConnected = Math.random() > 0.1 // 90%概率显示连接正常
    // }, 5000)
    //
    // // 模拟行为检测
    // setInterval(() => {
    //   if (this.analysisActive && this.enableAutoRemind) {
    //     const randomStudent = this.students[
    //       Math.floor(Math.random() * this.students.length)
    //     ]
    //
    //     if (randomStudent.deviceStatus && Math.random() > 0.7) {
    //       const behaviors = ['off_seat', 'distracted', 'sleeping']
    //       const randomBehavior = behaviors[Math.floor(Math.random() * behaviors.length)]
    //
    //       randomStudent.status = randomBehavior
    //       randomStudent.lastBehavior = {
    //         type: randomBehavior,
    //         time: new Date().toLocaleTimeString()
    //       }
    //
    //       this.virtualBehaviorStats[randomBehavior]++
    //
    //       if (this.enableAutoRemind) {
    //         this.sendReminder(randomStudent.id)
    //       }
    //     }
    //   }
    // }, 3000)

    // 初始化更新时间
    this.lastUpdateTime = new Date().toLocaleTimeString()
  },
  beforeUnmount() {
    // cancelAnimationFrame(this.videoAnimationFrame)
    // clearInterval(this.mqttInterval)
    // clearInterval(this.behaviorInterval)
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

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin: 12px 0;
  max-width: 150px;
}

.stat-label {
  font-weight: 500;
}

.control-item{
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

.stats-card-btn{
  background-color: #f4f4f4;
  position: absolute;
  right: 15px;
  top: 15px;
}
</style>
