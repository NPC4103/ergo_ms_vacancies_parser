<template>
  <div class="vp-modal" @mousedown.self="$emit('close')">
    <div class="vp-modal-dialog vp-modal-dialog-large">
      <div class="vp-modal-content">
        <div class="vp-modal-header">
          <h5 class="vp-modal-title">
            <Plus :size="24" />
            Создать задачу парсинга
          </h5>
          <button type="button" class="vp-modal-close" @click="$emit('close')">
            <X :size="20" />
          </button>
        </div>
        
        <div class="vp-modal-body">
          <!-- Индикатор шагов -->
          <StepIndicator :steps="steps" :current-step="currentStep" />

          <!-- Шаг 1: Источник и режим -->
          <SourceStep
            v-if="currentStep === 0"
            v-model="formData"
            :sources="sources"
            :errors="errors"
            @source-changed="handleSourceChanged"
            @mode-changed="handleModeChanged"
          />

          <!-- Шаг 2: Параметры поиска -->
          <QueryStep
            v-if="currentStep === 1"
            :source="formData.source"
            :parsing-mode="formData.parsing_mode"
            v-model:config="formData.config"
            :errors="errors"
          />

          <!-- Шаг 3: Проверка и название -->
          <SummaryStep
            v-if="currentStep === 2"
            :task-name="formData.name"
            :source="formData.source"
            :parsing-mode="formData.parsing_mode"
            :config="formData.config"
            :sources="sources"
          />
        </div>
        
        <div class="vp-modal-footer">
          <div class="vp-modal-footer-left">
            <button 
              v-if="currentStep > 0"
              type="button" 
              class="vp-btn-secondary" 
              @click="prevStep"
              :disabled="loading"
            >
              Назад
            </button>
          </div>
          
          <div class="vp-modal-footer-right">
            <button 
              type="button" 
              class="vp-btn-secondary" 
              @click="$emit('close')"
              :disabled="loading"
            >
              Отмена
            </button>
            <button 
              v-if="currentStep < steps.length - 1"
              type="button" 
              class="vp-btn-primary" 
              :disabled="!canProceed || loading"
              @click="nextStep"
            >
              Далее
            </button>
            <button 
              v-else
              type="button" 
              class="vp-btn-primary" 
              :disabled="!isFormValid || loading"
              @click="handleSubmit"
            >
              <Loader v-if="loading" :size="16" class="vp-spinner-inline" />
              Создать и запустить
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { Plus, X, Loader } from 'lucide-vue-next'
import { useToast } from 'vue-toastification'
import { useParsingTasks } from '../composables/useParsingTasks'
import { tasksApi } from '../js/api'
import StepIndicator from './CreateTaskModal/StepIndicator.vue'
import SourceStep from './CreateTaskModal/SourceStep.vue'
import QueryStep from './CreateTaskModal/QueryStep.vue'
import SummaryStep from './CreateTaskModal/SummaryStep.vue'

const toast = useToast()
const emit = defineEmits(['close', 'created', 'task-created'])

const { createTask, loading } = useParsingTasks()

// Шаги мастера
const steps = [
  { label: 'Источник и режим', key: 'source' },
  { label: 'Параметры поиска', key: 'query' },
  { label: 'Проверка', key: 'summary' }
]

const currentStep = ref(0)

// Доступные источники и режимы
const sources = ref([])

// Form data
const formData = ref({
  name: '',
  source: '',
  parsing_mode: '',
  config: {}
})

// Ошибки валидации
const errors = ref({})

// Дефолтные конфиги для разных режимов
const defaultConfigs = {
  headhunter_api: {
    area: '',
    pages: 5,
    per_page: 100,
    delay: 0.5,
    text: ''
  },
  headhunter_html: {
    area: '',
    max_pages: 10,
    items_per_page: 50,
    experience: '',
    text: ''
  },
  habr_career_api: {
    max_pages: 10,
    delay: 0.5,
    q: ''
  },
  habr_career_html: {
    max_pages: 10,
    q: ''
  },
  superjob_api: {
    max_pages: 10,
    delay: 0.5,
    keywords: ''
  },
  superjob_html: {
    max_pages: 10,
    keywords: ''
  }
}

// Computed
const availableModes = computed(() => {
  if (!formData.value.source) return []
  const source = sources.value.find(s => s.value === formData.value.source)
  return source ? source.modes : []
})

const canProceed = computed(() => {
  if (currentStep.value === 0) {
    return formData.value.source && formData.value.parsing_mode
  }
  if (currentStep.value === 1) {
    return validateQueryStep()
  }
  return true
})

const isFormValid = computed(() => {
  if (!formData.value.source || !formData.value.parsing_mode) return false
  
  const mode = formData.value.parsing_mode
  const source = formData.value.source
  const config = formData.value.config
  
  // HeadHunter API
  if (source === 'headhunter' && mode === 'api') {
    return config.area && config.pages > 0
  }
  
  // HeadHunter HTML
  if (source === 'headhunter' && mode === 'html') {
    return config.area && config.max_pages > 0
  }
  
  // Habr Career (API и HTML)
  if (source === 'habr_career') {
    return config.max_pages > 0
  }
  
  // SuperJob (API и HTML)
  if (source === 'superjob') {
    return config.max_pages > 0
  }
  
  return true
})

// Watch для переключения config при смене режима
watch(
  () => [formData.value.source, formData.value.parsing_mode],
  ([newSource, newMode]) => {
    if (newSource && newMode) {
      const configKey = `${newSource}_${newMode}`
      formData.value.config = { ...defaultConfigs[configKey] || {} }
      errors.value = {}
    }
  }
)

// Lifecycle
onMounted(async () => {
  await loadSources()
})

// Methods
async function loadSources() {
  try {
    const response = await tasksApi.getSources()
    const sourcesData = response.data || response

    if (!sourcesData || !sourcesData.sources || !Array.isArray(sourcesData.sources)) {
      console.error('Invalid sources response:', sourcesData)
      toast.error('Некорректный ответ от сервера')
      return
    }
    
    sources.value = sourcesData.sources.map(source => ({
      value: source.id,
      label: source.name,
      modes: source.modes
        .filter(mode => mode.available)
        .map(mode => ({
          value: mode.id,
          label: mode.name
        }))
    }))
  } catch (error) {
    console.error('Error loading sources:', error)
    toast.error('Ошибка загрузки источников: ' + (error.message || 'Неизвестная ошибка'))
  }
}

function handleSourceChanged(source) {
  formData.value.parsing_mode = ''
  formData.value.config = {}
  errors.value = {}
}

function handleModeChanged(mode) {
  formData.value.config = {}
  errors.value = {}
}

function validateQueryStep() {
  errors.value = {}
  const { source, parsing_mode, config } = formData.value

  if (source === 'headhunter' && parsing_mode === 'api') {
    if (!config.area) {
      errors.value.area = 'Выберите регион'
      return false
    }
    if (!config.pages || config.pages < 1 || config.pages > 20) {
      errors.value.pages = 'Укажите количество страниц от 1 до 20'
      return false
    }
  }

  if (source === 'headhunter' && parsing_mode === 'html') {
    if (!config.area) {
      errors.value.area = 'Выберите регион'
      return false
    }
    if (!config.max_pages || config.max_pages < 1) {
      errors.value.max_pages = 'Укажите количество страниц'
      return false
    }
  }

  if (source === 'habr_career' || source === 'superjob') {
    if (!config.max_pages || config.max_pages < 1) {
      errors.value.max_pages = 'Укажите количество страниц'
      return false
    }
  }

  return true
}

function nextStep() {
  if (currentStep.value === 1 && !validateQueryStep()) {
    return
  }
  if (currentStep.value < steps.length - 1) {
    currentStep.value++
  }
}

function prevStep() {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

function getSourceLabel(sourceValue) {
  const source = sources.value.find(s => s.value === sourceValue)
  return source ? source.label : sourceValue
}

function formatValidationErrors(responseData) {
  if (!responseData || typeof responseData !== 'object') return []
  const list = []
  for (const [field, messages] of Object.entries(responseData)) {
    const msg = Array.isArray(messages) ? messages.join(' ') : String(messages)
    if (msg) list.push(field + ': ' + msg)
  }
  return list
}

async function handleSubmit() {
  if (!isFormValid.value) {
    toast.error('Заполните все обязательные поля')
    return
  }

  const src = formData.value.source
  const mode = formData.value.parsing_mode
  if (!src || !mode) {
    toast.error('Выберите источник и режим парсинга')
    return
  }

  errors.value = {}
  try {
    const config = { ...(formData.value.config || {}) }
    Object.keys(config).forEach(key => {
      if (config[key] === '' || config[key] === null || config[key] === undefined) {
        delete config[key]
      }
    })

    const taskData = {
      source: String(src),
      parsing_mode: String(mode),
      name: formData.value.name?.trim() || `${getSourceLabel(src)} парсинг`,
      config
    }

    if (import.meta.env?.DEV) {
      console.debug('POST /api/vacancies_parser/tasks/ payload:', JSON.stringify(taskData, null, 2))
    }
    const result = await createTask(taskData)

    toast.success('Задача создана и запущена!')
    emit('task-created', result)
    emit('created')
    emit('close')
  } catch (err) {
    console.error('Error creating task:', err)
    const responseData = err.responseData || err.response?.data
    if (responseData && typeof responseData === 'object') {
      const fieldErrors = {}
      for (const [key, value] of Object.entries(responseData)) {
        if (key === 'detail') continue
        if (Array.isArray(value)) {
          fieldErrors[key] = value.join(' ')
        } else if (value && typeof value === 'object' && !Array.isArray(value)) {
          fieldErrors[key] = Object.values(value).flat().join(' ')
        } else {
          fieldErrors[key] = String(value)
        }
      }
      errors.value = fieldErrors
      const detail = responseData.detail
      const lines = formatValidationErrors(responseData)
      let msg = typeof detail === 'string' ? detail : (lines.length ? lines[0] : (err.message || 'Ошибка создания задачи'))
      if (responseData.broker && Array.isArray(responseData.broker) && responseData.broker.length > 0) {
        msg = 'Сервис очередей недоступен. Убедитесь, что брокер (БД из databases.yaml) запущен и доступен, и что API и Worker используют одну конфигурацию. Либо запустите Worker с CELERY_USE_LOCAL=true для локального SQLite.'
      }
      toast.error(msg)
    } else {
      toast.error(err.message || 'Ошибка создания задачи')
    }
  }
}
</script>

<style lang="scss" scoped>
@import '../scss/components/modal';

.vp-modal-dialog-large {
  max-width: 800px;
}

.vp-modal-footer {
  @include vp-flex(row, $vp-spacing-sm, center, space-between);

  @include vp-mobile {
    flex-direction: column-reverse;
    gap: $vp-spacing-sm;

    button {
      width: 100%;
    }
  }
}

.vp-modal-footer-left {
  @include vp-flex(row, $vp-spacing-sm, center, flex-start);
}

.vp-modal-footer-right {
  @include vp-flex(row, $vp-spacing-sm, center, flex-end);
}

.vp-spinner-inline {
  animation: vp-spin 0.8s linear infinite;
  margin-right: $vp-spacing-xs;
}

@keyframes vp-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
