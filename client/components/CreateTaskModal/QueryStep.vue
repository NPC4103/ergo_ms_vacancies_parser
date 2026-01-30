<template>
  <div class="vp-step-content">
    <div class="vp-step-header">
      <h3 class="vp-step-title">Параметры поиска</h3>
      <p class="vp-step-description">
        Настройте параметры поиска вакансий для выбранного источника
      </p>
    </div>

    <!-- HeadHunter API -->
    <template v-if="source === 'headhunter' && parsingMode === 'api'">
      <Select
        v-model="localConfig.area"
        :options="regionOptions"
        label="Регион"
        placeholder="Выберите регион"
        :required="true"
        :error="errors.area"
      />

      <div class="vp-form-grid">
        <div class="vp-form-group">
          <label class="vp-form-label">
            Количество страниц <span class="vp-required">*</span>
          </label>
          <input 
            v-model.number="localConfig.pages" 
            type="number" 
            class="vp-form-control" 
            min="1" 
            max="20"
            required
          >
          <div class="vp-form-help">
            <Info :size="14" />
            <span>Максимум 20 страниц (ограничение API HeadHunter)</span>
          </div>
        </div>

        <Select
          v-model.number="localConfig.per_page"
          :options="perPageOptions"
          label="Вакансий на страницу"
          placeholder="Выберите количество"
        />
      </div>

      <div class="vp-form-group">
        <label class="vp-form-label">Задержка между запросами (сек)</label>
        <input 
          v-model.number="localConfig.delay" 
          type="number" 
          class="vp-form-control" 
          min="0.1" 
          max="5" 
          step="0.1"
        >
      </div>

      <div class="vp-form-group">
        <label class="vp-form-label">Поисковый запрос</label>
        <input 
          v-model="localConfig.text" 
          type="text" 
          class="vp-form-control" 
          placeholder="Например: python developer"
        >
      </div>
    </template>

    <!-- HeadHunter HTML -->
    <template v-else-if="source === 'headhunter' && parsingMode === 'html'">
      <div class="vp-alert vp-alert-warning">
        <AlertTriangle :size="18" />
        <div class="vp-alert-content">
          HTML режим медленнее и может блокироваться. Используйте API режим если возможно.
        </div>
      </div>

      <div class="vp-form-grid">
        <div class="vp-form-group">
          <label class="vp-form-label">
            Регион <span class="vp-required">*</span>
          </label>
          <Select
            v-model="localConfig.area"
            :options="regionOptionsHtml"
            label="Регион"
            placeholder="Выберите регион"
            :required="true"
          />
        </div>

        <div class="vp-form-group">
          <label class="vp-form-label">
            Макс. страниц <span class="vp-required">*</span>
          </label>
          <input 
            v-model.number="localConfig.max_pages" 
            type="number" 
            class="vp-form-control" 
            min="1" 
            max="50"
            required
          >
        </div>
      </div>

      <div class="vp-form-grid">
        <div class="vp-form-group">
          <label class="vp-form-label">Вакансий на страницу</label>
          <Select
            v-model.number="localConfig.items_per_page"
            :options="itemsPerPageOptions"
            label="Вакансий на страницу"
            placeholder="Выберите количество"
          />
        </div>

        <div class="vp-form-group">
          <label class="vp-form-label">Опыт работы</label>
          <Select
            v-model="localConfig.experience"
            :options="experienceOptions"
            label="Опыт работы"
            placeholder="Выберите опыт"
          />
        </div>
      </div>

      <div class="vp-form-group">
        <label class="vp-form-label">Поисковый запрос</label>
        <input 
          v-model="localConfig.text" 
          type="text" 
          class="vp-form-control" 
          placeholder="Например: python developer"
        >
      </div>
    </template>

    <!-- Habr Career API -->
    <template v-else-if="source === 'habr_career' && parsingMode === 'api'">
      <div class="vp-form-grid">
        <div class="vp-form-group">
          <label class="vp-form-label">
            Макс. страниц <span class="vp-required">*</span>
          </label>
          <input 
            v-model.number="localConfig.max_pages" 
            type="number" 
            class="vp-form-control" 
            min="1" 
            max="50"
            required
          >
        </div>

        <div class="vp-form-group">
          <label class="vp-form-label">Задержка (сек)</label>
          <input 
            v-model.number="localConfig.delay" 
            type="number" 
            class="vp-form-control" 
            min="0.1" 
            max="5" 
            step="0.1"
          >
        </div>
      </div>

      <div class="vp-form-group">
        <label class="vp-form-label">Поисковый запрос</label>
        <input 
          v-model="localConfig.q" 
          type="text" 
          class="vp-form-control" 
          placeholder="Например: python"
        >
      </div>
    </template>

    <!-- Habr Career HTML -->
    <template v-else-if="source === 'habr_career' && parsingMode === 'html'">
      <div class="vp-form-group">
        <label class="vp-form-label">
          Макс. страниц <span class="vp-required">*</span>
        </label>
        <input 
          v-model.number="localConfig.max_pages" 
          type="number" 
          class="vp-form-control" 
          min="1" 
          max="30"
          required
        >
      </div>

      <div class="vp-form-group">
        <label class="vp-form-label">Поисковый запрос</label>
        <input 
          v-model="localConfig.q" 
          type="text" 
          class="vp-form-control" 
          placeholder="Например: python"
        >
      </div>
    </template>

    <!-- SuperJob API -->
    <template v-else-if="source === 'superjob' && parsingMode === 'api'">
      <div class="vp-form-grid">
        <div class="vp-form-group">
          <label class="vp-form-label">
            Макс. страниц <span class="vp-required">*</span>
          </label>
          <input 
            v-model.number="localConfig.max_pages" 
            type="number" 
            class="vp-form-control" 
            min="1" 
            max="50"
            required
          >
        </div>

        <div class="vp-form-group">
          <label class="vp-form-label">Задержка (сек)</label>
          <input 
            v-model.number="localConfig.delay" 
            type="number" 
            class="vp-form-control" 
            min="0.1" 
            max="5" 
            step="0.1"
          >
        </div>
      </div>

      <div class="vp-form-group">
        <label class="vp-form-label">Ключевые слова</label>
        <input 
          v-model="localConfig.keywords" 
          type="text" 
          class="vp-form-control" 
          placeholder="Например: python developer"
        >
      </div>
    </template>

    <!-- SuperJob HTML -->
    <template v-else-if="source === 'superjob' && parsingMode === 'html'">
      <div class="vp-form-group">
        <label class="vp-form-label">
          Макс. страниц <span class="vp-required">*</span>
        </label>
        <input 
          v-model.number="localConfig.max_pages" 
          type="number" 
          class="vp-form-control" 
          min="1" 
          max="30"
          required
        >
      </div>

      <div class="vp-form-group">
        <label class="vp-form-label">Ключевые слова</label>
        <input 
          v-model="localConfig.keywords" 
          type="text" 
          class="vp-form-control" 
          placeholder="Например: python developer"
        >
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Info, AlertTriangle } from 'lucide-vue-next'
import Select from '../Select.vue'

const props = defineProps({
  source: {
    type: String,
    required: true
  },
  parsingMode: {
    type: String,
    required: true
  },
  config: {
    type: Object,
    required: true
  },
  errors: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['update:config'])

const localConfig = computed({
  get: () => props.config,
  set: (value) => emit('update:config', value)
})

const regionOptions = [
  { value: '1', label: 'Москва' },
  { value: '2', label: 'Санкт-Петербург' },
  { value: '113', label: 'Россия (все регионы)' },
  { value: '66', label: 'Нижний Новгород' },
  { value: '88', label: 'Казань' },
  { value: '4', label: 'Новосибирск' },
  { value: '3', label: 'Екатеринбург' }
]

const regionOptionsHtml = [
  { value: '1', label: 'Москва' },
  { value: '2', label: 'Санкт-Петербург' },
  { value: '113', label: 'Россия (все регионы)' }
]

const perPageOptions = [
  { value: 20, label: '20' },
  { value: 50, label: '50' },
  { value: 100, label: '100 (рекомендуется)' }
]

const itemsPerPageOptions = [
  { value: 20, label: '20' },
  { value: 50, label: '50 (рекомендуется)' },
  { value: 100, label: '100' }
]

const experienceOptions = [
  { value: '', label: 'Любой' },
  { value: 'noExperience', label: 'Без опыта' },
  { value: 'between1And3', label: '1-3 года' },
  { value: 'between3And6', label: '3-6 лет' },
  { value: 'moreThan6', label: 'Более 6 лет' }
]
</script>

<style lang="scss" scoped>
@import '../../scss/components/create-task-steps';
</style>
