<template>
  <div class="student-management">
    <div class="management-header">
      <h2>学生管理</h2>
      <div class="search-bar">
        <input v-model="searchQuery" placeholder="搜索学生姓名或ID">
        <button @click="addStudent">添加学生</button>
      </div>
    </div>

    <!-- 学生表格 -->
    <div class="student-table">
      <table>
        <thead>
          <tr>
            <th>学号</th>
            <th>UWB定位编号</th>
            <th>班级</th>
            <th>姓名</th>
            <th>年龄</th>
            <th>座位</th>
            <th>特殊需求</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="student in filteredStudents" :key="student.id">
            <td>{{ student.student_id }}</td>
            <td>{{ student.uwb_id }}</td>
            <td>{{ student.class_id }}</td>
            <td>{{ student.name }}</td>
            <td>{{ student.age }}</td>
            <td>[{{ student.seat_x }},{{student.seat_y}}]</td>
            <td>
              <span class="special-needs">{{ student.specialNeeds.join(', ') }}</span>
            </td>
            <td class="actions">
              <button @click="editStudent(student)">编辑</button>
              <button @click="deleteStudent(student.student_id)">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 学生编辑对话框 -->
    <dialog ref="studentDialog">
      <h3>{{ editingStudent ? '编辑学生信息' : '添加新学生' }}</h3>
      <form @submit.prevent="saveStudent">
        <div class="form-row">
          <div class="form-group">
            <label>学号</label>
            <input v-model="currentStudent.student_id" required>
          </div>
          <div class="form-group">
            <label>UWB编号</label>
            <input v-model="currentStudent.uwb_id" required>
          </div>
          <div class="form-group">
            <label>班级</label>
            <input v-model="currentStudent.class_id" required>
          </div>
          <div class="form-group">
            <label>姓名</label>
            <input v-model="currentStudent.name" required>
          </div>
          <div class="form-group">
            <label>年龄</label>
            <input v-model="currentStudent.age" type="number">
          </div>
          <div class="form-group">
            <label>座位x坐标</label>
            <input v-model="currentStudent.seat_x" type="number">
          </div>
          <div class="form-group">
            <label>座位y坐标</label>
            <input v-model="currentStudent.seat_y" type="number">
          </div>
        </div>

        <div class="form-group">
          <label>特殊需求</label>
          <div class="special-needs-select">
            <label v-for="need in allSpecialNeeds" :key="need">
              <input type="checkbox" v-model="currentStudent.specialNeeds" :value="need">
              {{ need }}
            </label>
          </div>
        </div>

        <div class="dialog-actions">
          <button type="button" @click="closeStudentDialog">取消</button>
          <button type="submit">保存</button>
        </div>
      </form>
    </dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import {studentStore} from "@/stores/studentStore.js";

const allSpecialNeeds = ref(['自闭症', '多动症', '学习障碍', '言语障碍', '情绪障碍']);

const students = ref([]);

const searchQuery = ref('');
const studentDialog = ref(null);
const editingStudent = ref(false);
const currentStudent = ref({
  student_id: '',
  uwb_id: '',
  class_id:'',
  name: '',
  age: '',
  seat_x: '',
  seat_y: '',
  specialNeeds: [],
});

const filteredStudents = computed(() => {
  const query = searchQuery.value.toLowerCase();
  return students.value.filter(student =>
    student.name.toLowerCase().includes(query) ||
    student.student_id.toLowerCase().includes(query)
  );
});

const addStudent = () => {
  currentStudent.value = {
    student_id: '',
    uwb_id: '',
    class_id:'',
    name: '',
    age: '',
    seat_x: '',
    seat_y: '',
    specialNeeds: [],
  };
  editingStudent.value = false;
  studentDialog.value.showModal();
};

const editStudent = (student) => {
  currentStudent.value = { ...student };
  editingStudent.value = true;
  studentDialog.value.showModal();
};

const deleteStudent = (student_id) => {
  const isConfirmed = confirm("确定要删除该学生吗？");
  if (isConfirmed) {
    studentStore().delete_student(student_id);
    const id = students.value.findIndex((s) => s.student_id === student_id);
    if (id !== -1) students.value.splice(id, 1);
  } else {
    console.log("取消删除");
  }

};

const saveStudent = () => {
  if (editingStudent.value) {
    // 更新学生信息
    const index = students.value.findIndex(s => s.student_id === currentStudent.value.student_id);
    students.value[index] = { ...currentStudent.value };
    studentStore().edit_studentInfo(currentStudent.value);
  } else {
    // 添加新学生
    students.value.push({ ...currentStudent.value });
    studentStore().add_student(currentStudent.value);
  }
  closeStudentDialog();
};

const closeStudentDialog = () => {
  studentDialog.value.close();
};

onMounted(()=>{
  studentStore().fetch_studentList().then(studentList => {
  if (studentList) {
    console.log("获取到学生列表:", studentList);
    students.value = studentList;
  } else {
    console.log("获取学生列表失败");
  }
});
})
</script>

<style scoped>
.student-management {
  padding: 20px;
}

.management-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.search-bar {
  display: flex;
  gap: 10px;
}

.search-bar input {
  padding: 8px 12px;
  border: 1px solid #DCDFE6;
  border-radius: 4px;
  width: 250px;
}

.search-bar button {
  padding: 8px 16px;
  background: #409EFF;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.student-table {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  padding: 12px 15px;
  text-align: left;
  border-bottom: 1px solid #ebeef5;
}

th {
  background-color: #f5f7fa;
  font-weight: 600;
  color: #303133;
}

.special-needs {
  background: #f0f9eb;
  color: #67C23A;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 0.85em;
}

.actions {
  display: flex;
  gap: 8px;
}

.actions button {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.85em;
}

.actions button:first-child {
  background: #E6A23C;
  color: white;
}

.actions button:last-child {
  background: #d83500;
  color: white;
}

dialog {
  border: none;
  border-radius: 8px;
  padding: 20px;
  width: fit-content;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.form-row {
  display: flex;
  gap: 15px;
  margin-bottom: 15px;
}

.form-row .form-group {
  flex: 1;
}

.form-group {
  margin-bottom: 15px;
}

.form-group label {
  display: block;
  margin-bottom: 5px;
  font-weight: bold;
}

.form-group input, .form-group select {
  width: 100%;
  padding: 8px;
  border: 1px solid #DCDFE6;
  border-radius: 4px;
}

.special-needs-select {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.special-needs-select label {
  display: flex;
  align-items: center;
  gap: 5px;
  font-weight: normal;
  cursor: pointer;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}

.dialog-actions button {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.dialog-actions button:first-child {
  background: #F56C6C;
  color: white;
}

.dialog-actions button:last-child {
  background: #67C23A;
  color: white;
}
</style>
