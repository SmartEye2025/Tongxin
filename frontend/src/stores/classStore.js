import { defineStore } from 'pinia'

export const classStore = defineStore('class', {
  state: () => ({
    students: [],
    enableHotMap:true,
    enableAutoRemind: true,
    remindStudentId:{ value: ['0'], timestamp: Date.now() },
    remindIntensity:2
  }),
  actions: {
    updateValue(payload) {
      console.log(payload)
      if (payload.key in this.$state) {
        this[payload.key] = payload.value
      }
    },
    setDetectResult(data) {
      // 更新学生状态
      Object.keys(data).forEach(key => {
        for(let i=0;i<this.students.length;i++){
          if (this.students[i].id === key){
            this.students[i].x = data[key].x;
            this.students[i].y = data[key].y;
            this.students[i].status = data[key].status;
          }
        }
      })
    }
  }
})
