<template>
  <div class="vacancies-results container-fluid">
    <!-- Заголовок -->
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h2 class="mb-0">
        <Briefcase class="me-2" :size="28" />
        Результаты парсинга вакансий
      </h2>
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
            <label class="form-label">Компания</label>
            <input 
              v-model="filters.company" 
              type="text" 
              class="form-control" 
              placeholder="Название компании..."
              @input="debouncedSearch"
            >
          </div>
          
          <div class="col-md-3">
            <label class="form-label">Город</label>
            <input 
              v-model="filters.area" 
              type="text" 
              class="form-control" 
              placeholder="Город..."
              @input="debouncedSearch"
            >
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

    <!-- Статистика -->
    <div class="row mb-4">
      <div class="col-md-3">
        <div class="card text-center">
          <div class="card-body">
            <h3 class="mb-0">{{ totalVacancies }}</h3>
            <small class="text-muted">Всего вакансий</small>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card text-center">
          <div class="card-body">
            <h3 class="mb-0 text-success">{{ activeVacancies }}</h3>
            <small class="text-muted">Активных</small>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card text-center">
          <div class="card-body">
            <h3 class="mb-0 text-primary">{{ todayVacancies }}</h3>
            <small class="text-muted">Сегодня</small>
          </div>
        </div>
      </div>
      <div class="col-md-3">
        <div class="card text-center">
          <div class="card-body">
            <h3 class="mb-0 text-info">{{ uniqueCompanies }}</h3>
            <small class="text-muted">Компаний</small>
          </div>
        </div>
      </div>
    </div>

    <!-- Загрузка -->
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Загрузка...</span>
      </div>
    </div>

    <!-- Список вакансий -->
    <div v-else-if="vacancies.length === 0" class="alert alert-info">
      <Info :size="20" class="me-2" />
      Вакансий не найдено. Запустите парсинг для получения данных.
    </div>

    <div v-else class="row">
      <div v-for="vacancy in vacancies" :key="vacancy.id" class="col-md-6 col-lg-4 mb-3">
        <div class="card vacancy-card h-100">
          <div class="card-body">
            <!-- Заголовок -->
            <h5 class="card-title">
              <a :href="vacancy.source_url" target="_blank" class="text-decoration-none">
                {{ vacancy.title }}
                <ExternalLink :size="14" class="ms-1" />
              </a>
            </h5>

            <!-- Компания -->
            <p class="text-muted mb-2">
              <Building2 :size="16" class="me-1" />
              {{ vacancy.company_name }}
            </p>

            <!-- Локация -->
            <p class="text-muted mb-2" v-if="vacancy.area_name">
              <MapPin :size="16" class="me-1" />
              {{ vacancy.area_name }}
            </p>

            <!-- Зарплата -->
            <p class="fw-bold text-success mb-3" v-if="vacancy.salary_display">
              <DollarSign :size="16" class="me-1" />
              {{ vacancy.salary_display }}
            </p>

            <!-- Бейджи -->
            <div class="mb-3">
              <span class="badge" :class="getSourceBadgeClass(vacancy.source)">
                {{ vacancy.source_display }}
              </span>
              <span class="badge bg-secondary ms-1">
                {{ vacancy.parsing_mode_display }}
              </span>
              <span v-if="vacancy.is_active" class="badge bg-success ms-1">
                Активна
              </span>
            </div>

            <!-- Дата -->
            <small class="text-muted">
              <Clock :size="14" class="me-1" />
              {{ formatDate(vacancy.created_at) }}
            </small>
          </div>
        </div>
      </div>
    </div>

    <!-- Пагинация -->
    <nav v-if="totalPages > 1" aria-label="Навигация по вакансиям">
      <ul class="pagination justify-content-center">
        <li class="page-item" :class="{ disabled: currentPage === 1 }">
          <a class="page-link" href="#" @click.prevent="changePage(currentPage - 1)">
            Назад
          </a>
        </li>
        <li 
          v-for="page in displayedPages" 
          :key="page" 
          class="page-item" 
          :class="{ active: page === currentPage }"
        >
          <a class="page-link" href="#" @click.prevent="changePage(page)">
            {{ page }}
          </a>
        </li>
        <li class="page-item" :class="{ disabled: currentPage === totalPages }">
          <a class="page-link" href="#" @click.prevent="changePage(currentPage + 1)">
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
    
    console.log('Vacancies API response:', response) // DEBUG
    
    // handleResponse возвращает { data: ..., success: ..., message: ... }
    const data = response.data || response
    vacancies.value = data.results || []
    totalCount.value = data.count || 0
    
    console.log('Loaded vacancies:', vacancies.value.length) // DEBUG
    
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
    'headhunter': 'bg-danger',
    'habr_career': 'bg-info',
    'superjob': 'bg-success'
  }
  return classes[source] || 'bg-secondary'
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

<style scoped>
.vacancy-card {
  transition: all 0.3s ease;
  border-left: 3px solid #dee2e6;
}

.vacancy-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
  border-left-color: #0d6efd;
}

.badge {
  font-size: 0.85rem;
}
</style>
