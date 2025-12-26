<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Search, X, MapPin, DollarSign, Briefcase, Calendar, ExternalLink, Filter } from 'lucide-vue-next'
import { useVacancies } from '../composables/useVacancies'
import { useToast } from 'vue-toastification'

const route = useRoute()
const router = useRouter()
const toast = useToast()

const { vacancies, loading, pagination, loadVacancies, hasNextPage, hasPreviousPage, totalPages } = useVacancies()

// Фильтры и поиск
const searchQuery = ref(route.query.search || '')
const showFilters = ref(false)
const filters = ref({
  city: route.query.city || '',
  employment_type: route.query.employment_type || '',
  experience_level: route.query.experience_level || '',
  professional_role: route.query.professional_role || '',
  is_active: route.query.is_active || ''
})

const activeFiltersCount = computed(() => {
  return Object.values(filters.value).filter(v => v).length + (searchQuery.value ? 1 : 0)
})

const updateFilters = () => {
  const query = { ...filters.value }
  if (searchQuery.value) query.search = searchQuery.value
  router.push({ query })
  loadVacancies(query)
}

const clearFilters = () => {
  searchQuery.value = ''
  filters.value = {
    city: '',
    employment_type: '',
    experience_level: '',
    professional_role: '',
    is_active: ''
  }
  router.push({ query: {} })
  loadVacancies()
}

const formatSalary = (vacancy) => {
  if (!vacancy.salary_from && !vacancy.salary_to) return null
  if (vacancy.salary_from && vacancy.salary_to) {
    return `${vacancy.salary_from.toLocaleString('ru-RU')} - ${vacancy.salary_to.toLocaleString('ru-RU')} ${vacancy.salary_currency || '₽'}`
  }
  if (vacancy.salary_from) {
    return `от ${vacancy.salary_from.toLocaleString('ru-RU')} ${vacancy.salary_currency || '₽'}`
  }
  return `до ${vacancy.salary_to.toLocaleString('ru-RU')} ${vacancy.salary_currency || '₽'}`
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  const now = new Date()
  const diff = Math.floor((now - date) / (1000 * 60 * 60 * 24))
  
  if (diff === 0) return 'Сегодня'
  if (diff === 1) return 'Вчера'
  if (diff < 7) return `${diff} дн. назад`
  
  return date.toLocaleDateString('ru-RU', {
    day: 'numeric',
    month: 'short'
  })
}

const goToPage = (page) => {
  pagination.value.page = page
  updateFilters()
}

const goToVacancy = (id) => {
  router.push({ name: 'VacancyDetail', params: { id } })
}

onMounted(() => {
  loadVacancies(route.query)
})

watch(() => route.query, (newQuery) => {
  searchQuery.value = newQuery.search || ''
  filters.value = {
    city: newQuery.city || '',
    employment_type: newQuery.employment_type || '',
    experience_level: newQuery.experience_level || '',
    professional_role: newQuery.professional_role || '',
    is_active: newQuery.is_active || ''
  }
  loadVacancies(newQuery)
}, { deep: true })
</script>

<template>
  <div class="vacancies-list-view">
    <div class="list-header">
      <h2 class="list-title">Вакансии</h2>
      <div class="list-actions">
        <button 
          v-if="activeFiltersCount > 0"
          @click="clearFilters" 
          class="btn-clear-filters"
        >
          <X :size="16" />
          Сбросить ({{ activeFiltersCount }})
        </button>
      </div>
    </div>

    <!-- Поиск -->
    <div class="search-bar">
      <div class="search-input-wrapper">
        <Search :size="20" class="search-icon" />
        <input
          v-model="searchQuery"
          @keyup.enter="updateFilters"
          @input="updateFilters"
          type="text"
          class="search-input"
          placeholder="Поиск по названию, компании, описанию..."
        />
        <button 
          v-if="searchQuery"
          @click="searchQuery = ''; updateFilters()"
          class="search-clear"
        >
          <X :size="16" />
        </button>
      </div>
      <button 
        @click="showFilters = !showFilters"
        class="btn-filters"
        :class="{ active: showFilters || activeFiltersCount > 0 }"
      >
        <Filter :size="18" />
        Фильтры
        <span v-if="activeFiltersCount > 0" class="filter-badge">{{ activeFiltersCount }}</span>
      </button>
    </div>

    <!-- Фильтры -->
    <div v-if="showFilters" class="filters-panel">
      <div class="filters-grid">
        <div class="filter-group">
          <label class="filter-label">Город</label>
          <input
            v-model="filters.city"
            @change="updateFilters"
            type="text"
            class="filter-input"
            placeholder="Москва..."
          />
        </div>

        <div class="filter-group">
          <label class="filter-label">Тип занятости</label>
          <select
            v-model="filters.employment_type"
            @change="updateFilters"
            class="filter-select"
          >
            <option value="">Все</option>
            <option value="full">Полная</option>
            <option value="part">Частичная</option>
            <option value="project">Проектная</option>
            <option value="volunteer">Волонтерство</option>
            <option value="probation">Стажировка</option>
          </select>
        </div>

        <div class="filter-group">
          <label class="filter-label">Опыт</label>
          <select
            v-model="filters.experience_level"
            @change="updateFilters"
            class="filter-select"
          >
            <option value="">Все</option>
            <option value="noExperience">Без опыта</option>
            <option value="between1And3">1-3 года</option>
            <option value="between3And6">3-6 лет</option>
            <option value="moreThan6">Более 6 лет</option>
          </select>
        </div>

        <div class="filter-group">
          <label class="filter-label">Статус</label>
          <select
            v-model="filters.is_active"
            @change="updateFilters"
            class="filter-select"
          >
            <option value="">Все</option>
            <option value="true">Активные</option>
            <option value="false">Неактивные</option>
          </select>
        </div>
      </div>
    </div>

    <!-- Список вакансий -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
    </div>

    <div v-else-if="vacancies.length === 0" class="empty-state">
      <Briefcase :size="48" class="empty-icon" />
      <p class="empty-text">Вакансии не найдены</p>
    </div>

    <div v-else class="vacancies-list">
      <div 
        v-for="vacancy in vacancies" 
        :key="vacancy.id"
        class="vacancy-card"
        @click="goToVacancy(vacancy.id)"
      >
        <div class="vacancy-header">
          <div class="vacancy-title-row">
            <h3 class="vacancy-title">{{ vacancy.title }}</h3>
            <span v-if="vacancy.premium" class="premium-badge">Premium</span>
          </div>
          <p class="vacancy-company">{{ vacancy.company_name }}</p>
        </div>

        <div class="vacancy-meta">
          <div v-if="formatSalary(vacancy)" class="vacancy-salary">
            <DollarSign :size="16" />
            <span>{{ formatSalary(vacancy) }}</span>
          </div>
          <div v-if="vacancy.city" class="vacancy-location">
            <MapPin :size="16" />
            <span>{{ vacancy.city }}</span>
          </div>
          <div class="vacancy-date">
            <Calendar :size="16" />
            <span>{{ formatDate(vacancy.published_at) }}</span>
          </div>
        </div>

        <div v-if="vacancy.key_skills && vacancy.key_skills.length > 0" class="vacancy-skills">
          <span 
            v-for="skill in vacancy.key_skills.slice(0, 4)" 
            :key="skill"
            class="skill-tag"
          >
            {{ skill }}
          </span>
          <span v-if="vacancy.key_skills.length > 4" class="skill-tag-more">
            +{{ vacancy.key_skills.length - 4 }}
          </span>
        </div>

        <a 
          v-if="vacancy.url"
          :href="vacancy.url" 
          target="_blank"
          @click.stop
          class="vacancy-link"
        >
          <ExternalLink :size="16" />
          Открыть на HH
        </a>
      </div>
    </div>

    <!-- Пагинация -->
    <nav v-if="totalPages > 1" class="pagination-nav">
      <button 
        class="pagination-btn"
        :disabled="!hasPreviousPage"
        @click="goToPage(pagination.page - 1)"
      >
        Назад
      </button>
      <div class="pagination-info">
        Страница {{ pagination.page }} из {{ totalPages }}
      </div>
      <button 
        class="pagination-btn"
        :disabled="!hasNextPage"
        @click="goToPage(pagination.page + 1)"
      >
        Вперед
      </button>
    </nav>
  </div>
</template>

<style lang="scss" scoped>
.vacancies-list-view {
  .list-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1.5rem;
    
    .list-title {
      font-size: 1.5rem;
      font-weight: 600;
      margin: 0;
      color: var(--bs-body-color, #212529);
      letter-spacing: -0.02em;
    }
    
    .btn-clear-filters {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem 1rem;
      border: 1px solid var(--bs-border-color, #e9ecef);
      background: var(--bs-body-bg, #fff);
      border-radius: 8px;
      color: var(--bs-body-color, #6c757d);
      font-size: 0.875rem;
      cursor: pointer;
      transition: all 0.2s ease;
      
      &:hover {
        border-color: var(--bs-danger, #dc3545);
        color: var(--bs-danger, #dc3545);
      }
    }
  }
  
  .search-bar {
    display: flex;
    gap: 1rem;
    margin-bottom: 1.5rem;
    
    .search-input-wrapper {
      flex: 1;
      position: relative;
      display: flex;
      align-items: center;
      
      .search-icon {
        position: absolute;
        left: 1rem;
        color: var(--bs-secondary-color, #6c757d);
        pointer-events: none;
      }
      
      .search-input {
        width: 100%;
        padding: 0.875rem 1rem 0.875rem 3rem;
        border: 1px solid var(--bs-border-color, #e9ecef);
        border-radius: 10px;
        font-size: 0.9375rem;
        transition: all 0.2s ease;
        background: var(--bs-body-bg, #fff);
        
        &:focus {
          outline: none;
          border-color: var(--bs-primary, #0d6efd);
          box-shadow: 0 0 0 3px rgba(13, 110, 253, 0.1);
        }
      }
      
      .search-clear {
        position: absolute;
        right: 0.75rem;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 24px;
        height: 24px;
        border: none;
        background: transparent;
        color: var(--bs-secondary-color, #6c757d);
        cursor: pointer;
        border-radius: 4px;
        transition: all 0.2s ease;
        
        &:hover {
          background: var(--bs-secondary-bg, #f8f9fa);
          color: var(--bs-body-color, #212529);
        }
      }
    }
    
    .btn-filters {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.875rem 1.25rem;
      border: 1px solid var(--bs-border-color, #e9ecef);
      background: var(--bs-body-bg, #fff);
      border-radius: 10px;
      color: var(--bs-body-color, #212529);
      font-size: 0.9375rem;
      cursor: pointer;
      transition: all 0.2s ease;
      position: relative;
      
      &:hover,
      &.active {
        border-color: var(--bs-primary, #0d6efd);
        color: var(--bs-primary, #0d6efd);
        background: rgba(13, 110, 253, 0.05);
      }
      
      .filter-badge {
        display: flex;
        align-items: center;
        justify-content: center;
        min-width: 20px;
        height: 20px;
        padding: 0 6px;
        background: var(--bs-primary, #0d6efd);
        color: white;
        border-radius: 10px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-left: 0.25rem;
      }
    }
  }
  
  .filters-panel {
    padding: 1.5rem;
    background: var(--bs-body-bg, #fff);
    border: 1px solid var(--bs-border-color, #e9ecef);
    border-radius: 12px;
    margin-bottom: 1.5rem;
    
    .filters-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1.25rem;
    }
    
    .filter-group {
      .filter-label {
        display: block;
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--bs-body-color, #212529);
        margin-bottom: 0.5rem;
      }
      
      .filter-input,
      .filter-select {
        width: 100%;
        padding: 0.625rem 0.875rem;
        border: 1px solid var(--bs-border-color, #e9ecef);
        border-radius: 8px;
        font-size: 0.9375rem;
        background: var(--bs-body-bg, #fff);
        transition: all 0.2s ease;
        
        &:focus {
          outline: none;
          border-color: var(--bs-primary, #0d6efd);
          box-shadow: 0 0 0 3px rgba(13, 110, 253, 0.1);
        }
      }
    }
  }
  
  .vacancies-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }
  
  .vacancy-card {
    padding: 1.5rem;
    background: var(--bs-body-bg, #fff);
    border: 1px solid var(--bs-border-color, #e9ecef);
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.2s ease;
    position: relative;
    
    &:hover {
      border-color: var(--bs-primary, #0d6efd);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
      transform: translateY(-2px);
    }
    
    .vacancy-header {
      margin-bottom: 1rem;
      
      .vacancy-title-row {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 0.5rem;
        
        .vacancy-title {
          font-size: 1.125rem;
          font-weight: 600;
          margin: 0;
          color: var(--bs-body-color, #212529);
          line-height: 1.4;
          flex: 1;
        }
        
        .premium-badge {
          padding: 0.25rem 0.75rem;
          background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
          color: white;
          border-radius: 6px;
          font-size: 0.75rem;
          font-weight: 600;
          flex-shrink: 0;
        }
      }
      
      .vacancy-company {
        font-size: 0.9375rem;
        color: var(--bs-secondary-color, #6c757d);
        margin: 0;
      }
    }
    
    .vacancy-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 1.25rem;
      margin-bottom: 1rem;
      font-size: 0.875rem;
      
      > div {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        color: var(--bs-body-color, #212529);
        
        svg {
          color: var(--bs-secondary-color, #6c757d);
        }
      }
      
      .vacancy-salary {
        font-weight: 600;
        color: var(--bs-success, #198754);
        
        svg {
          color: var(--bs-success, #198754);
        }
      }
    }
    
    .vacancy-skills {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin-bottom: 1rem;
      
      .skill-tag {
        padding: 0.375rem 0.75rem;
        background: var(--bs-secondary-bg, #f8f9fa);
        border: 1px solid var(--bs-border-color, #e9ecef);
        border-radius: 6px;
        font-size: 0.8125rem;
        color: var(--bs-body-color, #212529);
      }
      
      .skill-tag-more {
        padding: 0.375rem 0.75rem;
        background: var(--bs-primary-bg-subtle, #cfe2ff);
        border: 1px solid var(--bs-primary-border-subtle, #9ec5fe);
        border-radius: 6px;
        font-size: 0.8125rem;
        color: var(--bs-primary, #0d6efd);
        font-weight: 500;
      }
    }
    
    .vacancy-link {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem 1rem;
      border: 1px solid var(--bs-border-color, #e9ecef);
      border-radius: 8px;
      color: var(--bs-body-color, #212529);
      text-decoration: none;
      font-size: 0.875rem;
      transition: all 0.2s ease;
      
      &:hover {
        border-color: var(--bs-primary, #0d6efd);
        color: var(--bs-primary, #0d6efd);
        background: rgba(13, 110, 253, 0.05);
      }
    }
  }
  
  .pagination-nav {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 1.5rem;
    margin-top: 2rem;
    padding-top: 2rem;
    border-top: 1px solid var(--bs-border-color, #e9ecef);
    
    .pagination-btn {
      padding: 0.625rem 1.25rem;
      border: 1px solid var(--bs-border-color, #e9ecef);
      background: var(--bs-body-bg, #fff);
      border-radius: 8px;
      color: var(--bs-body-color, #212529);
      font-size: 0.9375rem;
      cursor: pointer;
      transition: all 0.2s ease;
      
      &:hover:not(:disabled) {
        border-color: var(--bs-primary, #0d6efd);
        color: var(--bs-primary, #0d6efd);
        background: rgba(13, 110, 253, 0.05);
      }
      
      &:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }
    }
    
    .pagination-info {
      font-size: 0.9375rem;
      color: var(--bs-secondary-color, #6c757d);
    }
  }
  
  .loading-state,
  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 4rem 2rem;
    text-align: center;
    
    .spinner {
      width: 40px;
      height: 40px;
      border: 3px solid var(--bs-border-color, #e9ecef);
      border-top-color: var(--bs-primary, #0d6efd);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
    
    .empty-icon {
      color: var(--bs-secondary-color, #6c757d);
      margin-bottom: 1rem;
      opacity: 0.5;
    }
    
    .empty-text {
      color: var(--bs-secondary-color, #6c757d);
      margin: 0;
    }
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .vacancies-list-view {
    .search-bar {
      flex-direction: column;
    }
    
    .filters-panel .filters-grid {
      grid-template-columns: 1fr;
    }
    
    .vacancy-card {
      padding: 1.25rem;
    }
    
    .vacancy-meta {
      flex-direction: column;
      gap: 0.75rem;
    }
  }
}
</style>
