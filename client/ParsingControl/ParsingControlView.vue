<script setup>
import { ref, computed } from 'vue'
import { Play, Settings, CheckCircle, XCircle, Clock, Code, Users, AlertCircle } from 'lucide-vue-next'
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
  if (!taskStatus.value) return 'vp-text-secondary'
  const status = taskStatus.value.status
  if (status === 'SUCCESS') return 'vp-text-success'
  if (status === 'FAILURE') return 'vp-text-danger'
  return 'vp-text-warning'
})
</script>

<template>
  <div class="vp-parsing-control">
    <div class="vp-page-header">
      <h2>Управление парсингом</h2>
    </div>

    <!-- Статус задачи -->
    <div v-if="taskId" class="vp-task-card">
      <div class="vp-task-header">
        <component :is="taskStatusIcon" :size="24" :class="taskStatusColor" />
        <div class="task-status-info">
          <div class="task-status-id vp-text-sm">Task ID: {{ taskId }}</div>
          <div class="task-status-text vp-text-muted">{{ taskStatusText }}</div>
        </div>
        <button 
          @click="checkTaskStatus()" 
          class="vp-btn-secondary"
        >
          Обновить
        </button>
      </div>
      <div v-if="taskStatus && taskStatus.result" class="task-result">
        <pre>{{ JSON.stringify(taskStatus.result, null, 2) }}</pre>
      </div>
      <div 
        v-if="taskStatus && taskStatus.error" 
        class="vp-alert vp-alert-danger"
      >
        <AlertCircle :size="18" class="vp-alert-icon" />
        <div class="vp-alert-content">
          <div class="vp-alert-title">Ошибка задачи:</div>
          <div>{{ taskStatus.error }}</div>
        </div>
      </div>
    </div>

    <!-- Вкладки -->
    <div class="vp-tabs">
      <button 
        class="vp-tab"
        :class="{ 'vp-tab-active': activeTab === 'roles' }"
        @click="activeTab = 'roles'"
      >
        <Users :size="18" />
        По ролям
      </button>
      <button 
        class="vp-tab"
        :class="{ 'vp-tab-active': activeTab === 'technologies' }"
        @click="activeTab = 'technologies'"
      >
        <Code :size="18" />
        По технологиям
      </button>
    </div>

    <!-- Парсинг по ролям -->
    <div v-if="activeTab === 'roles'" class="vp-tab-content">
      <div class="vp-form-section">
        <div class="vp-form-section-header">
        <Settings :size="20" />
        <span>Парсинг по профессиональным ролям</span>
      </div>
      <div class="vp-form-section-body">
        <div class="vp-form-section-grid">
          <div class="vp-form-section-field">
          <label>Регион (area)</label>
          <input
            v-model.number="rolesForm.area"
            type="number"
            class="vp-form-control"
            placeholder="113 (Москва)"
          />
          <small class="vp-form-text">113 - Москва, 2 - СПб, и т.д.</small>
        </div>

        <div class="vp-form-section-field">
          <label>Количество страниц</label>
          <input
            v-model.number="rolesForm.pages"
            type="number"
            class="vp-form-control"
            min="1"
            max="200"
          />
        </div>

        <div class="vp-form-section-field">
          <label>Задержка (сек)</label>
          <input
            v-model.number="rolesForm.delay"
            type="number"
            step="0.1"
            class="vp-form-control"
            min="0.1"
          />
        </div>

        <div class="vp-form-section-field">
          <label>Параллельных ролей</label>
          <input
            v-model.number="rolesForm.max_concurrent_roles"
            type="number"
            class="vp-form-control"
            min="1"
            max="10"
          />
        </div>

        <div class="vp-form-section-field">
          <label>Размер батча</label>
          <input
            v-model.number="rolesForm.batch_size"
            type="number"
            class="vp-form-control"
            min="1"
            max="50"
          />
        </div>

        <div class="vp-form-section-field">
          <label>
            <input
              v-model="rolesForm.get_details"
              type="checkbox"
            />
            <span>Получать детальную информацию</span>
          </label>
        </div>

        <div class="vp-form-section-field">
          <label>
            <input
              v-model="rolesForm.force_refresh_roles"
              type="checkbox"
            />
            <span>Принудительно обновить список ролей</span>
          </label>
        </div>

        <div class="vp-form-section-field">
          <label>
            <input
              v-model="rolesForm.incremental"
              type="checkbox"
            />
            <span>Инкрементальный режим</span>
          </label>
        </div>
      </div>
      </div>

      <div class="vp-form-section-actions">
        <button 
          @click="handleParseByRoles" 
          class="vp-btn-primary"
          :disabled="parsing"
        >
          <Play :size="18" />
          {{ parsing ? 'Запуск...' : 'Запустить парсинг' }}
        </button>
      </div>
      </div>
    </div>

    <!-- Парсинг по технологиям -->
    <div v-if="activeTab === 'technologies'" class="vp-tab-content">
      <div class="vp-form-section">
        <div class="vp-form-section-header">
        <Settings :size="20" />
        <span>Парсинг по технологиям</span>
      </div>
      <div class="vp-form-section-body">
        <div class="vp-form-section-grid">
          <div class="vp-form-section-field">
          <label>Технологии (через запятую)</label>
          <textarea
            v-model="techForm.technologies"
            class="vp-form-control"
            rows="3"
            placeholder="Python, Django, Vue.js, React..."
          ></textarea>
          <small class="vp-form-text">Укажите технологии через запятую</small>
        </div>

        <div class="vp-form-section-field">
          <label>Регион (area)</label>
          <input
            v-model.number="techForm.area"
            type="number"
            class="vp-form-control"
            placeholder="113 (Москва)"
          />
        </div>

        <div class="vp-form-section-field">
          <label>Количество страниц</label>
          <input
            v-model.number="techForm.pages"
            type="number"
            class="vp-form-control"
            min="1"
            max="50"
          />
        </div>

        <div class="vp-form-section-field">
          <label>Задержка (сек)</label>
          <input
            v-model.number="techForm.delay"
            type="number"
            step="0.1"
            class="vp-form-control"
            min="0.1"
          />
        </div>

        <div class="vp-form-section-field">
          <label>
            <input
              v-model="techForm.get_details"
              type="checkbox"
            />
            <span>Получать детальную информацию</span>
          </label>
        </div>
      </div>
      </div>

      <div class="vp-form-section-actions">
        <button 
          @click="handleParseByTechnologies" 
          class="vp-btn-primary"
          :disabled="parsing"
        >
          <Play :size="18" />
          {{ parsing ? 'Запуск...' : 'Запустить парсинг' }}
        </button>
      </div>
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
@import '../scss/pages/parsing-control';
</style>
