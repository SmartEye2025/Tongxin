import { defineStore} from "pinia";
import request from "@/utils/request.js";

export const studentStore = defineStore("classStore", {
  state(){
    return {
      studentList:[],
      // student_id: '',
      // uwb_id:'',
      // name:'',
      // age:0,
      // speciality:'',
      // seat_x:0,
      // seat_y:0,
    }
  },
  getters: {

  },
  actions:{
    async fetch_studentList(){
      try {
        const response = await request.get("/get_studentList/");
        this.studentList = response.studentList;
        return response.studentList;
      } catch (err) {
        console.log('error:',err.message);
        return null;
      } finally {
        console.log('complete');
      }
    },
    async edit_studentInfo(studentInfo){
      try {
        this.studentList = this.studentList.map(element =>
          element.student_id === studentInfo.student_id
            ? { ...element, ...studentInfo } // 合并属性（保留未修改的字段）
            : element
        );
        await request.post("/edit_studentInfo/",studentInfo);
      } catch (err) {
        console.log('error:',err.message);
      } finally {
        console.log('complete');
      }
    },
    async add_student(studentInfo){
      try {
        await request.post("/add_student/",studentInfo);
      } catch (err) {
        console.log('error:',err.message);
      } finally {
        console.log('complete');
      }
    },
    delete_student(student_id){
      try {
        const id = this.studentList.findIndex((element) => element.student_id === student_id);
        if (id !== -1) {
          this.studentList.splice(id, 1); // 从 id 位置删除 1 个元素
          request.post("/delete_student/",{student_id:student_id});
        } else {
          console.warn(`未找到 student_id=${student_id} 的学生`);
        }
      } catch (err) {
        console.log('error:',err.message);
      } finally {
        console.log('complete');
      }
    },
  }
})
