<script setup>
import { ref, computed } from 'vue'
import { Play, Settings, CheckCircle, XCircle, Clock, Code, Users } from 'lucide-vue-next'
import { useParsing } from '../composables/useParsing'
import { useToast } from 'vue-toastification'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const toast = useToast()
const { parsing, taskId, taskStatus, parseByRoles, parseByTechnologies, checkTaskStatus } = useParsing()

// Форма для парсинга по ролям
const rolesForm = ref({
  area: 113,
  pages: 20,
  delay: 1.5,
  get_details: true,
  max_concurrent_roles: 5,
  batch_size: 25,
  force_refresh_roles: false,
  incremental: false
})

// Форма для парсинга по технологиям
const techForm = ref({
  technologies: '',
  area: 113,
  pages: 10,
  delay: 1.5,
  get_details: true
})

const activeTab = ref('roles')
const showConfirmDialog = ref(false)
const confirmAction = ref(null)

const handleParseByRoles = () => {
  confirmAction.value = () => {
    parseByRoles(rolesForm.value)
    if (taskId.value) {
      startStatusCheck()
    }
  }
  showConfirmDialog.value = true
}

const handleParseByTechnologies = () => {
  const technologies = techForm.value.technologies
    .split(',')
    .map(t => t.trim())
    .filter(t => t)
  
  if (technologies.length === 0) {
    toast.error('Укажите хотя бы одну технологию')
    return
  }

  confirmAction.value = () => {
    parseByTechnologies({
      ...techForm.value,
      technologies
    })
    if (taskId.value) {
      startStatusCheck()
    }
  }
  showConfirmDialog.value = true
}

const confirmParse = () => {
  showConfirmDialog.value = false
  if (confirmAction.value) {
    confirmAction.value()
  }
}

const startStatusCheck = () => {
  const interval = setInterval(async () => {
    if (!taskId.value) {
      clearInterval(interval)
      return
    }
    
    try {
      await checkTaskStatus()
      if (taskStatus.value && (taskStatus.value.status === 'SUCCESS' || taskStatus.value.status === 'FAILURE')) {
        clearInterval(interval)
        if (taskStatus.value.status === 'SUCCESS') {
          toast.success('Парсинг завершен успешно')
        } else {
          toast.error('Ошибка при парсинге')
        }
      }
    } catch (error) {
      clearInterval(interval)
    }
  }, 3000)
}

const taskStatusText = computed(() => {
  if (!taskStatus.value) return 'Ожидание...'
  const status = taskStatus.value.status
  if (status === 'SUCCESS') return 'Завершено успешно'
  if (status === 'FAILURE') return 'Ошибка'
  if (status === 'PENDING') return 'В очереди'
  if (status === 'STARTED') return 'Выполняется'
  return status
})

const taskStatusIcon = computed(() => {
  if (!taskStatus.value) return Clock
  const status = taskStatus.value.status
  if (status === 'SUCCESS') return CheckCircle
  if (status === 'FAILURE') return XCircle
  return Clock
})

const taskStatusColor = computed(() => {
  if (!taskStatus.value) return 'secondary'
  const status = taskStatus.value.status
  if (status === 'SUCCESS') return 'success'
  if (status === 'FAILURE') return 'danger'
  return 'warning'
})
</script>

<template>
  <div class="parsing-control-view">
    <div class="control-header">
      <h2 class="control-title">Управление парсингом</h2>
    </div>

    <!-- Статус задачи -->
    <div v-if="taskId" class="task-status-card">
      <div class="task-status-header">
        <component :is="taskStatusIcon" :size="24" :class="`status-icon-${taskStatusColor}`" />
        <div class="task-status-info">
          <div class="task-status-id">Task ID: {{ taskId }}</div>
          <div class="task-status-text">{{ taskStatusText }}</div>
        </div>
        <button 
          @click="checkTaskStatus()" 
          class="btn-refresh-status"
        >
          Обновить
        </button>
      </div>
      <div v-if="taskStatus && taskStatus.result" class="task-result">
        <pre>{{ JSON.stringify(taskStatus.result, null, 2) }}</pre>
      </div>
      <div v-if="taskStatus && taskStatus.error" class="task-error">
        {{ taskStatus.error }}
      </div>
    </div>

    <!-- Вкладки -->
    <div class="tabs">
      <button 
        class="tab-btn"
        :class="{ active: activeTab === 'roles' }"
        @click="activeTab = 'roles'"
      >
        <Users :size="18" />
        По ролям
      </button>
      <button 
        class="tab-btn"
        :class="{ active: activeTab === 'technologies' }"
        @click="activeTab = 'technologies'"
      >
        <Code :size="18" />
        По технологиям
      </button>
    </div>

    <!-- Парсинг по ролям -->
    <div v-if="activeTab === 'roles'" class="form-card">
      <div class="form-header">
        <Settings :size="20" />
        <h3>Парсинг по профессиональным ролям</h3>
      </div>
      <div class="form-grid">
        <div class="form-group">
          <label class="form-label">Регион (area)</label>
          <input
            v-model.number="rolesForm.area"
            type="number"
            class="form-input"
            placeholder="113 (Москва)"
          />
          <small class="form-hint">113 - Москва, 2 - СПб, и т.д.</small>
        </div>

        <div class="form-group">
          <label class="form-label">Количество страниц</label>
          <input
            v-model.number="rolesForm.pages"
            type="number"
            class="form-input"
            min="1"
            max="200"
          />
        </div>

        <div class="form-group">
          <label class="form-label">Задержка (сек)</label>
          <input
            v-model.number="rolesForm.delay"
            type="number"
            step="0.1"
            class="form-input"
            min="0.1"
          />
        </div>

        <div class="form-group">
          <label class="form-label">Параллельных ролей</label>
          <input
            v-model.number="rolesForm.max_concurrent_roles"
            type="number"
            class="form-input"
            min="1"
            max="10"
          />
        </div>

        <div class="form-group">
          <label class="form-label">Размер батча</label>
          <input
            v-model.number="rolesForm.batch_size"
            type="number"
            class="form-input"
            min="1"
            max="50"
          />
        </div>

        <div class="form-group checkbox-group">
          <label class="checkbox-label">
            <input
              v-model="rolesForm.get_details"
              type="checkbox"
              class="checkbox-input"
            />
            <span>Получать детальную информацию</span>
          </label>
        </div>

        <div class="form-group checkbox-group">
          <label class="checkbox-label">
            <input
              v-model="rolesForm.force_refresh_roles"
              type="checkbox"
              class="checkbox-input"
            />
            <span>Принудительно обновить список ролей</span>
          </label>
        </div>

        <div class="form-group checkbox-group">
          <label class="checkbox-label">
            <input
              v-model="rolesForm.incremental"
              type="checkbox"
              class="checkbox-input"
            />
            <span>Инкрементальный режим</span>
          </label>
        </div>
      </div>

      <div class="form-actions">
        <button 
          @click="handleParseByRoles" 
          class="btn-submit"
          :disabled="parsing"
        >
          <Play :size="18" />
          {{ parsing ? 'Запуск...' : 'Запустить парсинг' }}
        </button>
      </div>
    </div>

    <!-- Парсинг по технологиям -->
    <div v-if="activeTab === 'technologies'" class="form-card">
      <div class="form-header">
        <Settings :size="20" />
        <h3>Парсинг по технологиям</h3>
      </div>
      <div class="form-grid">
        <div class="form-group full-width">
          <label class="form-label">Технологии (через запятую)</label>
          <textarea
            v-model="techForm.technologies"
            class="form-textarea"
            rows="3"
            placeholder="Python, Django, Vue.js, React..."
          ></textarea>
          <small class="form-hint">Укажите технологии через запятую</small>
        </div>

        <div class="form-group">
          <label class="form-label">Регион (area)</label>
          <input
            v-model.number="techForm.area"
            type="number"
            class="form-input"
            placeholder="113 (Москва)"
          />
        </div>

        <div class="form-group">
          <label class="form-label">Количество страниц</label>
          <input
            v-model.number="techForm.pages"
            type="number"
            class="form-input"
            min="1"
            max="50"
          />
        </div>

        <div class="form-group">
          <label class="form-label">Задержка (сек)</label>
          <input
            v-model.number="techForm.delay"
            type="number"
            step="0.1"
            class="form-input"
            min="0.1"
          />
        </div>

        <div class="form-group checkbox-group">
          <label class="checkbox-label">
            <input
              v-model="techForm.get_details"
              type="checkbox"
              class="checkbox-input"
            />
            <span>Получать детальную информацию</span>
          </label>
        </div>
      </div>

      <div class="form-actions">
        <button 
          @click="handleParseByTechnologies" 
          class="btn-submit"
          :disabled="parsing"
        >
          <Play :size="18" />
          {{ parsing ? 'Запуск...' : 'Запустить парсинг' }}
        </button>
      </div>
    </div>

    <!-- Диалог подтверждения -->
    <ConfirmDialog
      :show="showConfirmDialog"
      title="Запустить парсинг?"
      message="Это запустит задачу парсинга в фоновом режиме. Процесс может занять некоторое время."
      confirm-text="Запустить"
      cancel-text="Отмена"
      @confirm="confirmParse"
      @close="showConfirmDialog = false"
      @cancel="showConfirmDialog = false"
    />
  </div>
</template>

<style lang="scss" scoped>
.parsing-control-view {
  .control-header {
    margin-bottom: 2rem;
    
    .control-title {
      font-size: 1.5rem;
      font-weight: 600;
      margin: 0;
      color: var(--bs-body-color, #212529);
      letter-spacing: -0.02em;
    }
  }
  
  .task-status-card {
    padding: 1.5rem;
    background: var(--bs-body-bg, #fff);
    border: 1px solid var(--bs-border-color, #e9ecef);
    border-radius: 12px;
    margin-bottom: 2rem;
    
    .task-status-header {
      display: flex;
      align-items: center;
      gap: 1rem;
      
      .status-icon-success {
        color: var(--bs-success, #198754);
      }
      
      .status-icon-danger {
        color: var(--bs-danger, #dc3545);
      }
      
      .status-icon-warning {
        color: var(--bs-warning, #ffc107);
      }
      
      .status-icon-secondary {
        color: var(--bs-secondary-color, #6c757d);
      }
      
      .task-status-info {
        flex: 1;
        
        .task-status-id {
          font-size: 0.875rem;
          font-weight: 600;
          color: var(--bs-body-color, #212529);
          margin-bottom: 0.25rem;
        }
        
        .task-status-text {
          font-size: 0.875rem;
          color: var(--bs-secondary-color, #6c757d);
        }
      }
      
      .btn-refresh-status {
        padding: 0.5rem 1rem;
        border: 1px solid var(--bs-border-color, #e9ecef);
        background: var(--bs-body-bg, #fff);
        border-radius: 8px;
        color: var(--bs-body-color, #212529);
        font-size: 0.875rem;
        cursor: pointer;
        transition: all 0.2s ease;
        
        &:hover {
          border-color: var(--bs-primary, #0d6efd);
          color: var(--bs-primary, #0d6efd);
        }
      }
    }
    
    .task-result {
      margin-top: 1rem;
      padding: 1rem;
      background: var(--bs-secondary-bg, #f8f9fa);
      border-radius: 8px;
      
      pre {
        margin: 0;
        font-size: 0.8125rem;
        color: var(--bs-body-color, #212529);
        white-space: pre-wrap;
        word-break: break-all;
      }
    }
    
    .task-error {
      margin-top: 1rem;
      padding: 1rem;
      background: var(--bs-danger-bg-subtle, #f8d7da);
      border: 1px solid var(--bs-danger-border-subtle, #f5c2c7);
      border-radius: 8px;
      color: var(--bs-danger, #dc3545);
      font-size: 0.875rem;
    }
  }
  
  .tabs {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 2rem;
    border-bottom: 1px solid var(--bs-border-color, #e9ecef);
    
    .tab-btn {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.875rem 1.5rem;
      border: none;
      background: transparent;
      color: var(--bs-secondary-color, #6c757d);
      font-size: 0.9375rem;
      font-weight: 500;
      cursor: pointer;
      border-bottom: 2px solid transparent;
      transition: all 0.2s ease;
      margin-bottom: -1px;
      
      &:hover {
        color: var(--bs-body-color, #212529);
      }
      
      &.active {
        color: var(--bs-primary, #0d6efd);
        border-bottom-color: var(--bs-primary, #0d6efd);
      }
    }
  }
  
  .form-card {
    padding: 2rem;
    background: var(--bs-body-bg, #fff);
    border: 1px solid var(--bs-border-color, #e9ecef);
    border-radius: 12px;
    
    .form-header {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin-bottom: 2rem;
      
      h3 {
        font-size: 1.125rem;
        font-weight: 600;
        margin: 0;
        color: var(--bs-body-color, #212529);
      }
    }
    
    .form-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 1.5rem;
      margin-bottom: 2rem;
      
      .form-group {
        &.full-width {
          grid-column: 1 / -1;
        }
        
        &.checkbox-group {
          display: flex;
          align-items: center;
        }
        
        .form-label {
          display: block;
          font-size: 0.875rem;
          font-weight: 500;
          color: var(--bs-body-color, #212529);
          margin-bottom: 0.5rem;
        }
        
        .form-input,
        .form-textarea {
          width: 100%;
          padding: 0.75rem;
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
        
        .form-textarea {
          resize: vertical;
          min-height: 80px;
        }
        
        .form-hint {
          display: block;
          font-size: 0.8125rem;
          color: var(--bs-secondary-color, #6c757d);
          margin-top: 0.375rem;
        }
        
        .checkbox-label {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          font-size: 0.9375rem;
          color: var(--bs-body-color, #212529);
          cursor: pointer;
          
          .checkbox-input {
            width: 18px;
            height: 18px;
            cursor: pointer;
          }
        }
      }
    }
    
    .form-actions {
      display: flex;
      justify-content: flex-end;
      
      .btn-submit {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.875rem 2rem;
        border: none;
        background: var(--bs-primary, #0d6efd);
        color: white;
        border-radius: 8px;
        font-size: 0.9375rem;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.2s ease;
        
        &:hover:not(:disabled) {
          background: var(--bs-primary-dark, #0b5ed7);
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(13, 110, 253, 0.3);
        }
        
        &:disabled {
          opacity: 0.6;
          cursor: not-allowed;
        }
      }
    }
  }
}

@media (max-width: 768px) {
  .parsing-control-view {
    .form-card {
      padding: 1.5rem;
      
      .form-grid {
        grid-template-columns: 1fr;
      }
    }
    
    .tabs {
      .tab-btn {
        padding: 0.75rem 1rem;
        font-size: 0.875rem;
      }
    }
  }
}
</style>
