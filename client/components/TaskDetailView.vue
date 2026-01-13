<template>
  <div class="task-detail-view container-fluid">
    <!-- Загрузка -->
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Загрузка...</span>
      </div>
    </div>

    <!-- Ошибка -->
    <div v-else-if="error" class="alert alert-danger">
      <AlertCircle :size="20" class="me-2" />
      {{ error }}
    </div>

    <!-- Детали задачи -->
    <div v-else-if="currentTask">
      <!-- Заголовок -->
      <div class="d-flex justify-content-between align-items-center mb-4">
        <div>
          <button class="btn btn-outline-secondary btn-sm mb-2" @click="goBack">
            <ArrowLeft :size="16" class="me-1" />
            Назад к списку
          </button>
          <h2 class="mb-0">{{ currentTask.name }}</h2>
          <div class="text-muted mt-1">
            <span class="badge" :class="getSourceBadgeClass(currentTask.source)">
              {{ currentTask.source_display }}
            </span>
            <span class="badge bg-secondary ms-1">
              {{ currentTask.parsing_mode_display }}
            </span>
            <span class="badge ms-1" :class="getStatusBadgeClass(currentTask.status)">
              {{ currentTask.status_display }}
            </span>
          </div>
        </div>
        
        <TaskControlButtons 
          :task="currentTask" 
          @pause="handlePause"
          @resume="handleResume"
          @stop="handleStop"
        />
      </div>

      <!-- Прогресс -->
      <div class="row mb-4">
        <div class="col-md-8">
          <div class="card">
            <div class="card-body">
              <h5 class="card-title">Прогресс выполнения</h5>
              <TaskProgressBar :task="currentTask" />
              
              <div v-if="taskProgress" class="mt-3">
                <div class="row text-center">
                  <div class="col">
                    <Clock :size="24" class="text-muted mb-2" />
                    <div class="h4 mb-0">{{ taskProgress.pending }}</div>
                    <div class="small text-muted">Ожидают</div>
                  </div>
                  <div class="col">
                    <Loader :size="24" class="text-primary mb-2" />
                    <div class="h4 mb-0">{{ taskProgress.in_progress }}</div>
                    <div class="small text-muted">В процессе</div>
                  </div>
                  <div class="col">
                    <CheckCircle :size="24" class="text-success mb-2" />
                    <div class="h4 mb-0">{{ taskProgress.completed }}</div>
                    <div class="small text-muted">Выполнено</div>
                  </div>
                  <div class="col">
                    <XCircle :size="24" class="text-danger mb-2" />
                    <div class="h4 mb-0">{{ taskProgress.failed }}</div>
                    <div class="small text-muted">Ошибки</div>
                  </div>
                  <div class="col">
                    <AlertTriangle :size="24" class="text-warning mb-2" />
                    <div class="h4 mb-0">{{ taskProgress.blocked }}</div>
                    <div class="small text-muted">Заблокировано</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="col-md-4">
          <div class="card">
            <div class="card-body">
              <h5 class="card-title">Информация</h5>
              <dl class="row mb-0 small">
                <dt class="col-sm-6">ID задачи:</dt>
                <dd class="col-sm-6">{{ currentTask.id }}</dd>
                
                <dt class="col-sm-6">Создана:</dt>
                <dd class="col-sm-6">{{ formatDate(currentTask.created_at) }}</dd>
                
                <dt class="col-sm-6" v-if="currentTask.started_at">Запущена:</dt>
                <dd class="col-sm-6" v-if="currentTask.started_at">{{ formatDate(currentTask.started_at) }}</dd>
                
                <dt class="col-sm-6" v-if="currentTask.completed_at">Завершена:</dt>
                <dd class="col-sm-6" v-if="currentTask.completed_at">{{ formatDate(currentTask.completed_at) }}</dd>
                
                <dt class="col-sm-6">Автор:</dt>
                <dd class="col-sm-6">{{ currentTask.created_by_username || 'Система' }}</dd>
              </dl>
            </div>
          </div>
        </div>
      </div>

      <!-- Конфигурация -->
      <div class="row mb-4">
        <div class="col-md-12">
          <div class="card">
            <div class="card-body">
              <h5 class="card-title">Конфигурация парсинга</h5>
              <pre class="bg-light p-3 rounded"><code>{{ JSON.stringify(currentTask.config, null, 2) }}</code></pre>
            </div>
          </div>
        </div>
      </div>

      <!-- Статистика -->
      <div v-if="currentTask.is_finished" class="row mb-4">
        <div class="col-md-12">
          <div class="card">
            <div class="card-body">
              <h5 class="card-title">
                <BarChart2 :size="20" class="me-2" />
                Статистика выполнения
              </h5>
              <button 
                class="btn btn-sm btn-outline-primary" 
                @click="loadStatistics"
                :disabled="loadingStats"
              >
                <RefreshCw :size="16" :class="{ 'spin': loadingStats }" class="me-1" />
                Загрузить статистику
              </button>
              
              <div v-if="statistics" class="mt-3">
                <div class="row">
                  <div class="col-md-3">
                    <div class="text-center">
                      <div class="h5">{{ statistics.items_per_second }}</div>
                      <div class="small text-muted">items/sec</div>
                    </div>
                  </div>
                  <div class="col-md-3">
                    <div class="text-center">
                      <div class="h5">{{ statistics.avg_item_duration_ms }}ms</div>
                      <div class="small text-muted">среднее время</div>
                    </div>
                  </div>
                  <div class="col-md-3">
                    <div class="text-center">
                      <div class="h5">{{ statistics.success_rate }}%</div>
                      <div class="small text-muted">успешность</div>
                    </div>
                  </div>
                  <div class="col-md-3">
                    <div class="text-center">
                      <div class="h5">{{ formatDuration(statistics.duration_seconds) }}</div>
                      <div class="small text-muted">длительность</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Ошибка -->
      <div v-if="currentTask.error_message" class="alert alert-danger">
        <AlertCircle :size="20" class="me-2" />
        <strong>Ошибка выполнения:</strong>
        <div class="mt-2">{{ currentTask.error_message }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft, AlertCircle, Clock, Loader, CheckCircle, XCircle, 
  AlertTriangle, BarChart2, RefreshCw
} from 'lucide-vue-next'
import { useParsingTasks } from '../composables/useParsingTasks'
import { statisticsApi } from '../js/api'
import TaskProgressBar from './TaskProgressBar.vue'
import TaskControlButtons from './TaskControlButtons.vue'

const route = useRoute()
const router = useRouter()

const {
  currentTask,
  taskProgress,
  loading,
  error,
  loadTask,
  loadTaskProgress,
  pauseTask,
  resumeTask,
  stopTask
} = useParsingTasks()

// Local state
const statistics = ref(null)
const loadingStats = ref(false)
let refreshInterval = null

// Methods
function goBack() {
  router.push('/vacancies-parser')
}

function getSourceBadgeClass(source) {
  const classes = {
    'headhunter': 'bg-danger',
    'habr_career': 'bg-info',
    'superjob': 'bg-success'
  }
  return classes[source] || 'bg-secondary'
}

function getStatusBadgeClass(status) {
  const classes = {
    'created': 'bg-secondary',
    'running': 'bg-primary',
    'paused': 'bg-warning',
    'stopped': 'bg-dark',
    'completed': 'bg-success',
    'failed': 'bg-danger'
  }
  return classes[status] || 'bg-secondary'
}

function formatDate(dateString) {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

function formatDuration(seconds) {
  if (!seconds) return '-'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  return `${hours}ч ${minutes}м ${secs}с`
}

async function handlePause(task) {
  await pauseTask(task.id)
  await loadTask(task.id)
}

async function handleResume(task) {
  await resumeTask(task.id)
  await loadTask(task.id)
}

async function handleStop(task) {
  await stopTask(task.id)
  await loadTask(task.id)
}

async function loadStatistics() {
  loadingStats.value = true
  try {
    const response = await statisticsApi.list({ task: route.params.id })
    if (response.results && response.results.length > 0) {
      statistics.value = response.results[0]
    }
  } catch (err) {
    console.error('Error loading statistics:', err)
  } finally {
    loadingStats.value = false
  }
}

async function refresh() {
  const taskId = route.params.id
  await loadTask(taskId)
  await loadTaskProgress(taskId)
}

// Lifecycle
onMounted(async () => {
  const taskId = route.params.id
  await loadTask(taskId)
  await loadTaskProgress(taskId)
  
  // Auto-refresh каждые 5 секунд для active задач
  refreshInterval = setInterval(() => {
    if (currentTask.value && currentTask.value.is_active) {
      refresh()
    }
  }, 5000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

pre {
  max-height: 300px;
  overflow-y: auto;
}
</style>
