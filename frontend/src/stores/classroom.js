const state = {
  currentClass: null,
  students: [],
  alerts: [],
  stats: {
    attendance: 0,
    focusRate: 0,
    abnormalCount: 0
  }
}

const mutations = {
  SET_CLASS_DATA(state, payload) {
    state.currentClass = payload.classInfo
    state.students = payload.students
    state.stats = payload.stats
  },
  ADD_ALERT(state, alert) {
    state.alerts.unshift(alert)
    state.stats.abnormalCount++
  },
  UPDATE_STUDENT(state, student) {
    const index = state.students.findIndex(s => s.id === student.id)
    if (index !== -1) {
      state.students.splice(index, 1, student)
    }
  }
}

const actions = {
  async fetchClassData({ commit }, classId) {
    try {
      const response = await api.getClassData(classId)
      commit('SET_CLASS_DATA', response.data)
    } catch (error) {
      console.error('Failed to fetch class data:', error)
    }
  },
  handleBehaviorAlert({ commit }, alertData) {
    commit('ADD_ALERT', {
      ...alertData,
      timestamp: new Date()
    })

    // 更新学生状态
    commit('UPDATE_STUDENT', {
      id: alertData.studentId,
      isAbnormal: true,
      status: alertData.behaviorType
    })

    // 5秒后恢复正常状态
    setTimeout(() => {
      commit('UPDATE_STUDENT', {
        id: alertData.studentId,
        isAbnormal: false
      })
    }, 5000)
  }
}

export default {
  namespaced: true,
  state,
  mutations,
  actions
}
