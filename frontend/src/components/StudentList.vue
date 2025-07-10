<template>
  <div class="student-list">
    <h3>学生列表</h3>
    <v-list>
      <v-list-item
        v-for="student in students"
        :key="student.id"
        @click="emitRemind(student.id)"
      >
        <v-list-item-avatar>
          <v-img :src="student.avatar" />
        </v-list-item-avatar>

        <v-list-item-content>
          <v-list-item-title>{{ student.name }}</v-list-item-title>
          <v-list-item-subtitle>
            状态: {{ getBehaviorStatus(student.id) }}
          </v-list-item-subtitle>
        </v-list-item-content>

        <v-list-item-action>
          <v-btn icon @click.stop="emitRemind(student.id)">
            <v-icon color="red">mdi-vibrate</v-icon>
          </v-btn>
        </v-list-item-action>
      </v-list-item>
    </v-list>
  </div>
</template>

<script>
export default {
  props: {
    students: {
      type: Array,
      required: true
    },
    behaviors: {
      type: Object,
      default: () => ({})
    }
  },
  methods: {
    emitRemind(studentId) {
      this.$emit('remind-student', studentId)
    },
    getBehaviorStatus(studentId) {
      const behavior = this.behaviors[studentId]
      return behavior ? behavior.type : '正常'
    }
  }
}
</script>
