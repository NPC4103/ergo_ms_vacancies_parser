<script setup>
import { ref, onMounted, computed } from 'vue'
import { BarChart3, TrendingUp, MapPin, DollarSign, Briefcase, RefreshCw, Activity } from 'lucide-vue-next'
import { useVacancies } from '../composables/useVacancies'

const { loadStats, loading } = useVacancies()

const stats = ref(null)

const loadStatsData = async () => {
  try {
    stats.value = await loadStats()
  } catch (error) {
    console.error('Ошибка загрузки статистики:', error)
  }
}

const topCities = computed(() => {
  if (!stats.value?.vacancies_by_city) return []
  return Object.entries(stats.value.vacancies_by_city)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([city, count]) => ({ city: city || 'Не указан', count }))
})

const topRoles = computed(() => {
  if (!stats.value?.vacancies_by_role) return []
  return Object.entries(stats.value.vacancies_by_role)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([role, count]) => ({ role, count }))
})

const topExperience = computed(() => {
  if (!stats.value?.vacancies_by_experience) return []
  return Object.entries(stats.value.vacancies_by_experience)
    .sort((a, b) => b[1] - a[1])
    .map(([exp, count]) => ({ experience: exp, count }))
})

const salaryStats = computed(() => {
  if (!stats.value) return null
  return {
    min: stats.value.min_salary_from,
    avgFrom: stats.value.avg_salary_from,
    avgTo: stats.value.avg_salary_to,
    max: stats.value.max_salary_to
  }
})

onMounted(() => {
  loadStatsData()
})
</script>

<template>
  <div class="stats-view">
    <div class="stats-header">
      <h2 class="stats-title">Статистика</h2>
      <button 
        @click="loadStatsData" 
        class="btn-refresh"
        :disabled="loading"
        :class="{ loading: loading }"
      >
        <RefreshCw :size="18" />
      </button>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
    </div>

    <div v-else-if="stats" class="stats-content">
      <!-- Основные метрики -->
      <div class="metrics-grid">
        <div class="metric-card">
          <div class="metric-icon primary">
            <Briefcase :size="24" />
          </div>
          <div class="metric-content">
            <div class="metric-value">{{ stats.total_vacancies || 0 }}</div>
            <div class="metric-label">Всего вакансий</div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon success">
            <Activity :size="24" />
          </div>
          <div class="metric-content">
            <div class="metric-value">{{ stats.active_vacancies || 0 }}</div>
            <div class="metric-label">Активных</div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon warning">
            <DollarSign :size="24" />
          </div>
          <div class="metric-content">
            <div class="metric-value">
              {{ stats.avg_salary_from ? Math.round(stats.avg_salary_from).toLocaleString('ru-RU') : '—' }}
            </div>
            <div class="metric-label">Средняя зарплата от (₽)</div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon info">
            <TrendingUp :size="24" />
          </div>
          <div class="metric-content">
            <div class="metric-value">{{ stats.recent_vacancies_count || 0 }}</div>
            <div class="metric-label">За последнюю неделю</div>
          </div>
        </div>
      </div>

      <!-- Диапазон зарплат -->
      <div v-if="salaryStats" class="salary-range-card">
        <h3 class="section-title">
          <DollarSign :size="20" />
          Диапазон зарплат
        </h3>
        <div class="salary-range">
          <div class="salary-item">
            <div class="salary-label">Минимум</div>
            <div class="salary-value">
              {{ salaryStats.min ? salaryStats.min.toLocaleString('ru-RU') : '—' }} ₽
            </div>
          </div>
          <div class="salary-item">
            <div class="salary-label">Средняя от</div>
            <div class="salary-value">
              {{ salaryStats.avgFrom ? Math.round(salaryStats.avgFrom).toLocaleString('ru-RU') : '—' }} ₽
            </div>
          </div>
          <div class="salary-item">
            <div class="salary-label">Средняя до</div>
            <div class="salary-value">
              {{ salaryStats.avgTo ? Math.round(salaryStats.avgTo).toLocaleString('ru-RU') : '—' }} ₽
            </div>
          </div>
          <div class="salary-item">
            <div class="salary-label">Максимум</div>
            <div class="salary-value">
              {{ salaryStats.max ? salaryStats.max.toLocaleString('ru-RU') : '—' }} ₽
            </div>
          </div>
        </div>
      </div>

      <!-- Топ списки -->
      <div class="top-lists">
        <div v-if="topCities.length > 0" class="top-list-card">
          <div class="list-header">
            <MapPin :size="20" />
            <h3>Топ городов</h3>
          </div>
          <div class="list-items">
            <div 
              v-for="(item, index) in topCities" 
              :key="item.city"
              class="list-item"
            >
              <div class="item-rank">{{ index + 1 }}</div>
              <div class="item-label">{{ item.city }}</div>
              <div class="item-value">{{ item.count }}</div>
              <div class="item-bar">
                <div 
                  class="item-bar-fill"
                  :style="{ width: `${(item.count / topCities[0].count) * 100}%` }"
                ></div>
              </div>
            </div>
          </div>
        </div>

        <div v-if="topRoles.length > 0" class="top-list-card">
          <div class="list-header">
            <TrendingUp :size="20" />
            <h3>Топ ролей</h3>
          </div>
          <div class="list-items">
            <div 
              v-for="(item, index) in topRoles" 
              :key="item.role"
              class="list-item"
            >
              <div class="item-rank">{{ index + 1 }}</div>
              <div class="item-label">{{ item.role }}</div>
              <div class="item-value">{{ item.count }}</div>
              <div class="item-bar">
                <div 
                  class="item-bar-fill"
                  :style="{ width: `${(item.count / topRoles[0].count) * 100}%` }"
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Распределение по опыту -->
      <div v-if="topExperience.length > 0" class="experience-card">
        <h3 class="section-title">Распределение по опыту</h3>
        <div class="experience-grid">
          <div 
            v-for="item in topExperience" 
            :key="item.experience"
            class="experience-item"
          >
            <div class="experience-value">{{ item.count }}</div>
            <div class="experience-label">{{ item.experience }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Пустое состояние -->
    <div v-else class="empty-state">
      <BarChart3 :size="48" class="empty-icon" />
      <p class="empty-text">Нет данных для отображения</p>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.stats-view {
  .stats-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
    
    .stats-title {
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
      border: 1px solid var(--bs-border-color, #e9ecef);
      background: var(--bs-body-bg, #fff);
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
  
  .metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 1.5rem;
    margin-bottom: 2rem;
  }
  
  .metric-card {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 1.5rem;
    background: var(--bs-body-bg, #fff);
    border: 1px solid var(--bs-border-color, #e9ecef);
    border-radius: 12px;
    transition: all 0.2s ease;
    
    &:hover {
      border-color: var(--bs-primary, #0d6efd);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }
    
    .metric-icon {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 48px;
      height: 48px;
      border-radius: 10px;
      flex-shrink: 0;
      
      &.primary {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
      }
      
      &.success {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        color: white;
      }
      
      &.warning {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        color: white;
      }
      
      &.info {
        background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
        color: white;
      }
    }
    
    .metric-content {
      flex: 1;
      min-width: 0;
    }
    
    .metric-value {
      font-size: 1.75rem;
      font-weight: 600;
      color: var(--bs-body-color, #212529);
      line-height: 1.2;
      margin-bottom: 0.25rem;
    }
    
    .metric-label {
      font-size: 0.875rem;
      color: var(--bs-secondary-color, #6c757d);
      font-weight: 500;
    }
  }
  
  .salary-range-card {
    padding: 1.5rem;
    background: var(--bs-body-bg, #fff);
    border: 1px solid var(--bs-border-color, #e9ecef);
    border-radius: 12px;
    margin-bottom: 2rem;
    
    .section-title {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      font-size: 1.125rem;
      font-weight: 600;
      margin: 0 0 1.5rem 0;
      color: var(--bs-body-color, #212529);
    }
    
    .salary-range {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1.5rem;
    }
    
    .salary-item {
      text-align: center;
      
      .salary-label {
        font-size: 0.875rem;
        color: var(--bs-secondary-color, #6c757d);
        margin-bottom: 0.5rem;
        font-weight: 500;
      }
      
      .salary-value {
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--bs-body-color, #212529);
      }
    }
  }
  
  .top-lists {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
    gap: 2rem;
    margin-bottom: 2rem;
  }
  
  .top-list-card {
    padding: 1.5rem;
    background: var(--bs-body-bg, #fff);
    border: 1px solid var(--bs-border-color, #e9ecef);
    border-radius: 12px;
    
    .list-header {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin-bottom: 1.5rem;
      
      h3 {
        font-size: 1.125rem;
        font-weight: 600;
        margin: 0;
        color: var(--bs-body-color, #212529);
      }
    }
    
    .list-items {
      display: flex;
      flex-direction: column;
      gap: 1rem;
    }
    
    .list-item {
      display: grid;
      grid-template-columns: 32px 1fr auto;
      gap: 1rem;
      align-items: center;
      padding: 0.875rem;
      background: var(--bs-secondary-bg, #f8f9fa);
      border-radius: 8px;
      position: relative;
      
      .item-rank {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        border-radius: 6px;
        background: var(--bs-body-bg, #fff);
        color: var(--bs-secondary-color, #6c757d);
        font-weight: 600;
        font-size: 0.875rem;
        flex-shrink: 0;
      }
      
      .item-label {
        font-size: 0.9375rem;
        color: var(--bs-body-color, #212529);
        font-weight: 500;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      
      .item-value {
        font-size: 0.9375rem;
        font-weight: 600;
        color: var(--bs-primary, #0d6efd);
        flex-shrink: 0;
      }
      
      .item-bar {
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        height: 3px;
        background: transparent;
        border-radius: 0 0 8px 8px;
        overflow: hidden;
        
        .item-bar-fill {
          height: 100%;
          background: var(--bs-primary, #0d6efd);
          opacity: 0.2;
          transition: width 0.3s ease;
        }
      }
    }
  }
  
  .experience-card {
    padding: 1.5rem;
    background: var(--bs-body-bg, #fff);
    border: 1px solid var(--bs-border-color, #e9ecef);
    border-radius: 12px;
    
    .section-title {
      font-size: 1.125rem;
      font-weight: 600;
      margin: 0 0 1.5rem 0;
      color: var(--bs-body-color, #212529);
    }
    
    .experience-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 1rem;
    }
    
    .experience-item {
      padding: 1.25rem;
      background: var(--bs-secondary-bg, #f8f9fa);
      border-radius: 10px;
      text-align: center;
      transition: all 0.2s ease;
      
      &:hover {
        background: var(--bs-primary-bg-subtle, #cfe2ff);
        transform: translateY(-2px);
      }
      
      .experience-value {
        font-size: 1.5rem;
        font-weight: 600;
        color: var(--bs-primary, #0d6efd);
        margin-bottom: 0.5rem;
      }
      
      .experience-label {
        font-size: 0.875rem;
        color: var(--bs-body-color, #212529);
        font-weight: 500;
      }
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
  .stats-view {
    .metrics-grid {
      grid-template-columns: 1fr;
    }
    
    .top-lists {
      grid-template-columns: 1fr;
    }
    
    .salary-range {
      grid-template-columns: repeat(2, 1fr);
    }
  }
}
</style>
