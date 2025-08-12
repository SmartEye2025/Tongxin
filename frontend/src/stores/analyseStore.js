// stores/analyseStore.js
import { defineStore } from 'pinia'

export const analyseStore = defineStore('timeRange', {
  state: () => ({
    range: '本周', // 默认值
    selectedId: '-1',
    availableRanges: ['本周','上周','本月','自定义']
  }),
})
