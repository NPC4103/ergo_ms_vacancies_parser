<script setup>
import { ref, onMounted, computed, onUnmounted } from 'vue'
import { 
  Briefcase, TrendingUp, MapPin, DollarSign, Clock, RefreshCw, Activity,
  Play, CheckCircle, XCircle, Loader, AlertTriangle, Plus, List, BarChart3,
  Calendar, Info
} from 'lucide-vue-next'
import { useRouter } from 'vue-router'
import { useParsingTasks } from '../composables/useParsingTasks'
import { useToast } from 'vue-toastification'
import TaskProgressBar from '../components/TaskProgressBar.vue'

const router = useRouter()
const toast = useToast()

const {
  tasks,
  loading: tasksLoading,
  loadTasks,
  activeTasks,
  finishedTasks
} = useParsingTasks()

const stats = ref(null)
const loading = ref(false)
let refreshInterval = null

// Статистика по задачам
const tasksStats = computed(() => {
  const tasksList = tasks.value || []
  const all = tasksList.length
  const running = tasksList.filter(t => t.status === 'running').length
  const completed = tasksList.filter(t => t.status === 'completed').length
  const failed = tasksList.filter(t => t.status === 'failed').length
  const paused = tasksList.filter(t => t.status === 'paused').length
  
  return {
    total: all,
    running,
    completed,
    failed,
    paused,
    success_rate: all > 0 ? Math.round((completed / all) * 100) : 0
  }
})

// Последние активные задачи
const recentActiveTasks = computed(() => {
  const tasksList = tasks.value || []
  return tasksList
    .filter(t => t.is_active)
    .sort((a, b) => new Date(b.started_at || b.created_at) - new Date(a.started_at || a.created_at))
    .slice(0, 5)
})

// Последние завершенные задачи
const recentFinishedTasks = computed(() => {
  const tasksList = tasks.value || []
  return tasksList
    .filter(t => t.is_finished)
    .sort((a, b) => new Date(b.completed_at || b.updated_at) - new Date(a.completed_at || a.updated_at))
    .slice(0, 5)
})

const loadDashboardData = async () => {
  loading.value = true
  try {
    // Загружаем задачи
    await loadTasks({ page_size: 50 })
    
    // Загружаем статистику вакансий (если нужно)
    // stats.value = await loadStats()
  } catch (error) {
    console.error('Ошибка загрузки данных дашборда:', error)
    toast.error('Ошибка загрузки данных дашборда')
  } finally {
    loading.value = false
  }
}

const statCards = computed(() => {
  return [
    {
      title: 'Всего задач',
      value: tasksStats.total,
      icon: List,
      gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      link: { name: 'VacanciesParser' },
      subtitle: `${tasksStats.completed} завершено`
    },
    {
      title: 'Активных задач',
      value: tasksStats.running,
      icon: Activity,
      gradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
      link: { name: 'VacanciesParser', query: { status: 'running' } },
      subtitle: `${tasksStats.paused} приостановлено`
    },
    {
      title: 'Успешных',
      value: tasksStats.completed,
      icon: CheckCircle,
      gradient: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
      link: { name: 'VacanciesParser', query: { status: 'completed' } },
      subtitle: `${tasksStats.success_rate}% успешность`
    },
    {
      title: 'С ошибками',
      value: tasksStats.failed,
      icon: XCircle,
      gradient: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
      link: { name: 'VacanciesParser', query: { status: 'failed' } },
      subtitle: tasksStats.failed > 0 ? 'Требуют внимания' : 'Все в порядке'
    }
  ]
})

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

function getSourceBadgeClass(source) {
  const classes = {
    'headhunter': 'vp-badge-danger',
    'habr_career': 'vp-badge-info',
    'superjob': 'vp-badge-success'
  }
  return classes[source] || 'vp-badge-secondary'
}

function navigateToTask(taskId) {
  router.push(`/vacancies-parser/tasks/${taskId}`)
}

function createTask() {
  router.push({ name: 'VacanciesParser' })
}

onMounted(() => {
  loadDashboardData()
  
  // Auto-refresh для активных задач (каждые 10 секунд)
  refreshInterval = setInterval(() => {
    if (recentActiveTasks.value.length > 0 && !loading.value) {
      loadDashboardData()
    }
  }, 10000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<template>
  <div class="vp-dashboard">
    <div class="vp-dashboard-header">
      <div>
        <h2 class="vp-dashboard-title">Панель управления парсингом</h2>
        <p class="vp-dashboard-subtitle">Мониторинг и управление задачами парсинга вакансий</p>
      </div>
      <div class="vp-dashboard-actions">
        <button 
          @click="createTask" 
          class="vp-btn-create"
        >
          <Plus :size="18" />
          Создать задачу
        </button>
        <button 
          @click="loadDashboardData" 
          class="vp-btn-refresh"
          :disabled="loading"
          :class="{ 'vp-loading': loading }"
        >
          <RefreshCw :size="18" />
        </button>
      </div>
    </div>

    <!-- Статистические карточки -->
    <div class="vp-stats-grid">
      <div 
        v-for="card in statCards" 
        :key="card.title"
        class="vp-stat-card"
        @click="card.link && router.push(card.link)"
      >
        <div class="vp-stat-icon" :style="{ background: card.gradient }">
          <component :is="card.icon" :size="24" />
        </div>
        <div class="vp-stat-content">
          <div class="vp-stat-label">{{ card.title }}</div>
          <div class="vp-stat-value">{{ card.value }}</div>
          <div v-if="card.subtitle" class="vp-stat-subtitle">{{ card.subtitle }}</div>
        </div>
      </div>
    </div>

    <!-- Активные задачи -->
    <div v-if="recentActiveTasks.length > 0" class="vp-section">
      <div class="vp-section-header">
        <div class="vp-section-title-group">
          <Loader :size="20" class="vp-text-primary" />
          <h3>Активные задачи</h3>
          <span class="vp-badge vp-badge-primary vp-badge-rounded">{{ recentActiveTasks.length }}</span>
        </div>
        <router-link 
          :to="{ name: 'VacanciesParser', query: { status: 'running' } }" 
          class="vp-section-link"
        >
          Все задачи →
        </router-link>
      </div>
      <div class="vp-tasks-list">
        <div 
          v-for="task in recentActiveTasks" 
          :key="task.id"
          class="vp-task-item"
          @click="navigateToTask(task.id)"
        >
          <div class="vp-task-item-header">
            <div class="vp-task-item-title-group">
              <h4 class="vp-task-item-title">{{ task.name || 'Задача без названия' }}</h4>
              <div class="vp-task-item-badges">
                <span class="vp-badge vp-badge-rounded" :class="getSourceBadgeClass(task.source)">
                  {{ task.source_display }}
                </span>
                <span class="vp-badge vp-badge-rounded" :class="getStatusBadgeClass(task.status)">
                  {{ task.status_display }}
                </span>
              </div>
            </div>
            <div class="vp-task-item-progress-value">
              {{ task.progress_percent }}%
            </div>
          </div>
          <TaskProgressBar :task="task" />
          <div class="vp-task-item-stats">
            <span class="vp-task-stat">
              <CheckCircle :size="14" class="vp-text-success" />
              {{ task.completed_items || 0 }} выполнено
            </span>
            <span class="vp-task-stat">
              <XCircle :size="14" :class="task.failed_items > 0 ? 'vp-text-danger' : 'vp-text-muted'" />
              {{ task.failed_items || 0 }} ошибок
            </span>
            <span class="vp-task-stat">
              <Clock :size="14" class="vp-text-info" />
              {{ (task.total_items || 0) - (task.completed_items || 0) - (task.failed_items || 0) }} осталось
            </span>
          </div>
          <div class="vp-task-item-footer">
            <span class="vp-text-muted vp-text-sm">
              Запущена: {{ formatRelativeTime(task.started_at || task.created_at) }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Информация о расписании -->
    <div class="vp-section">
      <div class="vp-section-header">
        <div class="vp-section-title-group">
          <Calendar :size="20" class="vp-text-info" />
          <h3>Расписание автоматического парсинга</h3>
        </div>
      </div>
      <div class="vp-schedule-info">
        <div class="vp-schedule-item">
          <div class="vp-schedule-time">02:00</div>
          <div class="vp-schedule-content">
            <div class="vp-schedule-title">Ежедневный парсинг за вчера и сегодня</div>
            <div class="vp-schedule-description">Полный парсинг всех технологий с максимальным покрытием</div>
          </div>
          <span class="vp-badge vp-badge-danger vp-badge-rounded">HeadHunter</span>
        </div>
        <div class="vp-schedule-item">
          <div class="vp-schedule-time">03:00</div>
          <div class="vp-schedule-content">
            <div class="vp-schedule-title">Глубокое сканирование топ-40</div>
            <div class="vp-schedule-description">Категории: языки программирования и фреймворки</div>
          </div>
          <span class="vp-badge vp-badge-danger vp-badge-rounded">HeadHunter</span>
        </div>
        <div class="vp-schedule-item">
          <div class="vp-schedule-time">06:15</div>
          <div class="vp-schedule-content">
            <div class="vp-schedule-title">Языки программирования (рабочие дни)</div>
            <div class="vp-schedule-description">Также в 12:15 и 18:15</div>
          </div>
          <span class="vp-badge vp-badge-danger vp-badge-rounded">HeadHunter</span>
        </div>
        <div class="vp-schedule-item">
          <div class="vp-schedule-time">07:30</div>
          <div class="vp-schedule-content">
            <div class="vp-schedule-title">Фреймворки (рабочие дни)</div>
            <div class="vp-schedule-description">Также в 13:30 и 19:30</div>
          </div>
          <span class="vp-badge vp-badge-danger vp-badge-rounded">HeadHunter</span>
        </div>
        <div class="vp-schedule-note">
          <Info :size="16" />
          <span>Расписание автоматически управляется Celery Beat. Все задачи выполняются в фоновом режиме.</span>
        </div>
      </div>
    </div>

    <!-- Последние завершенные задачи -->
    <div v-if="recentFinishedTasks.length > 0" class="vp-section">
      <div class="vp-section-header">
        <div class="vp-section-title-group">
          <BarChart3 :size="20" class="vp-text-success" />
          <h3>Последние завершенные задачи</h3>
          <span class="vp-badge vp-badge-success vp-badge-rounded">{{ recentFinishedTasks.length }}</span>
        </div>
        <router-link 
          :to="{ name: 'VacanciesParser', query: { status: 'completed' } }" 
          class="vp-section-link"
        >
          Все завершенные →
        </router-link>
      </div>
      <div class="vp-tasks-list">
        <div 
          v-for="task in recentFinishedTasks" 
          :key="task.id"
          class="vp-task-item vp-task-item-finished"
          @click="navigateToTask(task.id)"
        >
          <div class="vp-task-item-header">
            <div class="vp-task-item-title-group">
              <h4 class="vp-task-item-title">{{ task.name || 'Задача без названия' }}</h4>
              <div class="vp-task-item-badges">
                <span class="vp-badge vp-badge-rounded" :class="getSourceBadgeClass(task.source)">
                  {{ task.source_display }}
                </span>
                <span class="vp-badge vp-badge-rounded" :class="getStatusBadgeClass(task.status)">
                  {{ task.status_display }}
                </span>
              </div>
            </div>
            <div class="vp-task-item-progress-value vp-text-success">
              {{ task.progress_percent }}%
            </div>
          </div>
          <div class="vp-task-item-stats">
            <span class="vp-task-stat">
              <CheckCircle :size="14" class="vp-text-success" />
              {{ task.completed_items || 0 }} выполнено
            </span>
            <span class="vp-task-stat">
              <XCircle :size="14" :class="task.failed_items > 0 ? 'vp-text-danger' : 'vp-text-muted'" />
              {{ task.failed_items || 0 }} ошибок
            </span>
            <span class="vp-task-stat">
              <Briefcase :size="14" class="vp-text-primary" />
              {{ task.total_items || 0 }} всего
            </span>
          </div>
          <div class="vp-task-item-footer">
            <span class="vp-text-muted vp-text-sm">
              Завершена: {{ formatRelativeTime(task.completed_at || task.updated_at) }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Пустое состояние -->
    <div v-if="!loading && tasksStats.total === 0" class="vp-empty-state">
      <Briefcase :size="48" class="vp-empty-icon" />
      <h3 class="vp-empty-title">Нет задач парсинга</h3>
      <p class="vp-empty-text">Создайте первую задачу парсинга для начала работы</p>
      <button @click="createTask" class="vp-btn-create-empty">
        <Plus :size="18" />
        Создать задачу
      </button>
    </div>

    <!-- Загрузка -->
    <div v-if="loading && tasksStats.total === 0" class="vp-loading-state">
      <div class="vp-spinner"></div>
      <p class="vp-loading-text">Загрузка данных...</p>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@import '../scss/pages/dashboard';
</style>
