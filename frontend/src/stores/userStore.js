import { defineStore} from "pinia";

export const userStore = defineStore("classStore", {
  state(){
    return {
      user_id: null,
      account:'',
      password:'',
      is_login:false,
    }
  },
  getters: {
    getLoginStatus(){
      return this.is_login
    }
  },
  actions:{
    login(account,password){
      this.account = account;
      this.password = password;
      this.is_login=!this.is_login
    }
  }
})
