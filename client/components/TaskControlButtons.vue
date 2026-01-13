<template>
  <div class="task-control-buttons btn-group" role="group">
    <!-- Детали -->
    <button 
      class="btn btn-sm btn-outline-primary" 
      :title="'Детали'"
      @click="goToDetails"
    >
      <Eye :size="16" />
    </button>

    <!-- Pause -->
    <button 
      v-if="task.status === 'running'" 
      class="btn btn-sm btn-outline-warning" 
      :title="'Приостановить'"
      @click="$emit('pause', task)"
    >
      <Pause :size="16" />
    </button>

    <!-- Resume -->
    <button 
      v-if="task.status === 'paused'" 
      class="btn btn-sm btn-outline-success" 
      :title="'Возобновить'"
      @click="$emit('resume', task)"
    >
      <Play :size="16" />
    </button>

    <!-- Stop -->
    <button 
      v-if="task.is_active" 
      class="btn btn-sm btn-outline-danger" 
      :title="'Остановить'"
      @click="$emit('stop', task)"
    >
      <Square :size="16" />
    </button>

    <!-- Delete -->
    <button 
      v-if="task.is_finished" 
      class="btn btn-sm btn-outline-danger" 
      :title="'Удалить'"
      @click="$emit('delete', task)"
    >
      <Trash2 :size="16" />
    </button>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { Eye, Pause, Play, Square, Trash2 } from 'lucide-vue-next'

const props = defineProps({
  task: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['pause', 'resume', 'stop', 'delete'])
const router = useRouter()

function goToDetails() {
  router.push(`/vacancies-parser/tasks/${props.task.id}`)
}
</script>

<style scoped>
.task-control-buttons button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
</style>
