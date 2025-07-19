import { defineStore } from 'pinia'

export const classStore = defineStore('class', {
  state: () => ({
    students: [
      {
        id: 1,
        name: '张三',
        avatar: '',
        status: 'normal',
        x:0,
        y:0,
      },
      {
        id: 2,
        name: '李四',
        avatar: '',
        status: 'lookAround',
        x:0,
        y:0,
      },
      {
        id: 3,
        name: '王五',
        avatar: '',
        status: 'offSeat',
        x:0,
        y:0,
      },
      {
        id: 4,
        name: '赵六',
        avatar: '',
        status: 'run',
        x:0,
        y:0,
      },
      {
        id: 5,
        name: '小红',
        avatar: '',
        status: 'sleeping',
        x:0,
        y:0,
      }
    ],
    behaviorStats: {
      offSeat: 5,
      stand:3,
      run:1,
      lookAround: 12,
      sleeping: 3
    },
    enableHotMap:true,
    enableAutoRemind: true,
    remindStudentId:1,
    remindIntensity:2
  }),
  actions: {
    updateSetting(payload) {
      if (payload.key in this.$state) {
        this[payload.key] = payload.value
      }
    },
    setDetectResult(data) {
      this.students[0].x = data[0].x
      this.students[0].y = data[0].y
    }
  }
})
