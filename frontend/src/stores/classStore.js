import { defineStore} from "pinia";

export const classStore = defineStore("classStore", {
  state(){
    return {
      classId: null,
      students: ['1','2','3','4','5','6','7','8','9'],
      behaviors: [
        {
          date:12,
          stats: {
            '站立': 4,
            '走动': 5,
            '跑动': 21
          }
        },
        {
          date:13,
          stats: {
            '站立': 32,
            '走动': 2,
            '跑动': 13
          }
        },
        {
          date:14,
          stats: {
            '站立': 12,
            '走动': 32,
            '跑动': 21
          }
        }
      ],
    }
  },
  getters: {
    getBehaviorData:(state)=>(range)=> {
      if (range==='today'){
        return state.behaviors[0].stats
      }
      else if (range==='week'){
        let result = {}
        state.behaviors.slice(0,2).forEach(item => {
          Object.keys(item.stats).forEach(key => {
            if (!Object.prototype.hasOwnProperty.call(result, key)) {
              result[key] = item.stats[key]
            }
            else{
              result[key] += item.stats[key]
            }
          })
        })
        return result
      }
      else{
        let result = {}
        state.behaviors.forEach(item => {
          Object.keys(item.stats).forEach(key => {
            if (!Object.prototype.hasOwnProperty.call(result, key)) {
              result[key] = item.stats[key]
            }
            else{
              result[key] += item.stats[key]
            }
          })
        })
        return result
      }
    },
  },
  actions:{

  }
})
