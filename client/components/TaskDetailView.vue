<template>
  <div class="vp-task-detail">
    <!-- Загрузка -->
    <div v-if="loading" class="vp-loading-state">
      <div class="vp-spinner"></div>
      <p class="vp-loading-text">Загрузка...</p>
    </div>

    <!-- Ошибка -->
    <div v-else-if="error" class="vp-error-state">
      <AlertCircle :size="20" />
      {{ error }}
    </div>

    <!-- Детали задачи -->
    <div v-else-if="currentTask">
      <!-- Заголовок -->
      <div class="vp-page-header">
        <div>
          <button class="vp-back-button" @click="goBack">
            <ArrowLeft :size="16" />
            Назад к списку
          </button>
          <h2>{{ currentTask.name }}</h2>
          <div class="vp-task-badges">
            <span class="vp-badge vp-badge-rounded" :class="getSourceBadgeClass(currentTask.source)">
              {{ currentTask.source_display }}
            </span>
            <span class="vp-badge vp-badge-rounded vp-badge-secondary">
              {{ currentTask.parsing_mode_display }}
            </span>
            <span class="vp-badge vp-badge-rounded" :class="getStatusBadgeClass(currentTask.status)">
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
          <div class="vp-progress-card">
            <h5 class="vp-card-title">Прогресс выполнения</h5>
            <TaskProgressBar :task="currentTask" />
            
            <div v-if="taskProgress" class="vp-progress-stats">
              <div class="vp-progress-stat">
                <Clock :size="24" class="text-muted" />
                <div class="vp-stat-value">{{ taskProgress.pending }}</div>
                <div class="vp-stat-label">Ожидают</div>
              </div>
              <div class="vp-progress-stat">
                <Loader :size="24" class="text-primary" />
                <div class="vp-stat-value">{{ taskProgress.in_progress }}</div>
                <div class="vp-stat-label">В процессе</div>
              </div>
              <div class="vp-progress-stat">
                <CheckCircle :size="24" class="text-success" />
                <div class="vp-stat-value">{{ taskProgress.completed }}</div>
                <div class="vp-stat-label">Выполнено</div>
              </div>
              <div class="vp-progress-stat">
                <XCircle :size="24" class="text-danger" />
                <div class="vp-stat-value">{{ taskProgress.failed }}</div>
                <div class="vp-stat-label">Ошибки</div>
              </div>
              <div class="vp-progress-stat">
                <AlertTriangle :size="24" class="text-warning" />
                <div class="vp-stat-value">{{ taskProgress.blocked }}</div>
                <div class="vp-stat-label">Заблокировано</div>
              </div>
            </div>
          </div>
        </div>

        <div class="col-md-4">
          <div class="vp-info-card">
            <h5 class="vp-card-title">Информация</h5>
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

      <!-- Конфигурация -->
      <div class="vp-task-detail-section">
        <div class="vp-config-card">
            <div class="vp-card-header">
              <h5 class="vp-card-title">Конфигурация парсинга</h5>
              <button 
                class="vp-toggle-button"
                @click="showConfigRaw = !showConfigRaw"
              >
                {{ showConfigRaw ? 'Свернуть' : 'Развернуть JSON' }}
              </button>
            </div>
            
            <!-- Структурированное отображение конфигурации -->
            <div v-if="!showConfigRaw && currentTask.config" class="vp-config-structured">
              <div class="vp-config-grid">
                <div v-if="currentTask.config.area" class="vp-config-item">
                  <span class="vp-config-label">Регион:</span>
                  <span class="vp-config-value">{{ getAreaName(currentTask.config.area) }}</span>
                </div>
                <div v-if="currentTask.config.pages !== undefined" class="vp-config-item">
                  <span class="vp-config-label">Страниц:</span>
                  <span class="vp-config-value">{{ currentTask.config.pages }}</span>
                </div>
                <div v-if="currentTask.config.delay !== undefined" class="vp-config-item">
                  <span class="vp-config-label">Задержка:</span>
                  <span class="vp-config-value">{{ currentTask.config.delay }} сек</span>
                </div>
                <div v-if="currentTask.config.get_details !== undefined" class="vp-config-item">
                  <span class="vp-config-label">Детали:</span>
                  <span class="vp-config-value">{{ currentTask.config.get_details ? 'Да' : 'Нет' }}</span>
                </div>
                <div v-if="currentTask.config.text" class="vp-config-item">
                  <span class="vp-config-label">Поисковый запрос:</span>
                  <span class="vp-config-value">{{ currentTask.config.text }}</span>
                </div>
                <div v-if="currentTask.config.per_page" class="vp-config-item">
                  <span class="vp-config-label">На странице:</span>
                  <span class="vp-config-value">{{ currentTask.config.per_page }}</span>
                </div>
              </div>
            </div>
            
            <!-- Raw JSON -->
            <div v-if="showConfigRaw" class="vp-config-raw">
              <pre><code>{{ JSON.stringify(currentTask.config, null, 2) }}</code></pre>
            </div>
          </div>
        </div>

      <!-- Статистика -->
      <div v-if="currentTask.is_finished" class="vp-task-detail-section">
        <div class="vp-statistics-card">
            <div class="vp-card-header">
              <h5 class="vp-card-title">
                <BarChart2 :size="20" />
                Статистика выполнения
              </h5>
              <button 
                class="vp-refresh-button" 
                @click="loadStatistics"
                :disabled="loadingStats"
              >
                <RefreshCw :size="16" :class="{ 'vp-spin': loadingStats }" />
                Загрузить статистику
              </button>
            </div>
            
            <div v-if="statistics" class="vp-statistics-grid">
              <div class="vp-statistic-item">
                <div class="vp-stat-value">{{ statistics.items_per_second }}</div>
                <div class="vp-stat-label">items/sec</div>
              </div>
              <div class="vp-statistic-item">
                <div class="vp-stat-value">{{ statistics.avg_item_duration_ms }}ms</div>
                <div class="vp-stat-label">среднее время</div>
              </div>
              <div class="vp-statistic-item">
                <div class="vp-stat-value">{{ statistics.success_rate }}%</div>
                <div class="vp-stat-label">успешность</div>
              </div>
              <div class="vp-statistic-item">
                <div class="vp-stat-value">{{ formatDuration(statistics.duration_seconds) }}</div>
                <div class="vp-stat-label">длительность</div>
              </div>
            </div>
          </div>
        </div>

      <!-- Ошибка -->
      <div v-if="currentTask.error_message" class="vp-alert vp-alert-danger">
        <AlertCircle :size="20" class="vp-alert-icon" />
        <div class="vp-alert-content">
          <div class="vp-alert-title">Ошибка выполнения:</div>
          <div>{{ currentTask.error_message }}</div>
        </div>
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
import { tasksApi } from '../js/api'
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
const showConfigRaw = ref(false)
let refreshInterval = null

// Methods
function goBack() {
  router.push('/vacancies-parser')
}

function getSourceBadgeClass(source) {
  const classes = {
    'headhunter': 'vp-badge-danger',
    'habr_career': 'vp-badge-info',
    'superjob': 'vp-badge-success'
  }
  return classes[source] || 'vp-badge-secondary'
}

function getStatusBadgeClass(status) {
  const classes = {
    'created': 'vp-badge-secondary',
    'running': 'vp-badge-primary',
    'paused': 'vp-badge-warning',
    'stopped': 'vp-badge-secondary',
    'completed': 'vp-badge-success',
    'failed': 'vp-badge-danger'
  }
  return classes[status] || 'vp-badge-secondary'
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

function getAreaName(areaId) {
  const areas = {
    1: 'Москва',
    2: 'Санкт-Петербург',
    66: 'Нижний Новгород',
    88: 'Казань',
    113: 'Россия (все регионы)'
  }
  return areas[areaId] || `ID: ${areaId}`
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
    const taskId = route.params.id
    const response = await tasksApi.getStatistics(taskId)

    // apiClient возвращает объект формата { success, data, message, status }
    if (response && response.success && response.data) {
      statistics.value = response.data
    } else {
      // Если success === false, логируем сообщение, чтобы было видно причину
      console.error('Statistics response error:', response?.message || 'unknown error')
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

<style lang="scss" scoped>
@import '../scss/pages/task-detail';
</style>
