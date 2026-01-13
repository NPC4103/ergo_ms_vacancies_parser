<template>
  <div class="vacancies-parser-tasks container-fluid">
    <!-- Заголовок и кнопка создания -->
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2 class="mb-0">
        <FileText class="me-2" :size="28" />
        Задачи парсинга вакансий
      </h2>
      <button class="btn btn-primary" @click="showCreateModal = true">
        <Plus :size="20" class="me-1" />
        Создать задачу
      </button>
    </div>

    <!-- Фильтры -->
    <div class="card mb-4">
      <div class="card-body">
        <div class="row g-3">
          <div class="col-md-3">
            <label class="form-label">Источник</label>
            <select v-model="filters.source" class="form-select" @change="applyFilters">
              <option :value="null">Все источники</option>
              <option value="headhunter">HeadHunter</option>
              <option value="habr_career">Habr Career</option>
              <option value="superjob">SuperJob</option>
            </select>
          </div>
          
          <div class="col-md-3">
            <label class="form-label">Режим парсинга</label>
            <select v-model="filters.parsing_mode" class="form-select" @change="applyFilters">
              <option :value="null">Все режимы</option>
              <option value="api">API режим</option>
              <option value="html">HTML режим</option>
            </select>
          </div>
          
          <div class="col-md-3">
            <label class="form-label">Статус</label>
            <select v-model="filters.status" class="form-select" @change="applyFilters">
              <option :value="null">Все статусы</option>
              <option value="created">Создана</option>
              <option value="running">Выполняется</option>
              <option value="paused">Приостановлена</option>
              <option value="stopped">Остановлена</option>
              <option value="completed">Завершена</option>
              <option value="failed">Ошибка</option>
            </select>
          </div>
          
          <div class="col-md-3">
            <label class="form-label">Поиск</label>
            <div class="input-group">
              <input 
                v-model="filters.search" 
                type="text" 
                class="form-control" 
                placeholder="Поиск по названию..."
                @input="debouncedSearch"
              >
              <button class="btn btn-outline-secondary" type="button" @click="resetFilters">
                <X :size="18" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Список задач -->
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Загрузка...</span>
      </div>
    </div>

    <div v-else-if="error" class="alert alert-danger">
      <AlertCircle :size="20" class="me-2" />
      {{ error }}
    </div>

    <div v-else-if="!hasTasks" class="alert alert-info">
      <Info :size="20" class="me-2" />
      Задач не найдено. Создайте первую задачу парсинга.
    </div>

    <div v-else class="row">
      <div v-for="task in tasks" :key="task.id" class="col-12 mb-3">
        <div class="card task-card shadow-sm" :class="getTaskCardClass(task)">
          <div class="card-body">
            <!-- Заголовок задачи -->
            <div class="d-flex justify-content-between align-items-start mb-3">
              <div class="flex-grow-1">
                <h5 class="card-title mb-2">
                  <router-link 
                    :to="`/vacancies-parser/tasks/${task.id}`" 
                    class="text-decoration-none text-dark fw-bold"
                  >
                    {{ task.name || 'Задача без названия' }}
                  </router-link>
                </h5>
                
                <!-- Бейджи -->
                <div class="mb-2">
                  <span class="badge rounded-pill" :class="getSourceBadgeClass(task.source)">
                    {{ task.source_display }}
                  </span>
                  <span class="badge rounded-pill bg-secondary ms-1">
                    {{ task.parsing_mode_display }}
                  </span>
                  <span class="badge rounded-pill ms-1" :class="getStatusBadgeClass(task.status)">
                    <component :is="getStatusIcon(task.status)" :size="12" class="me-1" />
                    {{ task.status_display }}
                  </span>
                </div>
              </div>
              
              <!-- Кнопки управления -->
              <div class="ms-3">
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
            <div class="mb-3">
              <div class="d-flex justify-content-between align-items-center mb-1">
                <span class="small text-muted">
                  <TrendingUp :size="14" class="me-1" />
                  Прогресс выполнения
                </span>
                <span class="small fw-bold" :class="getProgressColor(task.progress_percent)">
                  {{ task.progress_percent }}%
                </span>
              </div>
              <TaskProgressBar :task="task" />
            </div>

            <!-- Статистика -->
            <div class="row g-2 mb-3">
              <!-- Всего -->
              <div class="col-6 col-md-3">
                <div class="d-flex align-items-center p-2 bg-light rounded">
                  <Database :size="18" class="text-primary me-2" />
                  <div>
                    <div class="small text-muted">Всего</div>
                    <div class="fw-bold">{{ task.total_items || 0 }}</div>
                  </div>
                </div>
              </div>
              
              <!-- Выполнено -->
              <div class="col-6 col-md-3">
                <div class="d-flex align-items-center p-2 bg-light rounded">
                  <CheckCircle :size="18" class="text-success me-2" />
                  <div>
                    <div class="small text-muted">Выполнено</div>
                    <div class="fw-bold text-success">{{ task.completed_items || 0 }}</div>
                  </div>
                </div>
              </div>
              
              <!-- Ошибки -->
              <div class="col-6 col-md-3">
                <div class="d-flex align-items-center p-2 bg-light rounded">
                  <XCircle :size="18" :class="task.failed_items > 0 ? 'text-danger' : 'text-muted'" class="me-2" />
                  <div>
                    <div class="small text-muted">Ошибки</div>
                    <div class="fw-bold" :class="task.failed_items > 0 ? 'text-danger' : 'text-muted'">
                      {{ task.failed_items || 0 }}
                    </div>
                  </div>
                </div>
              </div>
              
              <!-- Осталось -->
              <div class="col-6 col-md-3">
                <div class="d-flex align-items-center p-2 bg-light rounded">
                  <Clock :size="18" class="text-info me-2" />
                  <div>
                    <div class="small text-muted">Осталось</div>
                    <div class="fw-bold text-info">
                      {{ (task.total_items || 0) - (task.completed_items || 0) - (task.failed_items || 0) }}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Дополнительная информация -->
            <div class="d-flex justify-content-between align-items-center text-muted small border-top pt-2">
              <div>
                <Calendar :size="14" class="me-1" />
                Создана: {{ formatDate(task.created_at) }}
              </div>
              <div v-if="task.started_at">
                <Play :size="14" class="me-1" />
                Запущена: {{ formatRelativeTime(task.started_at) }}
              </div>
              <div v-if="task.completed_at">
                <CheckCircle2 :size="14" class="me-1" />
                Завершена: {{ formatRelativeTime(task.completed_at) }}
              </div>
              <div v-if="task.created_by_username">
                <User :size="14" class="me-1" />
                {{ task.created_by_username }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Пагинация -->
    <nav v-if="pagination.total > pagination.pageSize" aria-label="Навигация по задачам">
      <ul class="pagination justify-content-center">
        <li class="page-item" :class="{ disabled: pagination.page === 1 }">
          <a class="page-link" href="#" @click.prevent="changePage(pagination.page - 1)">
            Назад
          </a>
        </li>
        <li 
          v-for="page in totalPages" 
          :key="page" 
          class="page-item" 
          :class="{ active: page === pagination.page }"
        >
          <a class="page-link" href="#" @click.prevent="changePage(page)">
            {{ page }}
          </a>
        </li>
        <li class="page-item" :class="{ disabled: pagination.page === totalPages }">
          <a class="page-link" href="#" @click.prevent="changePage(pagination.page + 1)">
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
    'border-primary': task.status === 'running',
    'border-warning': task.status === 'paused',
    'border-success': task.status === 'completed',
    'border-danger': task.status === 'failed'
  }
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
  if (percent >= 100) return 'text-success'
  if (percent >= 75) return 'text-info'
  if (percent >= 50) return 'text-primary'
  if (percent >= 25) return 'text-warning'
  return 'text-secondary'
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

<style scoped>
/* Улучшенные стили для карточек задач */
.task-card {
  transition: all 0.3s ease;
  border-left: 4px solid transparent;
}

.task-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
}

.task-card.border-primary {
  border-left-color: #0d6efd !important;
  background: linear-gradient(to right, rgba(13, 110, 253, 0.03), transparent);
}

.task-card.border-success {
  border-left-color: #198754 !important;
  background: linear-gradient(to right, rgba(25, 135, 84, 0.03), transparent);
}

.task-card.border-danger {
  border-left-color: #dc3545 !important;
  background: linear-gradient(to right, rgba(220, 53, 69, 0.03), transparent);
}

.task-card.border-warning {
  border-left-color: #ffc107 !important;
  background: linear-gradient(to right, rgba(255, 193, 7, 0.03), transparent);
}

.task-card.border-dark {
  border-left-color: #212529 !important;
  background: linear-gradient(to right, rgba(33, 37, 41, 0.03), transparent);
}

.task-card .card-title a {
  transition: color 0.2s ease;
}

.task-card .card-title a:hover {
  color: #0d6efd !important;
}

.badge {
  font-size: 0.85rem;
}

.badge.rounded-pill {
  padding: 0.35em 0.75em;
  font-weight: 500;
}

.bg-light {
  background-color: #f8f9fa !important;
  border-radius: 0.375rem;
  transition: background-color 0.2s ease;
}

.bg-light:hover {
  background-color: #e9ecef !important;
}

/* Анимация для иконки Loader в статусе running */
.badge.bg-primary svg {
  animation: spin 2s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Адаптивность */
@media (max-width: 768px) {
  .task-card .row > div {
    margin-bottom: 1rem;
  }
  
  .task-card .text-end {
    text-align: left !important;
  }
  
  .task-card .col-6:nth-child(odd) {
    padding-right: 0.5rem;
  }
  
  .task-card .col-6:nth-child(even) {
    padding-left: 0.5rem;
  }
}
</style>
