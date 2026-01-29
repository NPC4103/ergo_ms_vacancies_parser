<template>
  <div class="vp-task-progress">
    <div class="vp-progress-header">
      <span class="vp-progress-label">Прогресс</span>
      <span class="vp-progress-value">{{ task.progress_percent }}%</span>
    </div>
    <div class="vp-progress-bar">
      <div 
        class="vp-progress-fill" 
        :class="getProgressBarClass()"
        :style="{ width: task.progress_percent + '%' }"
        role="progressbar"
        :aria-valuenow="task.progress_percent"
        aria-valuemin="0"
        aria-valuemax="100"
      ></div>
    </div>
    <div class="vp-progress-info">
      {{ task.completed_items }} / {{ task.total_items }}
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  task: {
    type: Object,
    required: true
  }
})

function getProgressBarClass() {
  if (props.task.status === 'completed') {
    return 'vp-progress-success'
  } else if (props.task.status === 'failed') {
    return 'vp-progress-danger'
  } else if (props.task.status === 'paused') {
    return 'vp-progress-warning'
  } else if (props.task.status === 'running') {
    return 'vp-progress-primary vp-progress-animated'
  }
  return 'vp-progress-secondary'
}
</script>

<style lang="scss" scoped>
@import '../scss/components/task-progress';
</style>
