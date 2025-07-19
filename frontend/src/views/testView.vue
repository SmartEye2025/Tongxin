<template>
  <v-app>
    <v-main>
      <v-container fluid class="pa-4 fill-height">
        <v-row class="h-100" no-gutters>
          <!-- 左侧监控区 -->
          <v-col cols="12" md="7">
            <v-card class="h-100" elevation="2">
              <v-card-title class="bg-primary">
                <v-icon icon="mdi-cctv" class="mr-2"></v-icon>
                课堂实时监控
              </v-card-title>
              <div class="video-container">
                <v-overlay
                  v-model="showHeatmap"
                  contained
                  class="heatmap-overlay"
                  scrim="rgba(0,0,0,0.5)"
                ></v-overlay>
              </div>
              <v-card-actions>
                <v-btn
                  @click="toggleHeatmap"
                  :prepend-icon="showHeatmap ? 'mdi-eye-off' : 'mdi-eye'"
                  variant="text"
                >
                  {{ showHeatmap ? '隐藏热力图' : '显示热力图' }}
                </v-btn>
                <v-spacer></v-spacer>
                <v-chip
                  v-for="(count, behavior) in behaviorStats"
                  :key="behavior"
                  class="ma-1"
                  :color="getBehaviorColor(behavior)"
                >
                  {{ behavior }}: {{ count }}
                </v-chip>
              </v-card-actions>
            </v-card>
          </v-col>

          <!-- 右侧学生信息区 -->
          <v-col cols="12" md="5">
            <v-card class="h-100" elevation="2">
              <v-card-title class="bg-primary">
                <v-icon icon="mdi-account-group" class="mr-2"></v-icon>
                学生状态监测
              </v-card-title>
              <v-tabs v-model="studentViewMode" grow>
                <v-tab value="grid">网格视图</v-tab>
                <v-tab value="list">列表视图</v-tab>
                <v-tab value="stats">行为统计</v-tab>
              </v-tabs>

              <v-window v-model="studentViewMode">
                <!-- 网格视图 -->
                <v-window-item value="grid">
                  <v-container fluid>
                    <v-row dense>
                      <v-col
                        v-for="student in students"
                        :key="student.id"
                        cols="6"
                        sm="4"
                      >
                        <student-card
                          :student="student"
                          :selected="selectedStudents.includes(student.id)"
                          @toggle="toggleStudentSelection"
                        />
                      </v-col>
                    </v-row>
                  </v-container>
                </v-window-item>

                <!-- 列表视图 -->
                <v-window-item value="list">
                  <v-list lines="two">
                    <v-list-item
                      v-for="student in students"
                      :key="student.id"
                      @click="toggleStudentSelection(student.id)"
                      :active="selectedStudents.includes(student.id)"
                    >
                      <template v-slot:prepend>
                        <v-avatar :color="getStatusColor(student.status)">
                          <v-icon icon="mdi-account"></v-icon>
                        </v-avatar>
                      </template>
                      <v-list-item-title>
                        {{ student.name }}
                      </v-list-item-title>
                      <v-list-item-subtitle>
                        <v-chip
                          size="small"
                          :color="getBehaviorColor(student.behavior)"
                          class="mr-1"
                        >
                          {{ student.behavior }}
                        </v-chip>
                        <span>位置: ({{ student.x }}, {{ student.y }})</span>
                      </v-list-item-subtitle>
                    </v-list-item>
                  </v-list>
                </v-window-item>

                <!-- 统计视图 -->
                <v-window-item value="stats">
                  <v-card-text>
                    <v-row>
                      <v-col cols="12" md="6">
                        <v-card>
                          <v-card-title>行为分布</v-card-title>
                          <v-card-text>
                            <behavior-pie-chart :stats="behaviorStats" />
                          </v-card-text>
                        </v-card>
                      </v-col>
                      <v-col cols="12" md="6">
                        <v-card>
                          <v-card-title>专注度趋势</v-card-title>
                          <v-card-text>
                            <attention-line-chart :data="attentionData" />
                          </v-card-text>
                        </v-card>
                      </v-col>
                    </v-row>
                  </v-card-text>
                </v-window-item>
              </v-window>

              <v-divider></v-divider>

              <v-card-actions>
                <v-select
                  v-model="alertType"
                  :items="alertTypes"
                  label="提醒类型"
                  density="compact"
                  class="mr-2"
                  style="max-width: 200px"
                ></v-select>
                <v-checkbox
                  v-model="selectAll"
                  label="全选"
                  density="compact"
                  hide-details
                ></v-checkbox>
              </v-card-actions>
            </v-card>
          </v-col>
        </v-row>
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup>
import { ref, watch, computed } from 'vue'

// 状态管理
const studentViewMode = ref('grid')
const showHeatmap = ref(false)
const selectedStudents = ref([])
const selectAll = ref(false)
const alertType = ref('attention')

const students = ref([
  // 示例数据，实际从WebSocket获取
  { id: 1, name: '张三', x: 2.5, y: 3.2, behavior: '专注', status: 'normal' },
  { id: 2, name: '李四', x: 1.8, y: 4.0, behavior: '分心', status: 'warning' },
  // 更多学生...
])

// 行为统计
const behaviorStats = computed(() => {
  const stats = {}
  students.value.forEach(s => {
    stats[s.behavior] = (stats[s.behavior] || 0) + 1
  })
  return stats
})

// 全选逻辑
watch(selectAll, (val) => {
  selectedStudents.value = val ? students.value.map(s => s.id) : []
})

// 颜色映射
const getStatusColor = (status) => {
  const colors = { normal: 'success', warning: 'warning', danger: 'error' }
  return colors[status] || 'grey'
}

const getBehaviorColor = (behavior) => {
  const colors = {
    专注: 'green',
    分心: 'orange',
    走动: 'blue',
    趴桌: 'red'
  }
  return colors[behavior] || 'grey'
}

</script>

<style scoped>
.video-container {
  position: relative;
  width: 100%;
  height: 0;
  padding-bottom: 56.25%; /* 16:9 */
  background: #000;
}

.heatmap-overlay {
  pointer-events: none;
}

.h-100 {
  height: 100%;
}

.fill-height {
  height: calc(100vh - 64px);
}
</style>
