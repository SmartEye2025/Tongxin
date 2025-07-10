// stores/timeRangeStore.js
import { defineStore } from 'pinia'

export const timeRangeStore = defineStore('timeRange', {
  state: () => ({
    range: 'week', // 默认值
    availableRanges: [
      { label: '今日', value: 'day' },
      { label: '本周', value: 'week' },
      { label: '本月', value: 'month' },
      { label: '自定义', value: 'custom' }
    ]
  }),
  actions: {
    setRange(newRange) {
      this.range = newRange
    }
  },
  getters: {
    timeRangeLabel: (state) => {
      const rangeMap = {
        day: '今日',
        week: '本周',
        month: '本月',
        custom: '自定义'
      }
      return rangeMap[state.range] || '周'
    }
  }
})
