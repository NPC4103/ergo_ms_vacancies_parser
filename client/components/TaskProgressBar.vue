<template>
  <div class="task-progress">
    <div class="d-flex justify-content-between align-items-center mb-1">
      <span class="small text-muted">Прогресс</span>
      <span class="small fw-bold">{{ task.progress_percent }}%</span>
    </div>
    <div class="progress" style="height: 8px;">
      <div 
        class="progress-bar" 
        :class="getProgressBarClass()"
        :style="{ width: task.progress_percent + '%' }"
        role="progressbar"
        :aria-valuenow="task.progress_percent"
        aria-valuemin="0"
        aria-valuemax="100"
      ></div>
    </div>
    <div class="small text-muted mt-1">
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
    return 'bg-success'
  } else if (props.task.status === 'failed') {
    return 'bg-danger'
  } else if (props.task.status === 'paused') {
    return 'bg-warning'
  } else if (props.task.status === 'running') {
    return 'bg-primary progress-bar-animated progress-bar-striped'
  }
  return 'bg-secondary'
}
</script>

<style scoped>
.progress {
  border-radius: 4px;
  overflow: hidden;
}

.progress-bar {
  transition: width 0.6s ease;
}
</style>
