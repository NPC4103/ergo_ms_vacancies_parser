<template>
  <div class="vp-vacancies-results vp-container">
    <!-- Заголовок -->
    <div class="vp-page-header">
      <h2>
        <Briefcase :size="28" />
        Результаты парсинга вакансий
      </h2>
    </div>

    <!-- Фильтры -->
    <div class="vp-filters-card">
      <div class="vp-filters-grid">
        <div class="vp-filter-group">
          <Select
            v-model="filters.source"
            :options="sourceOptions"
            label="Источник"
            placeholder="Все источники"
            @change="applyFilters"
          />
        </div>
        
        <div class="vp-filter-group">
          <label>Компания</label>
          <input 
            v-model="filters.company" 
            type="text" 
            class="vp-filter-input" 
            placeholder="Название компании..."
            @input="debouncedSearch"
          >
        </div>
        
        <div class="vp-filter-group">
          <label>Город</label>
          <input 
            v-model="filters.area" 
            type="text" 
            class="vp-filter-input" 
            placeholder="Город..."
            @input="debouncedSearch"
          >
        </div>
        
        <div class="vp-filter-search">
          <label class="vp-filter-label">Поиск</label>
          <div>
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

    <!-- Статистика -->
    <div class="vp-stats-grid">
      <div class="vp-stat-card">
        <h3>{{ totalVacancies }}</h3>
        <div class="vp-stat-label">Всего вакансий</div>
      </div>
      <div class="vp-stat-card">
        <h3 class="vp-text-success">{{ activeVacancies }}</h3>
        <div class="vp-stat-label">Активных</div>
      </div>
      <div class="vp-stat-card">
        <h3 class="vp-text-primary">{{ todayVacancies }}</h3>
        <div class="vp-stat-label">Сегодня</div>
      </div>
      <div class="vp-stat-card">
        <h3 class="vp-text-info">{{ uniqueCompanies }}</h3>
        <div class="vp-stat-label">Компаний</div>
      </div>
    </div>

    <!-- Загрузка -->
    <div v-if="loading" class="vp-loading-state">
      <div class="vp-spinner"></div>
      <p class="vp-loading-text">Загрузка...</p>
    </div>

    <!-- Пустое состояние -->
    <div v-else-if="vacancies.length === 0" class="vp-alert vp-alert-info">
      <Info :size="20" class="vp-alert-icon" />
      <div class="vp-alert-content">
        Вакансий не найдено. Запустите парсинг для получения данных.
      </div>
    </div>

    <!-- Список вакансий -->
    <div v-else class="vp-vacancies-grid">
      <div 
        v-for="vacancy in vacancies" 
        :key="vacancy.id" 
        class="vp-vacancy-card"
        :class="getVacancyCardClass(vacancy)"
      >
        <div class="vp-vacancy-header">
          <h5 class="vp-vacancy-title">
            <a :href="vacancy.source_url" target="_blank" class="vp-link">
              {{ vacancy.title }}
              <ExternalLink :size="14" />
            </a>
          </h5>
        </div>

        <div class="vp-vacancy-body">
          <!-- Компания -->
          <div class="vp-vacancy-info">
            <Building2 :size="16" />
            {{ vacancy.company_name }}
          </div>

          <!-- Локация -->
          <div v-if="vacancy.area_name" class="vp-vacancy-info">
            <MapPin :size="16" />
            {{ vacancy.area_name }}
          </div>

          <!-- Зарплата -->
          <div v-if="vacancy.salary_display" class="vp-vacancy-salary">
            <DollarSign :size="16" />
            {{ vacancy.salary_display }}
          </div>

          <!-- Бейджи -->
          <div class="vp-vacancy-badges">
            <span class="vp-badge vp-badge-rounded" :class="getSourceBadgeClass(vacancy.source)">
              {{ vacancy.source_display }}
            </span>
            <span class="vp-badge vp-badge-rounded vp-badge-secondary">
              {{ vacancy.parsing_mode_display }}
            </span>
            <span v-if="vacancy.is_active" class="vp-badge vp-badge-rounded vp-badge-success">
              Активна
            </span>
          </div>
        </div>

        <div class="vp-vacancy-footer">
          <div class="vp-vacancy-date">
            <Clock :size="14" />
            {{ formatDate(vacancy.created_at) }}
          </div>
        </div>
      </div>
    </div>

    <!-- Пагинация -->
    <nav v-if="totalPages > 1" class="vp-pagination" aria-label="Навигация по вакансиям">
      <ul class="vp-pagination-list">
        <li class="vp-page-item">
          <a 
            class="vp-page-link" 
            :class="{ disabled: currentPage === 1 }"
            href="#" 
            @click.prevent="changePage(currentPage - 1)"
          >
            Назад
          </a>
        </li>
        <li 
          v-for="page in displayedPages" 
          :key="page" 
          class="vp-page-item"
        >
          <a 
            class="vp-page-link" 
            :class="{ active: page === currentPage }"
            href="#" 
            @click.prevent="changePage(page)"
          >
            {{ page }}
          </a>
        </li>
        <li class="vp-page-item">
          <a 
            class="vp-page-link" 
            :class="{ disabled: currentPage === totalPages }"
            href="#" 
            @click.prevent="changePage(currentPage + 1)"
          >
            Вперед
          </a>
        </li>
      </ul>
    </nav>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { 
  Briefcase, X, Info, ExternalLink, Building2, MapPin, 
  DollarSign, Clock
} from 'lucide-vue-next'
import { vacanciesApi } from '../js/api'
import { useToast } from 'vue-toastification'
import Select from './Select.vue'

const toast = useToast()

// State
const vacancies = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(18)
const totalCount = ref(0)

// Статистика
const totalVacancies = ref(0)
const activeVacancies = ref(0)
const todayVacancies = ref(0)
const uniqueCompanies = ref(0)

// Фильтры
const filters = ref({
  source: null,
  company: '',
  area: '',
  search: ''
})

const sourceOptions = [
  { value: null, label: 'Все источники' },
  { value: 'headhunter', label: 'HeadHunter' },
  { value: 'habr_career', label: 'Habr Career' },
  { value: 'superjob', label: 'SuperJob' }
]

function getVacancyCardClass(vacancy) {
  return {
    'vp-vacancy-headhunter': vacancy.source === 'headhunter',
    'vp-vacancy-habr': vacancy.source === 'habr_career',
    'vp-vacancy-superjob': vacancy.source === 'superjob'
  }
}

// Computed
const totalPages = computed(() => Math.ceil(totalCount.value / pageSize.value))

const displayedPages = computed(() => {
  const pages = []
  const maxPages = 7
  
  if (totalPages.value <= maxPages) {
    for (let i = 1; i <= totalPages.value; i++) {
      pages.push(i)
    }
  } else {
    const half = Math.floor(maxPages / 2)
    let start = Math.max(1, currentPage.value - half)
    let end = Math.min(totalPages.value, start + maxPages - 1)
    
    if (end - start < maxPages - 1) {
      start = Math.max(1, end - maxPages + 1)
    }
    
    for (let i = start; i <= end; i++) {
      pages.push(i)
    }
  }
  
  return pages
})

// Methods
async function loadVacancies() {
  loading.value = true
  
  try {
    const params = {
      page: currentPage.value,
      page_size: pageSize.value,
      source: filters.value.source,
      company_name__icontains: filters.value.company,
      area_name__icontains: filters.value.area,
      search: filters.value.search
    }
    
    // Удаляем пустые параметры
    Object.keys(params).forEach(key => {
      if (params[key] === null || params[key] === '') {
        delete params[key]
      }
    })
    
    const response = await vacanciesApi.list(params)

    // handleResponse возвращает { data: ..., success: ..., message: ... }
    const data = response.data || response
    vacancies.value = data.results || []
    totalCount.value = data.count || 0

  } catch (error) {
    console.error('Error loading vacancies:', error)
    toast.error('Ошибка загрузки вакансий')
  } finally {
    loading.value = false
  }
}

async function loadStatistics() {
  try {
    // handleResponse возвращает { data: ..., success: ..., message: ... }
    
    // Общее количество
    const allResponse = await vacanciesApi.list({ page_size: 1 })
    const allData = allResponse.data || allResponse
    totalVacancies.value = allData.count || 0
    
    // Активные
    const activeResponse = await vacanciesApi.list({ is_active: true, page_size: 1 })
    const activeData = activeResponse.data || activeResponse
    activeVacancies.value = activeData.count || 0
    
    // Сегодняшние
    const today = new Date().toISOString().split('T')[0]
    const todayResponse = await vacanciesApi.list({ 
      created_at__gte: today,
      page_size: 1 
    })
    const todayData = todayResponse.data || todayResponse
    todayVacancies.value = todayData.count || 0
    
    // Уникальные компании (примерная оценка)
    uniqueCompanies.value = Math.floor(totalVacancies.value / 3)
    
  } catch (error) {
    console.error('Error loading statistics:', error)
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

function formatDate(dateString) {
  if (!dateString) return '-'
  const date = new Date(dateString)
  return date.toLocaleDateString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  })
}

function changePage(page) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  loadVacancies()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function applyFilters() {
  currentPage.value = 1
  loadVacancies()
}

function resetFilters() {
  filters.value = {
    source: null,
    company: '',
    area: '',
    search: ''
  }
  currentPage.value = 1
  loadVacancies()
}

// Debounced search
let searchTimeout = null
const debouncedSearch = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    applyFilters()
  }, 500)
}

// Lifecycle
onMounted(() => {
  loadVacancies()
  loadStatistics()
})
</script>

<style lang="scss" scoped>
@import '../scss/pages/vacancies-results';
</style>
