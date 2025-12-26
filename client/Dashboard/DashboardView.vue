<script setup>
import { ref, onMounted, computed } from 'vue'
import { Briefcase, TrendingUp, MapPin, DollarSign, Clock, RefreshCw, Activity } from 'lucide-vue-next'
import { useVacancies } from '../composables/useVacancies'
import { useRouter } from 'vue-router'

const router = useRouter()
const { loadStats, loading } = useVacancies()

const stats = ref(null)

const loadDashboardData = async () => {
  try {
    stats.value = await loadStats()
  } catch (error) {
    console.error('Ошибка загрузки данных дашборда:', error)
  }
}

const statCards = computed(() => {
  if (!stats.value) return []
  
  return [
    {
      title: 'Всего вакансий',
      value: stats.value.total_vacancies || 0,
      icon: Briefcase,
      gradient: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      link: { name: 'VacanciesList' }
    },
    {
      title: 'Активных',
      value: stats.value.active_vacancies || 0,
      icon: Activity,
      gradient: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
      link: { name: 'VacanciesList', query: { is_active: 'true' } }
    },
    {
      title: 'Средняя зарплата',
      value: stats.value.avg_salary_from 
        ? `${Math.round(stats.value.avg_salary_from).toLocaleString('ru-RU')} ₽`
        : '—',
      icon: DollarSign,
      gradient: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
      link: { name: 'VacancyStats' }
    },
    {
      title: 'За неделю',
      value: stats.value.recent_vacancies_count || 0,
      icon: Clock,
      gradient: 'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
      link: { name: 'VacanciesList' }
    }
  ]
})

const topCities = computed(() => {
  if (!stats.value?.vacancies_by_city) return []
  return Object.entries(stats.value.vacancies_by_city)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([city, count]) => ({ city: city || 'Не указан', count }))
})

const topRoles = computed(() => {
  if (!stats.value?.vacancies_by_role) return []
  return Object.entries(stats.value.vacancies_by_role)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([role, count]) => ({ role, count }))
})

onMounted(() => {
  loadDashboardData()
})
</script>

<template>
  <div class="dashboard-view">
    <div class="dashboard-header">
      <h2 class="dashboard-title">Обзор</h2>
      <button 
        @click="loadDashboardData" 
        class="btn-refresh"
        :disabled="loading"
        :class="{ loading: loading }"
      >
        <RefreshCw :size="18" />
      </button>
    </div>

    <!-- Статистические карточки -->
    <div class="stats-grid">
      <div 
        v-for="card in statCards" 
        :key="card.title"
        class="stat-card"
        @click="card.link && router.push(card.link)"
      >
        <div class="stat-card-icon" :style="{ background: card.gradient }">
          <component :is="card.icon" :size="24" />
        </div>
        <div class="stat-card-content">
          <div class="stat-card-label">{{ card.title }}</div>
          <div class="stat-card-value">{{ card.value }}</div>
        </div>
      </div>
    </div>

    <!-- Дополнительная статистика -->
    <div v-if="stats && (topCities.length > 0 || topRoles.length > 0)" class="stats-sections">
      <div v-if="topCities.length > 0" class="stats-section">
        <div class="stats-section-header">
          <MapPin :size="20" />
          <h3>Топ городов</h3>
        </div>
        <div class="stats-list">
          <div 
            v-for="(item, index) in topCities" 
            :key="item.city"
            class="stats-item"
          >
            <div class="stats-item-rank">{{ index + 1 }}</div>
            <div class="stats-item-label">{{ item.city }}</div>
            <div class="stats-item-value">{{ item.count }}</div>
          </div>
        </div>
      </div>

      <div v-if="topRoles.length > 0" class="stats-section">
        <div class="stats-section-header">
          <TrendingUp :size="20" />
          <h3>Топ ролей</h3>
        </div>
        <div class="stats-list">
          <div 
            v-for="(item, index) in topRoles" 
            :key="item.role"
            class="stats-item"
          >
            <div class="stats-item-rank">{{ index + 1 }}</div>
            <div class="stats-item-label">{{ item.role }}</div>
            <div class="stats-item-value">{{ item.count }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Пустое состояние -->
    <div v-if="!loading && !stats" class="empty-state">
      <Briefcase :size="48" class="empty-icon" />
      <p class="empty-text">Нет данных для отображения</p>
    </div>

    <!-- Загрузка -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.dashboard-view {
  .dashboard-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
    
    .dashboard-title {
      font-size: 1.5rem;
      font-weight: 600;
      margin: 0;
      color: var(--bs-body-color, #212529);
      letter-spacing: -0.02em;
    }
    
    .btn-refresh {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 40px;
      height: 40px;
      border: none;
      background: var(--bs-body-bg, #fff);
      border: 1px solid var(--bs-border-color, #e9ecef);
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.2s ease;
      color: var(--bs-body-color, #6c757d);
      
      &:hover:not(:disabled) {
        background: var(--bs-primary, #0d6efd);
        color: white;
        border-color: var(--bs-primary, #0d6efd);
        transform: rotate(90deg);
      }
      
      &:disabled {
        opacity: 0.6;
        cursor: not-allowed;
      }
      
      &.loading {
        animation: spin 1s linear infinite;
      }
    }
  }
  
  .stats-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 1.5rem;
    margin-bottom: 3rem;
  }
  
  .stat-card {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1.5rem;
    background: var(--bs-body-bg, #fff);
    border: 1px solid var(--bs-border-color, #e9ecef);
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.2s ease;
    
    &:hover {
      border-color: var(--bs-primary, #0d6efd);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
      transform: translateY(-2px);
    }
    
    .stat-card-icon {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 48px;
      height: 48px;
      border-radius: 10px;
      color: white;
      flex-shrink: 0;
    }
    
    .stat-card-content {
      flex: 1;
      min-width: 0;
    }
    
    .stat-card-label {
      font-size: 0.875rem;
      color: var(--bs-secondary-color, #6c757d);
      margin-bottom: 0.25rem;
      font-weight: 500;
    }
    
    .stat-card-value {
      font-size: 1.5rem;
      font-weight: 600;
      color: var(--bs-body-color, #212529);
      line-height: 1.2;
    }
  }
  
  .stats-sections {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 2rem;
  }
  
  .stats-section {
    .stats-section-header {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin-bottom: 1.5rem;
      color: var(--bs-body-color, #212529);
      
      h3 {
        font-size: 1.125rem;
        font-weight: 600;
        margin: 0;
      }
    }
    
    .stats-list {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
    }
    
    .stats-item {
      display: flex;
      align-items: center;
      gap: 1rem;
      padding: 0.875rem;
      background: var(--bs-body-bg, #fff);
      border: 1px solid var(--bs-border-color, #e9ecef);
      border-radius: 8px;
      transition: all 0.2s ease;
      
      &:hover {
        border-color: var(--bs-primary, #0d6efd);
        background: rgba(13, 110, 253, 0.02);
      }
      
      .stats-item-rank {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        border-radius: 6px;
        background: var(--bs-secondary-bg, #f8f9fa);
        color: var(--bs-secondary-color, #6c757d);
        font-weight: 600;
        font-size: 0.875rem;
        flex-shrink: 0;
      }
      
      .stats-item-label {
        flex: 1;
        font-size: 0.9375rem;
        color: var(--bs-body-color, #212529);
        font-weight: 500;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      
      .stats-item-value {
        font-size: 0.9375rem;
        font-weight: 600;
        color: var(--bs-primary, #0d6efd);
        flex-shrink: 0;
      }
    }
  }
  
  .empty-state,
  .loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 4rem 2rem;
    text-align: center;
    
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
  
  .spinner {
    width: 40px;
    height: 40px;
    border: 3px solid var(--bs-border-color, #e9ecef);
    border-top-color: var(--bs-primary, #0d6efd);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .dashboard-view {
    .stats-grid {
      grid-template-columns: 1fr;
      gap: 1rem;
    }
    
    .stats-sections {
      grid-template-columns: 1fr;
      gap: 1.5rem;
    }
    
    .stat-card {
      padding: 1.25rem;
    }
  }
}
</style>
