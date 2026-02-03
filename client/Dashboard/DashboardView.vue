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

// Полное расписание Celery Beat для модуля vacancies_parser (HeadHunter + сервисные задачи)
const scheduleItems = [
  // Сервисные задачи модуля vacancies_parser
  {
    id: 'vacancies_parser-release-expired-leases',
    time: '*/5 мин',
    title: 'Crash recovery: освобождение зависших задач',
    description: 'Освобождает просроченные leases задач парсинга каждые 5 минут',
    queueLabel: 'VacanciesParser',
    queueVariant: 'info',
    frequency: 'Каждые 5 минут',
    frequencyVariant: 'info'
  },
  {
    id: 'vacancies_parser-monitor-tasks-progress',
    time: '*/10 мин',
    title: 'Мониторинг прогресса задач',
    description: 'Проверка состояния и прогресса задач парсинга каждые 10 минут',
    queueLabel: 'VacanciesParser',
    queueVariant: 'info',
    frequency: 'Каждые 10 минут',
    frequencyVariant: 'info'
  },
  // HeadHunter — ежедневные и месячные крупные задачи
  {
    id: 'hh-daily-yesterday-today',
    time: '02:00',
    title: 'Ежедневный парсинг за вчера и сегодня',
    description: 'Полный парсинг всех технологий за вчера и сегодня с максимальным покрытием',
    queueLabel: 'HeadHunter',
    queueVariant: 'danger',
    frequency: 'Ежедневно',
    frequencyVariant: 'info'
  },
  {
    id: 'hh-monthly-recursive',
    time: '01:00 (1 число)',
    title: 'Месячный рекурсивный парсинг',
    description: 'Глубокий парсинг за прошедший месяц с рекурсивной сегментацией по дням',
    queueLabel: 'HeadHunter',
    queueVariant: 'danger',
    frequency: 'Раз в месяц',
    frequencyVariant: 'info'
  },
  // Языки программирования — рабочие дни
  {
    id: 'hh-languages-workdays-morning',
    time: '06:15 (будни)',
    title: 'Языки программирования — утро',
    description: 'Категория LANG, до 2 страниц, рабочие дни утром',
    queueLabel: 'HeadHunter',
    queueVariant: 'danger',
    frequency: 'Пн–Пт, 06:15',
    frequencyVariant: 'info'
  },
  {
    id: 'hh-languages-workdays-noon',
    time: '12:15 (будни)',
    title: 'Языки программирования — день',
    description: 'Категория LANG, до 2 страниц, рабочие дни в обед',
    queueLabel: 'HeadHunter',
    queueVariant: 'danger',
    frequency: 'Пн–Пт, 12:15',
    frequencyVariant: 'info'
  },
  {
    id: 'hh-languages-workdays-evening',
    time: '18:15 (будни)',
    title: 'Языки программирования — вечер',
    description: 'Категория LANG, до 2 страниц, рабочие дни вечером',
    queueLabel: 'HeadHunter',
    queueVariant: 'danger',
    frequency: 'Пн–Пт, 18:15',
    frequencyVariant: 'info'
  },
  // Языки программирования — выходные
  {
    id: 'hh-languages-weekend-morning',
    time: '10:15 (выходные)',
    title: 'Языки программирования — утро (выходные)',
    description: 'Категория LANG, до 2 страниц, суббота и воскресенье утром',
    queueLabel: 'HeadHunter',
    queueVariant: 'danger',
    frequency: 'Сб–Вс, 10:15',
    frequencyVariant: 'info'
  },
  {
    id: 'hh-languages-weekend-evening',
    time: '18:15 (выходные)',
    title: 'Языки программирования — вечер (выходные)',
    description: 'Категория LANG, до 2 страниц, суббота и воскресенье вечером',
    queueLabel: 'HeadHunter',
    queueVariant: 'danger',
    frequency: 'Сб–Вс, 18:15',
    frequencyVariant: 'info'
  },
  // Фреймворки — рабочие дни
  {
    id: 'hh-frameworks-workdays-morning',
    time: '07:30 (будни)',
    title: 'Фреймворки — утро',
    description: 'Категория FRAMEWORK, до 2 страниц, рабочие дни утром',
    queueLabel: 'HeadHunter',
    queueVariant: 'danger',
    frequency: 'Пн–Пт, 07:30',
    frequencyVariant: 'info'
  },
  {
    id: 'hh-frameworks-workdays-noon',
    time: '13:30 (будни)',
    title: 'Фреймворки — день',
    description: 'Категория FRAMEWORK, до 2 страниц, рабочие дни в обед',
    queueLabel: 'HeadHunter',
    queueVariant: 'danger',
    frequency: 'Пн–Пт, 13:30',
    frequencyVariant: 'info'
  },
  {
    id: 'hh-frameworks-workdays-evening',
    time: '19:30 (будни)',
    title: 'Фреймворки — вечер',
    description: 'Категория FRAMEWORK, до 2 страниц, рабочие дни вечером',
    queueLabel: 'HeadHunter',
    queueVariant: 'danger',
    frequency: 'Пн–Пт, 19:30',
    frequencyVariant: 'info'
  },
  // Фреймворки — выходные
  {
    id: 'hh-frameworks-weekend-morning',
    time: '11:30 (выходные)',
    title: 'Фреймворки — утро (выходные)',
    description: 'Категория FRAMEWORK, до 2 страниц, суббота и воскресенье утром',
    queueLabel: 'HeadHunter',
    queueVariant: 'danger',
    frequency: 'Сб–Вс, 11:30',
    frequencyVariant: 'info'
  },
  {
    id: 'hh-frameworks-weekend-evening',
    time: '19:30 (выходные)',
    title: 'Фреймворки — вечер (выходные)',
    description: 'Категория FRAMEWORK, до 2 страниц, суббота и воскресенье вечером',
    queueLabel: 'HeadHunter',
    queueVariant: 'danger',
    frequency: 'Сб–Вс, 19:30',
    frequencyVariant: 'info'
  },
  // Базы данных
  {
    id: 'hh-databases-morning',
    time: '08:45',
    title: 'Базы данных — утро',
    description: 'Категория DB, 2 страницы, акцент на популярные СУБД',
    queueLabel: 'HeadHunter',
    queueVariant: 'danger',
    frequency: 'Ежедневно, 08:45',
    frequencyVariant: 'info'
  },
  {
    id: 'hh-databases-evening',
    time: '20:45',
    title: 'Базы данных — вечер',
    description: 'Категория DB, 2 страницы, вечерний прогон',
    queueLabel: 'HeadHunter',
    queueVariant: 'danger',
    frequency: 'Ежедневно, 20:45',
    frequencyVariant: 'info'
  },
  // Инструменты
  {
    id: 'hh-tools-daily',
    time: '14:00',
    title: 'Инструменты разработчика',
    description: 'Категория TOOL, утренний дневной прогон по инструментам',
    queueLabel: 'HeadHunter',
    queueVariant: 'danger',
    frequency: 'Ежедневно, 14:00',
    frequencyVariant: 'info'
  },
  // Облачные платформы
  {
    id: 'hh-platforms-nightly',
    time: '23:30',
    title: 'Облачные платформы — ночной парсинг',
    description: 'Категория PLATFORM, углублённый ночной прогон по облачным платформам',
    queueLabel: 'HeadHunter',
    queueVariant: 'danger',
    frequency: 'Ежедневно, 23:30',
    frequencyVariant: 'info'
  },
  // Пульс топ‑20
  {
    id: 'hh-top20-pulse-09',
    time: '09:00 (будни)',
    title: 'Пульс ТОП‑20 — утро',
    description: 'Топ‑20 технологий, лёгкий прогон без деталей',
    queueLabel: 'HeadHunter',
    queueVariant: 'danger',
    frequency: 'Пн–Пт, 09:00',
    frequencyVariant: 'info'
  },
  {
    id: 'hh-top20-pulse-12',
    time: '12:00 (будни)',
    title: 'Пульс ТОП‑20 — день',
    description: 'Топ‑20 технологий, дневной прогон',
    queueLabel: 'HeadHunter',
    queueVariant: 'danger',
    frequency: 'Пн–Пт, 12:00',
    frequencyVariant: 'info'
  },
  {
    id: 'hh-top20-pulse-15',
    time: '15:00 (будни)',
    title: 'Пульс ТОП‑20 — после обеда',
    description: 'Топ‑20 технологий, послеобеденный прогон',
    queueLabel: 'HeadHunter',
    queueVariant: 'danger',
    frequency: 'Пн–Пт, 15:00',
    frequencyVariant: 'info'
  },
  {
    id: 'hh-top20-pulse-18',
    time: '18:00 (будни)',
    title: 'Пульс ТОП‑20 — вечер',
    description: 'Топ‑20 технологий, вечерний прогон',
    queueLabel: 'HeadHunter',
    queueVariant: 'danger',
    frequency: 'Пн–Пт, 18:00',
    frequencyVariant: 'info'
  },
  {
    id: 'hh-top20-pulse-21',
    time: '21:00 (будни)',
    title: 'Пульс ТОП‑20 — поздний вечер',
    description: 'Топ‑20 технологий, финальный прогон дня',
    queueLabel: 'HeadHunter',
    queueVariant: 'danger',
    frequency: 'Пн–Пт, 21:00',
    frequencyVariant: 'info'
  },
  // Глубокие сканы и крупные задачи
  {
    id: 'hh-top40-deep-scan',
    time: '03:00',
    title: 'Глубокое сканирование ТОП‑40',
    description: 'Топ‑40 технологий по языкам и фреймворкам, ночной глубокий прогон',
    queueLabel: 'HeadHunter',
    queueVariant: 'danger',
    frequency: 'Ежедневно, 03:00',
    frequencyVariant: 'info'
  },
  {
    id: 'hh-weekly-comprehensive',
    time: '04:00 (вс)',
    title: 'Еженедельный полный парсинг',
    description: 'Полный парсинг по основным категориям (LANG, FRAMEWORK, DB, TOOL) ночью в воскресенье',
    queueLabel: 'HeadHunter',
    queueVariant: 'danger',
    frequency: 'Каждое воскресенье, 04:00',
    frequencyVariant: 'info'
  },
  {
    id: 'hh-check-vacancies-status',
    time: '05:00',
    title: 'Проверка статуса вакансий',
    description: 'Проверка актуальности существующих вакансий (batch‑обновление статусов)',
    queueLabel: 'HeadHunter',
    queueVariant: 'danger',
    frequency: 'Ежедневно, 05:00',
    frequencyVariant: 'info'
  },
  {
    id: 'hh-update-professional-roles',
    time: '06:30 (вс)',
    title: 'Актуализация профессиональных ролей',
    description: 'Обновление справочника профессиональных ролей раз в неделю',
    queueLabel: 'HeadHunter',
    queueVariant: 'danger',
    frequency: 'Каждое воскресенье, 06:30',
    frequencyVariant: 'info'
  },
  // Профессиональные роли
  {
    id: 'hh-professional-roles-comprehensive',
    time: '03:00 (пн)',
    title: 'Роли IT — полный прогон',
    description: 'Глубокий парсинг по всем IT‑ролям, понедельник ночью',
    queueLabel: 'HeadHunter',
    queueVariant: 'danger',
    frequency: 'Каждый понедельник, 03:00',
    frequencyVariant: 'info'
  },
  {
    id: 'hh-professional-roles-daily',
    time: '09:00 (вт–пт)',
    title: 'Роли IT — ежедневный прогон',
    description: 'Быстрый ежедневный прогон по IT‑ролям во вторник–пятницу утром',
    queueLabel: 'HeadHunter',
    queueVariant: 'danger',
    frequency: 'Вт–Пт, 09:00',
    frequencyVariant: 'info'
  },
  {
    id: 'hh-professional-roles-quick-scan',
    time: '14:30 (сб)',
    title: 'Роли IT — быстрый скан',
    description: 'Лёгкий субботний прогон по IT‑ролям без полного углубления',
    queueLabel: 'HeadHunter',
    queueVariant: 'danger',
    frequency: 'Каждая суббота, 14:30',
    frequencyVariant: 'info'
  }
]

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
  const s = tasksStats.value

  return [
    {
      title: 'Всего задач',
      value: s.total,
      icon: List,
      link: { name: 'VacanciesParser' },
      subtitle: `${s.completed} завершено`
    },
    {
      title: 'Активных задач',
      value: s.running,
      icon: Activity,
      link: { name: 'VacanciesParser', query: { status: 'running' } },
      subtitle: `${s.paused} приостановлено`
    },
    {
      title: 'Успешных',
      value: s.completed,
      icon: CheckCircle,
      link: { name: 'VacanciesParser', query: { status: 'completed' } },
      subtitle: `${s.success_rate}% успешность`
    },
    {
      title: 'С ошибками',
      value: s.failed,
      icon: XCircle,
      link: { name: 'VacanciesParser', query: { status: 'failed' } },
      subtitle: s.failed > 0 ? 'Требуют внимания' : 'Все в порядке'
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
        <div class="vp-stat-icon">
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
          <Calendar :size="20" class="vp-text-danger" />
          <h3>Расписание автоматического парсинга</h3>
          <span class="vp-text-muted vp-text-sm">Ключевые сценарии, которые Celery Beat запускает по расписанию</span>
        </div>
      </div>
      <div class="vp-schedule-info">
        <div 
          v-for="item in scheduleItems" 
          :key="item.id" 
          :class="['vp-schedule-item', item.queueVariant === 'danger' ? 'vp-schedule-item-danger' : 'vp-schedule-item-info']"
        >
          <div 
            class="vp-schedule-time"
            :class="item.queueVariant === 'danger' ? 'vp-text-danger' : 'vp-text-muted'"
          >
            {{ item.time }}
          </div>
          <div class="vp-schedule-content">
            <div class="vp-schedule-title">{{ item.title }}</div>
            <div class="vp-schedule-description">{{ item.description }}</div>
          </div>
          <div class="vp-schedule-meta">
            <span 
              class="vp-badge vp-badge-rounded" 
              :class="item.queueVariant === 'danger' ? 'vp-badge-danger' : 'vp-badge-secondary'"
            >
              {{ item.queueLabel }}
            </span>
            <span 
              v-if="item.frequency" 
              class="vp-badge vp-badge-rounded vp-badge-secondary"
            >
              {{ item.frequency }}
            </span>
          </div>
        </div>
        <div class="vp-schedule-note">
          <Info :size="16" />
          <span>Расписание автоматически управляется Celery Beat. Здесь показаны основные сценарии; внутри каждой точки запускается несколько отдельных задач в фоне.</span>
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
