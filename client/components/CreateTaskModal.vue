<template>
  <div class="modal fade show d-block" tabindex="-1" style="background-color: rgba(0,0,0,0.5);">
    <div class="modal-dialog modal-lg modal-dialog-centered">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">
            <Plus :size="24" class="me-2" />
            Создать задачу парсинга
          </h5>
          <button type="button" class="btn-close" @click="$emit('close')"></button>
        </div>
        
        <div class="modal-body">
          <form @submit.prevent="handleSubmit">
            <!-- Название задачи -->
            <div class="mb-3">
              <label class="form-label">Название задачи</label>
              <input 
                v-model="formData.name" 
                type="text" 
                class="form-control" 
                placeholder="Например: Парсинг Python вакансий Москва"
              >
            </div>

            <!-- Источник -->
            <div class="mb-3">
              <label class="form-label">Источник *</label>
              <select v-model="formData.source" class="form-select" required @change="loadSourceModes">
                <option value="">Выберите источник</option>
                <option v-for="source in sources" :key="source.value" :value="source.value">
                  {{ source.label }}
                </option>
              </select>
            </div>

            <!-- Режим парсинга -->
            <div class="mb-3">
              <label class="form-label">Режим парсинга *</label>
              <select v-model="formData.parsing_mode" class="form-select" required :disabled="!formData.source">
                <option value="">Выберите режим</option>
                <option v-for="mode in availableModes" :key="mode.value" :value="mode.value">
                  {{ mode.label }}
                </option>
              </select>
              <div class="form-text">
                API режим - быстрый и надежный. HTML режим - для случаев, когда API недоступен.
              </div>
            </div>

            <!-- ============================================== -->
            <!-- HEADHUNTER API -->
            <!-- ============================================== -->
            <div v-if="formData.source === 'headhunter' && formData.parsing_mode === 'api'" class="card mb-3">
              <div class="card-header bg-danger text-white">
                <strong>🔴 HeadHunter — API режим</strong>
              </div>
              <div class="card-body">
                <div class="row">
                  <div class="col-md-6 mb-3">
                    <label class="form-label">Регион *</label>
                    <select v-model="formData.config.area" class="form-select" required>
                      <option value="">Выберите регион</option>
                      <option value="1">Москва</option>
                      <option value="2">Санкт-Петербург</option>
                      <option value="113">Россия (все регионы)</option>
                      <option value="66">Нижний Новгород</option>
                      <option value="88">Казань</option>
                    </select>
                  </div>
                  
                  <div class="col-md-6 mb-3">
                    <label class="form-label">Количество страниц *</label>
                    <input 
                      v-model.number="formData.config.pages" 
                      type="number" 
                      class="form-control" 
                      min="1" 
                      max="20"
                      required
                    >
                    <div class="form-text">Макс. 20 страниц (API ограничение)</div>
                  </div>
                </div>

                <div class="row">
                  <div class="col-md-6 mb-3">
                    <label class="form-label">Вакансий на страницу</label>
                    <select v-model.number="formData.config.per_page" class="form-select">
                      <option :value="20">20</option>
                      <option :value="50">50</option>
                      <option :value="100">100 (рекомендуется)</option>
                    </select>
                  </div>
                  
                  <div class="col-md-6 mb-3">
                    <label class="form-label">Задержка между запросами (сек)</label>
                    <input 
                      v-model.number="formData.config.delay" 
                      type="number" 
                      class="form-control" 
                      min="0.1" 
                      max="5" 
                      step="0.1"
                    >
                    <div class="form-text">Рекомендуется 0.5 сек для API</div>
                  </div>
                </div>

                <div class="mb-3">
                  <label class="form-label">Поисковый запрос</label>
                  <input 
                    v-model="formData.config.text" 
                    type="text" 
                    class="form-control" 
                    placeholder="Например: python developer"
                  >
                  <div class="form-text">Оставьте пустым для поиска всех вакансий</div>
                </div>
              </div>
            </div>

            <!-- ============================================== -->
            <!-- HEADHUNTER HTML -->
            <!-- ============================================== -->
            <div v-else-if="formData.source === 'headhunter' && formData.parsing_mode === 'html'" class="card mb-3">
              <div class="card-header bg-warning text-dark">
                <strong>🟡 HeadHunter — HTML режим (веб-парсинг)</strong>
              </div>
              <div class="card-body">
                <div class="alert alert-warning mb-3">
                  <Info :size="18" class="me-2" />
                  HTML режим медленнее и может блокироваться. Используйте API режим если возможно.
                </div>

                <div class="row">
                  <div class="col-md-6 mb-3">
                    <label class="form-label">Регион *</label>
                    <select v-model="formData.config.area" class="form-select" required>
                      <option value="">Выберите регион</option>
                      <option value="1">Москва</option>
                      <option value="2">Санкт-Петербург</option>
                      <option value="113">Россия (все регионы)</option>
                    </select>
                  </div>
                  
                  <div class="col-md-6 mb-3">
                    <label class="form-label">Макс. страниц *</label>
                    <input 
                      v-model.number="formData.config.max_pages" 
                      type="number" 
                      class="form-control" 
                      min="1" 
                      max="50"
                      required
                    >
                    <div class="form-text">Рекомендуется не более 10 страниц</div>
                  </div>
                </div>

                <div class="row">
                  <div class="col-md-6 mb-3">
                    <label class="form-label">Вакансий на страницу</label>
                    <select v-model.number="formData.config.items_per_page" class="form-select">
                      <option :value="20">20</option>
                      <option :value="50">50 (рекомендуется)</option>
                      <option :value="100">100</option>
                    </select>
                  </div>
                  
                  <div class="col-md-6 mb-3">
                    <label class="form-label">Опыт работы</label>
                    <select v-model="formData.config.experience" class="form-select">
                      <option value="">Любой</option>
                      <option value="noExperience">Без опыта</option>
                      <option value="between1And3">1-3 года</option>
                      <option value="between3And6">3-6 лет</option>
                      <option value="moreThan6">Более 6 лет</option>
                    </select>
                  </div>
                </div>

                <div class="mb-3">
                  <label class="form-label">Поисковый запрос</label>
                  <input 
                    v-model="formData.config.text" 
                    type="text" 
                    class="form-control" 
                    placeholder="Например: python developer"
                  >
                </div>
              </div>
            </div>

            <!-- ============================================== -->
            <!-- HABR CAREER API -->
            <!-- ============================================== -->
            <div v-else-if="formData.source === 'habr_career' && formData.parsing_mode === 'api'" class="card mb-3">
              <div class="card-header bg-info text-white">
                <strong>🔵 Habr Career — API режим</strong>
              </div>
              <div class="card-body">
                <div class="row">
                  <div class="col-md-6 mb-3">
                    <label class="form-label">Макс. страниц *</label>
                    <input 
                      v-model.number="formData.config.max_pages" 
                      type="number" 
                      class="form-control" 
                      min="1" 
                      max="50"
                      required
                    >
                  </div>
                  
                  <div class="col-md-6 mb-3">
                    <label class="form-label">Задержка (сек)</label>
                    <input 
                      v-model.number="formData.config.delay" 
                      type="number" 
                      class="form-control" 
                      min="0.1" 
                      max="5" 
                      step="0.1"
                    >
                  </div>
                </div>

                <div class="mb-3">
                  <label class="form-label">Поисковый запрос</label>
                  <input 
                    v-model="formData.config.q" 
                    type="text" 
                    class="form-control" 
                    placeholder="Например: python"
                  >
                </div>
              </div>
            </div>

            <!-- ============================================== -->
            <!-- HABR CAREER HTML -->
            <!-- ============================================== -->
            <div v-else-if="formData.source === 'habr_career' && formData.parsing_mode === 'html'" class="card mb-3">
              <div class="card-header bg-warning text-dark">
                <strong>🟡 Habr Career — HTML режим</strong>
              </div>
              <div class="card-body">
                <div class="row">
                  <div class="col-md-6 mb-3">
                    <label class="form-label">Макс. страниц *</label>
                    <input 
                      v-model.number="formData.config.max_pages" 
                      type="number" 
                      class="form-control" 
                      min="1" 
                      max="30"
                      required
                    >
                  </div>
                </div>

                <div class="mb-3">
                  <label class="form-label">Поисковый запрос</label>
                  <input 
                    v-model="formData.config.q" 
                    type="text" 
                    class="form-control" 
                    placeholder="Например: python"
                  >
                </div>
              </div>
            </div>

            <!-- ============================================== -->
            <!-- SUPERJOB API -->
            <!-- ============================================== -->
            <div v-else-if="formData.source === 'superjob' && formData.parsing_mode === 'api'" class="card mb-3">
              <div class="card-header bg-success text-white">
                <strong>🟢 SuperJob — API режим</strong>
              </div>
              <div class="card-body">
                <div class="row">
                  <div class="col-md-6 mb-3">
                    <label class="form-label">Макс. страниц *</label>
                    <input 
                      v-model.number="formData.config.max_pages" 
                      type="number" 
                      class="form-control" 
                      min="1" 
                      max="50"
                      required
                    >
                  </div>
                  
                  <div class="col-md-6 mb-3">
                    <label class="form-label">Задержка (сек)</label>
                    <input 
                      v-model.number="formData.config.delay" 
                      type="number" 
                      class="form-control" 
                      min="0.1" 
                      max="5" 
                      step="0.1"
                    >
                  </div>
                </div>

                <div class="mb-3">
                  <label class="form-label">Ключевые слова</label>
                  <input 
                    v-model="formData.config.keywords" 
                    type="text" 
                    class="form-control" 
                    placeholder="Например: python developer"
                  >
                </div>
              </div>
            </div>

            <!-- ============================================== -->
            <!-- SUPERJOB HTML -->
            <!-- ============================================== -->
            <div v-else-if="formData.source === 'superjob' && formData.parsing_mode === 'html'" class="card mb-3">
              <div class="card-header bg-warning text-dark">
                <strong>🟡 SuperJob — HTML режим</strong>
              </div>
              <div class="card-body">
                <div class="row">
                  <div class="col-md-6 mb-3">
                    <label class="form-label">Макс. страниц *</label>
                    <input 
                      v-model.number="formData.config.max_pages" 
                      type="number" 
                      class="form-control" 
                      min="1" 
                      max="30"
                      required
                    >
                  </div>
                </div>

                <div class="mb-3">
                  <label class="form-label">Ключевые слова</label>
                  <input 
                    v-model="formData.config.keywords" 
                    type="text" 
                    class="form-control" 
                    placeholder="Например: python developer"
                  >
                </div>
              </div>
            </div>

            <!-- ============================================== -->
            <!-- ВЫБЕРИТЕ РЕЖИМ -->
            <!-- ============================================== -->
            <div v-else-if="formData.source && !formData.parsing_mode" class="alert alert-secondary">
              <Info :size="20" class="me-2" />
              Выберите режим парсинга для настройки параметров.
            </div>
          </form>
        </div>
        
        <div class="modal-footer">
          <button type="button" class="btn btn-secondary" @click="$emit('close')">
            Отмена
          </button>
          <button 
            type="button" 
            class="btn btn-primary" 
            :disabled="!isFormValid || loading"
            @click="handleSubmit"
          >
            <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
            Создать и запустить
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { Plus, Info } from 'lucide-vue-next'
import { useToast } from 'vue-toastification'
import { useParsingTasks } from '../composables/useParsingTasks'
import { tasksApi } from '../js/api'

const toast = useToast()
const emit = defineEmits(['close', 'created', 'task-created'])

const { createTask, loading } = useParsingTasks()

// Доступные источники и режимы (загружаются из API)
const sources = ref([])

// Form data
const formData = ref({
  name: '',
  source: '',
  parsing_mode: '',
  config: {}
})

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

    // handleResponse возвращает { data: ..., success: ..., message: ... }
    // Поэтому нужно брать response.data, а не response
    const sourcesData = response.data || response

    // Проверяем что sourcesData и sourcesData.sources существуют
    if (!sourcesData || !sourcesData.sources || !Array.isArray(sourcesData.sources)) {
      console.error('Invalid sources response:', sourcesData)
      toast.error('Некорректный ответ от сервера')
      return
    }
    
    // Преобразуем данные из API в формат для select
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

function loadSourceModes() {
  formData.value.parsing_mode = ''
  formData.value.config = {}
}

function getSourceLabel(sourceValue) {
  const source = sources.value.find(s => s.value === sourceValue)
  return source ? source.label : sourceValue
}

async function handleSubmit() {
  if (!isFormValid.value) return
  
  try {
    // Подготовка данных
    const taskData = {
      source: formData.value.source,
      parsing_mode: formData.value.parsing_mode,
      name: formData.value.name || `${getSourceLabel(formData.value.source)} парсинг`,
      config: { ...formData.value.config }
    }
    
    // Очистка пустых полей в config
    Object.keys(taskData.config).forEach(key => {
      if (taskData.config[key] === '' || taskData.config[key] === null) {
        delete taskData.config[key]
      }
    })
    
    const result = await createTask(taskData)
    
    toast.success('Задача создана и запущена!')
    
    // Эмитим событие с данными созданной задачи
    emit('task-created', result)
    emit('created')
    emit('close')
  } catch (error) {
    console.error('Error creating task:', error)
    toast.error('Ошибка создания задачи: ' + (error.message || 'Неизвестная ошибка'))
  }
}
</script>

<style scoped>
.modal {
  display: block;
}

.card-header {
  background-color: #f8f9fa;
}
</style>
