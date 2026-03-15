<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, MapPin, DollarSign, Calendar, Briefcase, ExternalLink, History, RefreshCw, Building2 } from 'lucide-vue-next'
import { useVacancies } from '../composables/useVacancies'
import { vacanciesApi } from '../js/vacanciesApi'
import { useToast } from 'vue-toastification'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()

const { loadVacancy, loading } = useVacancies()

const vacancy = ref(null)
const versions = ref([])
const showVersions = ref(false)
const showConfirmDialog = ref(false)

const SOURCE_LABELS = {
  headhunter: 'HeadHunter',
  habr_career: 'Habr Career',
  superjob: 'SuperJob'
}

const vacancySource = computed(() => vacancy.value?.source || '')

const sourceLabel = computed(() =>
  SOURCE_LABELS[vacancySource.value] || vacancySource.value
)

const formatSalary = (v) => {
  if (!v) return null
  return v.salary_display || null
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleDateString('ru-RU', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

const loadVacancyData = async () => {
  try {
    vacancy.value = await loadVacancy(route.params.id)
  } catch (err) {
    toast.error('Ошибка при загрузке вакансии')
  }
}

const loadVersions = async () => {
  if (!vacancy.value) return
  try {
    const response = await vacanciesApi.getVersions(vacancySource.value, route.params.id)
    versions.value = response.data
  } catch (err) {
    toast.error('Ошибка при загрузке версий')
  }
}

const handleParse = async () => {
  showConfirmDialog.value = true
}

const confirmParse = async () => {
  showConfirmDialog.value = false
  if (!vacancy.value) return

  const source = vacancySource.value
  try {
    const result = await vacanciesApi.getDetails(source, {
      vacancy_id: vacancy.value.source_id
    })
    toast.success('Обновление вакансии запущено')

    const checkStatus = setInterval(async () => {
      try {
        const status = await vacanciesApi.getTaskStatus(source, result.data.task_id)
        if (status.data.status === 'SUCCESS' || status.data.status === 'FAILURE') {
          clearInterval(checkStatus)
          if (status.data.status === 'SUCCESS') {
            toast.success('Вакансия обновлена')
            loadVacancyData()
          } else {
            toast.error('Ошибка при парсинге')
          }
        }
      } catch (err) {
        clearInterval(checkStatus)
      }
    }, 2000)
  } catch (err) {
    toast.error('Ошибка при запуске парсинга')
  }
}

onMounted(() => {
  loadVacancyData()
})
</script>

<template>
  <div class="vacancy-detail-view">
    <div class="detail-header">
      <button 
        @click="router.go(-1)" 
        class="btn-back"
      >
        <ArrowLeft :size="20" />
      </button>
      <div class="header-actions">
        <button 
          v-if="vacancy"
          @click="handleParse" 
          class="btn-refresh"
          :disabled="loading"
        >
          <RefreshCw :size="18" />
          Обновить
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
    </div>

    <div v-else-if="vacancy" class="detail-content">
      <!-- Основная информация -->
      <div class="detail-main">
        <div class="vacancy-header">
          <div class="vacancy-title-section">
            <h1 class="vacancy-title">
              {{ vacancy.title }}
              <span v-if="vacancy.premium" class="premium-badge">Premium</span>
            </h1>
            <div class="vacancy-company">
              <Building2 :size="18" />
              <span>{{ vacancy.company_name }}</span>
            </div>
          </div>
          <a 
            v-if="vacancy.source_url"
            :href="vacancy.source_url" 
            target="_blank"
            class="btn-external"
          >
            <ExternalLink :size="18" />
            На {{ sourceLabel }}
          </a>
        </div>

        <!-- Мета-информация -->
        <div class="vacancy-meta-grid">
          <div v-if="formatSalary(vacancy)" class="meta-item salary">
            <DollarSign :size="20" />
            <div>
              <div class="meta-label">Зарплата</div>
              <div class="meta-value">{{ formatSalary(vacancy) }}</div>
            </div>
          </div>
          <div v-if="vacancy.area_name" class="meta-item">
            <MapPin :size="20" />
            <div>
              <div class="meta-label">Город</div>
              <div class="meta-value">{{ vacancy.area_name }}</div>
            </div>
          </div>
          <div v-if="vacancy.employment_type && vacancy.employment_type.length" class="meta-item">
            <Briefcase :size="20" />
            <div>
              <div class="meta-label">Тип занятости</div>
              <div class="meta-value">{{ Array.isArray(vacancy.employment_type) ? vacancy.employment_type.join(', ') : vacancy.employment_type }}</div>
            </div>
          </div>
          <div v-if="vacancy.experience" class="meta-item">
            <div>
              <div class="meta-label">Опыт</div>
              <div class="meta-value">{{ vacancy.experience }}</div>
            </div>
          </div>
          <div class="meta-item">
            <Calendar :size="20" />
            <div>
              <div class="meta-label">Опубликовано</div>
              <div class="meta-value">{{ formatDate(vacancy.published_at) }}</div>
            </div>
          </div>
        </div>

        <!-- Описание -->
        <div v-if="vacancy.description" class="content-section">
          <h3 class="section-title">Описание</h3>
          <div class="content-text" v-html="vacancy.description.replace(/\n/g, '<br>')"></div>
        </div>

        <!-- Требования -->
        <div v-if="vacancy.requirements" class="content-section">
          <h3 class="section-title">Требования</h3>
          <div class="content-text" v-html="vacancy.requirements.replace(/\n/g, '<br>')"></div>
        </div>

        <!-- Обязанности -->
        <div v-if="vacancy.responsibilities" class="content-section">
          <h3 class="section-title">Обязанности</h3>
          <div class="content-text" v-html="vacancy.responsibilities.replace(/\n/g, '<br>')"></div>
        </div>

        <!-- Навыки -->
        <div v-if="vacancy.key_skills && vacancy.key_skills.length > 0" class="content-section">
          <h3 class="section-title">Ключевые навыки</h3>
          <div class="skills-list">
            <span 
              v-for="skill in vacancy.key_skills" 
              :key="skill"
              class="skill-badge"
            >
              {{ skill }}
            </span>
          </div>
        </div>
      </div>

      <!-- Боковая панель -->
      <aside class="detail-sidebar">
        <div class="sidebar-card">
          <h4 class="sidebar-title">Информация</h4>
          <div class="sidebar-info">
            <div class="info-item">
              <span class="info-label">Источник</span>
              <span class="info-value">{{ sourceLabel }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">ID на источнике</span>
              <span class="info-value">{{ vacancy.source_id }}</span>
            </div>
            <div v-if="vacancy.current_version" class="info-item">
              <span class="info-label">Версия</span>
              <span class="info-value">{{ vacancy.current_version }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">Статус</span>
              <span :class="`status-badge ${vacancy.is_active ? 'active' : 'inactive'}`">
                {{ vacancy.is_active ? 'Активна' : 'Неактивна' }}
              </span>
            </div>
            <div v-if="vacancy.company_name" class="info-item">
              <span class="info-label">Работодатель</span>
              <span class="info-value">{{ vacancy.company_name }}</span>
            </div>
          </div>
        </div>

        <div class="sidebar-card">
          <div class="sidebar-header">
            <h4 class="sidebar-title">
              <History :size="18" />
              Версии
            </h4>
            <button 
              @click="showVersions = !showVersions; showVersions && loadVersions()"
              class="btn-toggle"
            >
              {{ showVersions ? 'Скрыть' : 'Показать' }}
            </button>
          </div>
          <div v-if="showVersions" class="versions-list">
            <div v-if="versions.length === 0" class="empty-text">
              Нет версий
            </div>
            <div 
              v-for="version in versions" 
              :key="version.id"
              class="version-item"
            >
              <div class="version-header">
                <span class="version-number">Версия {{ version.version_number }}</span>
                <span class="version-date">{{ formatDate(version.created_at) }}</span>
              </div>
              <div v-if="version.change_summary" class="version-summary">
                {{ version.change_summary }}
              </div>
            </div>
          </div>
        </div>
      </aside>
    </div>

    <!-- Диалог подтверждения -->
    <ConfirmDialog
      :show="showConfirmDialog"
      title="Обновить данные вакансии?"
      :message="`Это запустит парсинг вакансии с ${sourceLabel} и обновит данные в базе.`"
      confirm-text="Обновить"
      cancel-text="Отмена"
      @confirm="confirmParse"
      @close="showConfirmDialog = false"
      @cancel="showConfirmDialog = false"
    />
  </div>
</template>

<style lang="scss" scoped>
.vacancy-detail-view {
  .detail-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 2rem;
    
    .btn-back {
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
      color: var(--bs-body-color, #212529);
      
      &:hover {
        border-color: var(--bs-primary, #0d6efd);
        color: var(--bs-primary, #0d6efd);
        background: rgba(13, 110, 253, 0.05);
      }
    }
    
    .btn-refresh {
      display: flex;
      align-items: center;
      gap: 0.5rem;
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
        opacity: 0.6;
        cursor: not-allowed;
      }
    }
  }
  
  .detail-content {
    display: grid;
    grid-template-columns: 1fr 320px;
    gap: 2rem;
  }
  
  .detail-main {
    .vacancy-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 1.5rem;
      margin-bottom: 2rem;
      padding-bottom: 2rem;
      border-bottom: 1px solid var(--bs-border-color, #e9ecef);
      
      .vacancy-title-section {
        flex: 1;
        
        .vacancy-title {
          font-size: 1.75rem;
          font-weight: 600;
          margin: 0 0 1rem 0;
          color: var(--bs-body-color, #212529);
          line-height: 1.3;
          letter-spacing: -0.02em;
          display: flex;
          align-items: center;
          gap: 0.75rem;
          flex-wrap: wrap;
          
          .premium-badge {
            padding: 0.25rem 0.75rem;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 600;
          }
        }
        
        .vacancy-company {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-size: 1rem;
          color: var(--bs-secondary-color, #6c757d);
        }
      }
      
      .btn-external {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.625rem 1.25rem;
        border: 1px solid var(--bs-border-color, #e9ecef);
        border-radius: 8px;
        color: var(--bs-body-color, #212529);
        text-decoration: none;
        font-size: 0.9375rem;
        transition: all 0.2s ease;
        flex-shrink: 0;
        
        &:hover {
          border-color: var(--bs-primary, #0d6efd);
          color: var(--bs-primary, #0d6efd);
          background: rgba(13, 110, 253, 0.05);
        }
      }
    }
    
    .vacancy-meta-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1.5rem;
      margin-bottom: 2.5rem;
      
      .meta-item {
        display: flex;
        align-items: flex-start;
        gap: 0.75rem;
        padding: 1rem;
        background: var(--bs-secondary-bg, #f8f9fa);
        border-radius: 10px;
        
        svg {
          color: var(--bs-secondary-color, #6c757d);
          flex-shrink: 0;
          margin-top: 2px;
        }
        
        .meta-label {
          font-size: 0.8125rem;
          color: var(--bs-secondary-color, #6c757d);
          margin-bottom: 0.25rem;
          font-weight: 500;
        }
        
        .meta-value {
          font-size: 0.9375rem;
          color: var(--bs-body-color, #212529);
          font-weight: 500;
        }
        
        &.salary {
          .meta-value {
            color: var(--bs-success, #198754);
            font-weight: 600;
          }
          
          svg {
            color: var(--bs-success, #198754);
          }
        }
      }
    }
    
    .content-section {
      margin-bottom: 2.5rem;
      
      .section-title {
        font-size: 1.25rem;
        font-weight: 600;
        margin: 0 0 1rem 0;
        color: var(--bs-body-color, #212529);
        letter-spacing: -0.01em;
      }
      
      .content-text {
        font-size: 0.9375rem;
        line-height: 1.7;
        color: var(--bs-body-color, #212529);
        white-space: pre-wrap;
      }
      
      .skills-list {
        display: flex;
        flex-wrap: wrap;
        gap: 0.75rem;
        
        .skill-badge {
          padding: 0.5rem 1rem;
          background: var(--bs-primary-bg-subtle, #cfe2ff);
          border: 1px solid var(--bs-primary-border-subtle, #9ec5fe);
          border-radius: 8px;
          font-size: 0.875rem;
          color: var(--bs-primary, #0d6efd);
          font-weight: 500;
        }
      }
    }
  }
  
  .detail-sidebar {
    .sidebar-card {
      padding: 1.5rem;
      background: var(--bs-body-bg, #fff);
      border: 1px solid var(--bs-border-color, #e9ecef);
      border-radius: 12px;
      margin-bottom: 1.5rem;
      
      .sidebar-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1.25rem;
      }
      
      .sidebar-title {
        font-size: 1rem;
        font-weight: 600;
        margin: 0;
        color: var(--bs-body-color, #212529);
        display: flex;
        align-items: center;
        gap: 0.5rem;
      }
      
      .btn-toggle {
        padding: 0.375rem 0.75rem;
        border: 1px solid var(--bs-border-color, #e9ecef);
        background: var(--bs-body-bg, #fff);
        border-radius: 6px;
        color: var(--bs-body-color, #212529);
        font-size: 0.875rem;
        cursor: pointer;
        transition: all 0.2s ease;
        
        &:hover {
          border-color: var(--bs-primary, #0d6efd);
          color: var(--bs-primary, #0d6efd);
        }
      }
      
      .sidebar-info {
        display: flex;
        flex-direction: column;
        gap: 1rem;
        
        .info-item {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
          
          .info-label {
            font-size: 0.8125rem;
            color: var(--bs-secondary-color, #6c757d);
            font-weight: 500;
          }
          
          .info-value {
            font-size: 0.9375rem;
            color: var(--bs-body-color, #212529);
            font-weight: 500;
          }
          
          .status-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 6px;
            font-size: 0.8125rem;
            font-weight: 600;
            
            &.active {
              background: var(--bs-success-bg-subtle, #d1e7dd);
              color: var(--bs-success, #198754);
            }
            
            &.inactive {
              background: var(--bs-secondary-bg, #f8f9fa);
              color: var(--bs-secondary-color, #6c757d);
            }
          }
        }
      }
      
      .versions-list {
        display: flex;
        flex-direction: column;
        gap: 1rem;
        
        .empty-text {
          font-size: 0.875rem;
          color: var(--bs-secondary-color, #6c757d);
          text-align: center;
          padding: 1rem 0;
        }
        
        .version-item {
          padding: 1rem;
          background: var(--bs-secondary-bg, #f8f9fa);
          border-radius: 8px;
          
          .version-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
            
            .version-number {
              font-size: 0.875rem;
              font-weight: 600;
              color: var(--bs-body-color, #212529);
            }
            
            .version-date {
              font-size: 0.8125rem;
              color: var(--bs-secondary-color, #6c757d);
            }
          }
          
          .version-summary {
            font-size: 0.8125rem;
            color: var(--bs-secondary-color, #6c757d);
          }
        }
      }
    }
  }
  
  .loading-state {
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 4rem 2rem;
    
    .spinner {
      width: 40px;
      height: 40px;
      border: 3px solid var(--bs-border-color, #e9ecef);
      border-top-color: var(--bs-primary, #0d6efd);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
    }
  }
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

@media (max-width: 1024px) {
  .vacancy-detail-view {
    .detail-content {
      grid-template-columns: 1fr;
    }
  }
}

@media (max-width: 768px) {
  .vacancy-detail-view {
    .detail-main {
      .vacancy-header {
        flex-direction: column;
      }
      
      .vacancy-meta-grid {
        grid-template-columns: 1fr;
      }
    }
  }
}
</style>
