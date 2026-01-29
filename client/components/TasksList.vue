<template>
  <div class="vp-tasks-list-page">
    <!-- Заголовок и кнопка создания -->
    <div class="vp-page-header">
      <h2>
        <FileText :size="28" />
        Задачи парсинга вакансий
      </h2>
      <button class="vp-btn-create" @click="showCreateModal = true">
        <Plus :size="20" />
        Создать задачу
      </button>
    </div>

    <!-- Фильтры -->
    <div class="vp-filters-card">
      <div class="vp-filters-grid">
        <div class="vp-filter-group">
          <label>Источник</label>
          <select v-model="filters.source" class="vp-filter-control" @change="applyFilters">
            <option :value="null">Все источники</option>
            <option value="headhunter">HeadHunter</option>
            <option value="habr_career">Habr Career</option>
            <option value="superjob">SuperJob</option>
          </select>
        </div>
        
        <div class="vp-filter-group">
          <label>Режим парсинга</label>
          <select v-model="filters.parsing_mode" class="vp-filter-control" @change="applyFilters">
            <option :value="null">Все режимы</option>
            <option value="api">API режим</option>
            <option value="html">HTML режим</option>
          </select>
        </div>
        
        <div class="vp-filter-group">
          <label>Статус</label>
          <select v-model="filters.status" class="vp-filter-control" @change="applyFilters">
            <option :value="null">Все статусы</option>
            <option value="created">Создана</option>
            <option value="running">Выполняется</option>
            <option value="paused">Приостановлена</option>
            <option value="stopped">Остановлена</option>
            <option value="completed">Завершена</option>
            <option value="failed">Ошибка</option>
          </select>
        </div>
        
        <div class="vp-filter-search">
          <label>Поиск</label>
          <div style="position: relative;">
            <input 
              v-model="filters.search" 
              type="text" 
              class="vp-filter-input" 
              placeholder="Поиск по названию..."
              @input="debouncedSearch"
            >
            <button class="vp-filter-clear" type="button" @click="resetFilters">
              <X :size="18" />
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Список задач -->
    <div v-if="loading" class="vp-loading-state">
      <div class="vp-spinner"></div>
      <p class="vp-loading-text">Загрузка...</p>
    </div>

    <div v-else-if="error" class="vp-error-state">
      <AlertCircle :size="20" />
      {{ error }}
    </div>

    <div v-else-if="!hasTasks" class="vp-empty-state">
      <Info :size="48" class="vp-empty-icon" />
      <h3 class="vp-empty-title">Задач не найдено</h3>
      <p class="vp-empty-text">Создайте первую задачу парсинга.</p>
    </div>

    <div v-else class="vp-tasks-grid">
      <div 
        v-for="task in tasks" 
        :key="task.id"
        class="vp-task-card"
        :class="getTaskCardClass(task)"
      >
        <!-- Заголовок задачи -->
        <div class="vp-task-header">
          <div class="vp-task-title-group">
            <h5 class="vp-task-title">
              <router-link 
                :to="`/vacancies-parser/tasks/${task.id}`" 
                class="vp-link"
              >
                {{ task.name || 'Задача без названия' }}
              </router-link>
            </h5>
            
            <!-- Бейджи -->
            <div class="vp-task-badges">
              <span class="vp-badge vp-badge-rounded" :class="getSourceBadgeClass(task.source)">
                {{ task.source_display }}
              </span>
              <span class="vp-badge vp-badge-rounded vp-badge-secondary">
                {{ task.parsing_mode_display }}
              </span>
              <span class="vp-badge vp-badge-rounded" :class="getStatusBadgeClass(task.status)">
                <component :is="getStatusIcon(task.status)" :size="12" />
                {{ task.status_display }}
              </span>
            </div>
          </div>
          
          <!-- Кнопки управления -->
          <div class="vp-task-actions">
            <TaskControlButtons 
              :task="task" 
              @pause="handlePause"
              @resume="handleResume"
              @stop="handleStop"
              @delete="handleDelete"
            />
          </div>
        </div>

        <!-- Прогресс-бар -->
        <div class="vp-task-progress-section">
          <div class="vp-task-progress-header">
            <span class="vp-text-sm vp-text-muted">
              <TrendingUp :size="14" />
              Прогресс выполнения
            </span>
            <span class="vp-text-sm vp-font-weight-semibold" :class="getProgressColor(task.progress_percent)">
              {{ task.progress_percent }}%
            </span>
          </div>
          <TaskProgressBar :task="task" />
        </div>

        <!-- Статистика -->
        <div class="vp-task-stats-grid">
          <!-- Всего -->
          <div class="vp-task-stat-item">
            <Database :size="18" class="vp-text-primary" />
            <div>
              <div class="vp-stat-label">Всего</div>
              <div class="vp-stat-value">{{ task.total_items || 0 }}</div>
            </div>
          </div>
          
          <!-- Выполнено -->
          <div class="vp-task-stat-item">
            <CheckCircle :size="18" class="vp-text-success" />
            <div>
              <div class="vp-stat-label">Выполнено</div>
              <div class="vp-stat-value vp-text-success">{{ task.completed_items || 0 }}</div>
            </div>
          </div>
          
          <!-- Ошибки -->
          <div class="vp-task-stat-item">
            <XCircle :size="18" :class="task.failed_items > 0 ? 'vp-text-danger' : 'vp-text-muted'" />
            <div>
              <div class="vp-stat-label">Ошибки</div>
              <div class="vp-stat-value" :class="task.failed_items > 0 ? 'vp-text-danger' : 'vp-text-muted'">
                {{ task.failed_items || 0 }}
              </div>
            </div>
          </div>
          
          <!-- Осталось -->
          <div class="vp-task-stat-item">
            <Clock :size="18" class="vp-text-info" />
            <div>
              <div class="vp-stat-label">Осталось</div>
              <div class="vp-stat-value vp-text-info">
                {{ (task.total_items || 0) - (task.completed_items || 0) - (task.failed_items || 0) }}
              </div>
            </div>
          </div>
        </div>

        <!-- Дополнительная информация -->
        <div class="vp-task-footer">
          <div>
            <Calendar :size="14" />
            Создана: {{ formatDate(task.created_at) }}
          </div>
          <div v-if="task.started_at">
            <Play :size="14" />
            Запущена: {{ formatRelativeTime(task.started_at) }}
          </div>
          <div v-if="task.completed_at">
            <CheckCircle2 :size="14" />
            Завершена: {{ formatRelativeTime(task.completed_at) }}
          </div>
          <div v-if="task.created_by_username">
            <User :size="14" />
            {{ task.created_by_username }}
          </div>
        </div>
      </div>
    </div>

    <!-- Пагинация -->
    <nav v-if="pagination.total > pagination.pageSize" class="vp-pagination" aria-label="Навигация по задачам">
      <ul class="vp-pagination-list">
        <li class="vp-page-item">
          <a 
            class="vp-page-link" 
            :class="{ disabled: pagination.page === 1 }"
            href="#" 
            @click.prevent="changePage(pagination.page - 1)"
          >
            Назад
          </a>
        </li>
        <li 
          v-for="page in totalPages" 
          :key="page" 
          class="vp-page-item"
        >
          <a 
            class="vp-page-link" 
            :class="{ active: page === pagination.page }"
            href="#" 
            @click.prevent="changePage(page)"
          >
            {{ page }}
          </a>
        </li>
        <li class="vp-page-item">
          <a 
            class="vp-page-link" 
            :class="{ disabled: pagination.page === totalPages }"
            href="#" 
            @click.prevent="changePage(pagination.page + 1)"
          >
            Вперед
          </a>
        </li>
      </ul>
    </nav>

    <!-- Модальное окно создания задачи -->
    <CreateTaskModal 
      v-if="showCreateModal" 
      @close="showCreateModal = false"
      @created="handleTaskCreated"
      @task-created="handleTaskCreated"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { 
  FileText, Plus, X, AlertCircle, Info, CheckCircle, XCircle, Clock,
  Database, Calendar, Play, CheckCircle2, User, TrendingUp, Circle,
  Loader, Pause, StopCircle, AlertTriangle
} from 'lucide-vue-next'
import { useParsingTasks } from '../composables/useParsingTasks'
import TaskProgressBar from './TaskProgressBar.vue'
import TaskControlButtons from './TaskControlButtons.vue'
import CreateTaskModal from './CreateTaskModal.vue'
import { useToast } from 'vue-toastification'

const router = useRouter()
const toast = useToast()

// Composable
const {
  tasks,
  loading,
  error,
  pagination,
  filters,
  hasTasks,
  loadTasks,
  pauseTask,
  resumeTask,
  stopTask,
  deleteTask,
  setFilters,
  resetFilters,
  changePage
} = useParsingTasks()

// Local state
const showCreateModal = ref(false)
let refreshInterval = null

// Computed
const totalPages = computed(() => Math.ceil(pagination.value.total / pagination.value.pageSize))

// Debounced search
let searchTimeout = null
const debouncedSearch = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    applyFilters()
  }, 500)
}

// Methods
function applyFilters() {
  setFilters(filters.value)
}

function getTaskCardClass(task) {
  return {
    'vp-task-running': task.status === 'running',
    'vp-task-paused': task.status === 'paused',
    'vp-task-completed': task.status === 'completed',
    'vp-task-failed': task.status === 'failed'
  }
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
    minute: '2-digit'
  })
}

function formatRelativeTime(dateString) {
  if (!dateString) return '-'
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now - date
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMins / 60)
  const diffDays = Math.floor(diffHours / 24)
  
  if (diffMins < 1) return 'только что'
  if (diffMins < 60) return `${diffMins} мин назад`
  if (diffHours < 24) return `${diffHours} ч назад`
  if (diffDays < 7) return `${diffDays} д назад`
  
  return formatDate(dateString)
}

function getStatusIcon(status) {
  const icons = {
    'created': Circle,
    'running': Loader,
    'paused': Pause,
    'stopped': StopCircle,
    'completed': CheckCircle,
    'failed': AlertTriangle
  }
  return icons[status] || Circle
}

function getProgressColor(percent) {
  if (percent >= 100) return 'vp-text-success'
  if (percent >= 75) return 'vp-text-info'
  if (percent >= 50) return 'vp-text-primary'
  if (percent >= 25) return 'vp-text-warning'
  return 'vp-text-secondary'
}

async function handlePause(task) {
  await pauseTask(task.id)
}

async function handleResume(task) {
  await resumeTask(task.id)
}

async function handleStop(task) {
  await stopTask(task.id)
}

async function handleDelete(task) {
  // Используем простое подтверждение (ConfirmDialog требует дополнительной настройки)
  if (window.confirm(`Удалить задачу "${task.name}"?`)) {
    await deleteTask(task.id)
  }
}

async function handleTaskCreated() {
  showCreateModal.value = false
  // Перезагружаем список задач
  await loadTasks()
  toast.success('Список задач обновлен')
}

// Lifecycle
onMounted(() => {
  loadTasks()
  
  // Auto-refresh для running задач (каждые 10 секунд)
  refreshInterval = setInterval(() => {
    const hasRunningTasks = tasks.value.some(t => t.is_active)
    if (hasRunningTasks && !loading.value) {
      loadTasks()
    }
  }, 10000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
  if (searchTimeout) {
    clearTimeout(searchTimeout)
  }
})
</script>

<style lang="scss" scoped>
@import '../scss/pages/tasks-list';
</style>
