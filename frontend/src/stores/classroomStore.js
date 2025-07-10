import { defineStore } from 'pinia'

export const classroomStore = defineStore('classroom', {
  state: () => ({
    students: [
      {
        id: 1,
        name: '张三',
        avatar: '',
        status: 'normal',
        deviceStatus: true,
        lastBehavior: null,
      },
      {
        id: 2,
        name: '李四',
        avatar: '',
        status: 'distracted',
        deviceStatus: true,
        lastBehavior: { type: 'distracted', time: '10:25' }
      },
      {
        id: 3,
        name: '王五',
        avatar: '',
        status: 'off_seat',
        deviceStatus: true,
        lastBehavior: { type: 'off_seat', time: '10:30' }
      },
      {
        id: 4,
        name: '赵六',
        avatar: '',
        status: 'normal',
        deviceStatus: false,
        lastBehavior: null
      },
      {
        id: 5,
        name: '小红',
        avatar: '',
        status: 'sleeping',
        deviceStatus: true,
        lastBehavior: { type: 'sleeping', time: '10:28' }
      }
    ],
    behaviorStats: {
      offSeat: 5,
      distracted: 12,
      sleeping: 3
    },
    autoRemindEnabled: false,
    classroomImg: null,
  }),
  actions: {
    // async fetchStudents(classroomId) {
    //   const response = await api.getClassroomStudents(classroomId)
    //   this.students = response.data
    // },
    // sendReminder(studentId) {
    //   api.sendReminder({
    //     student_id: studentId,
    //     classroom_id: this.currentClassroomId
    //   })
    // },
    // toggleAutoRemind(enabled) {
    //   this.autoRemindEnabled = enabled
    //   api.setAutoRemind(enabled)
    // },
    // updateBehaviorStats(detection) {
    //   // 更新行为统计数据
    //   if (detection.type === 'off_seat') {
    //     this.behaviorStats.offSeat++
    //   } else if (detection.type === 'distracted') {
    //     this.behaviorStats.distracted++
    //   }
    //
    //   // 更新学生状态
    //   const student = this.students.find(s => s.id === detection.student_id)
    //   if (student) {
    //     student.status = detection.type
    //   }
    // }
    setImg(img){
      this.classroomImg = img
    }
  }
})
