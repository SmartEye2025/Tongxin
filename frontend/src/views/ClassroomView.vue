<template>
  <div class="classroom-management">
    <h2>教室管理</h2>

    <!-- 教室列表 -->
    <div class="classroom-list">
      <div v-for="room in classrooms" :key="room.id" class="classroom-card">
        <div class="room-info">
          <h3>{{ room.name }}</h3>
          <p>容量: {{ room.capacity }}人</p>
          <p>设备状态:
            <span :class="{'status-active': room.status === 'active',
                          'status-inactive': room.status !== 'active'}">
              {{ room.status === 'active' ? '正常' : '维护中' }}
            </span>
          </p>
        </div>
        <div class="room-actions">
          <button @click="editClassroom(room)">编辑</button>
          <button @click="monitorClassroom(room.id)">实时监控</button>
        </div>
      </div>
    </div>

    <!-- 添加/编辑教室对话框 -->
    <dialog ref="classroomDialog">
      <h3>{{ editingRoom ? '编辑教室' : '添加教室' }}</h3>
      <form @submit.prevent="saveClassroom">
        <div class="form-group">
          <label>教室名称</label>
          <input v-model="currentRoom.name" required>
        </div>
        <div class="form-group">
          <label>教室容量</label>
          <input v-model="currentRoom.capacity" type="number" required>
        </div>
        <div class="form-group">
          <label>状态</label>
          <select v-model="currentRoom.status">
            <option value="active">正常</option>
            <option value="maintenance">维护中</option>
          </select>
        </div>
        <div class="dialog-actions">
          <button type="button" @click="closeDialog">取消</button>
          <button type="submit">保存</button>
        </div>
      </form>
    </dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const classrooms = ref([
  { id: 1, name: '阳光教室', capacity: 15, status: 'active' },
  { id: 2, name: '彩虹教室', capacity: 12, status: 'active' },
  { id: 3, name: '星星教室', capacity: 10, status: 'maintenance' }
]);

const classroomDialog = ref(null);
const editingRoom = ref(false);
const currentRoom = ref({
  id: null,
  name: '',
  capacity: 10,
  status: 'active'
});

const editClassroom = (room) => {
  currentRoom.value = { ...room };
  editingRoom.value = true;
  classroomDialog.value.showModal();
};

const monitorClassroom = (roomId) => {
  // 跳转到教室监控页面
  console.log('监控教室:', roomId);
};

const saveClassroom = () => {
  if (editingRoom.value) {
    // 更新教室
    const index = classrooms.value.findIndex(r => r.id === currentRoom.value.id);
    classrooms.value[index] = { ...currentRoom.value };
  } else {
    // 添加教室
    const newId = Math.max(...classrooms.value.map(r => r.id)) + 1;
    classrooms.value.push({ ...currentRoom.value, id: newId });
  }
  closeDialog();
};

const closeDialog = () => {
  classroomDialog.value.close();
  resetForm();
};

const resetForm = () => {
  currentRoom.value = {
    id: null,
    name: '',
    capacity: 10,
    status: 'active'
  };
  editingRoom.value = false;
};
</script>

<style scoped>
.classroom-management {
  padding: 20px;
}

.classroom-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

.classroom-card {
  background: white;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  display: flex;
  flex-direction: column;
}

.room-info h3 {
  margin-top: 0;
  color: #333;
}

.status-active {
  color: #67C23A;
}

.status-inactive {
  color: #F56C6C;
}

.room-actions {
  margin-top: auto;
  display: flex;
  gap: 10px;
  padding-top: 15px;
}

.room-actions button {
  flex: 1;
  padding: 8px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.room-actions button:first-child {
  background: #E6A23C;
  color: white;
}

.room-actions button:last-child {
  background: #409EFF;
  color: white;
}

dialog {
  border: none;
  border-radius: 8px;
  padding: 20px;
  width: 400px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
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
