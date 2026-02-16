<template>
  <div class="vp-step-content">
    <div class="vp-step-header">
      <h3 class="vp-step-title">Проверьте параметры задачи</h3>
      <p class="vp-step-description">
        Убедитесь, что все параметры настроены правильно перед созданием задачи
      </p>
    </div>

    <div class="vp-summary-card">
      <div class="vp-summary-section">
        <h4 class="vp-summary-section-title">Основная информация</h4>
        <div class="vp-summary-item">
          <span class="vp-summary-label">Название:</span>
          <span class="vp-summary-value">{{ taskName || 'Не указано' }}</span>
        </div>
        <div class="vp-summary-item">
          <span class="vp-summary-label">Источник:</span>
          <span class="vp-summary-value">{{ getSourceLabel(source) }}</span>
        </div>
        <div class="vp-summary-item">
          <span class="vp-summary-label">Режим:</span>
          <span class="vp-summary-value">{{ getModeLabel(parsingMode) }}</span>
        </div>
      </div>

      <div class="vp-summary-section">
        <h4 class="vp-summary-section-title">Параметры поиска</h4>
        <div v-for="(value, key) in config" :key="key" class="vp-summary-item">
          <span class="vp-summary-label">{{ getConfigLabel(key) }}:</span>
          <span class="vp-summary-value">{{ formatConfigValue(key, value) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>

const props = defineProps({
  taskName: {
    type: String,
    default: ''
  },
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
  sources: {
    type: Array,
    required: true
  }
})

function getSourceLabel(source) {
  const sourceObj = props.sources.find(s => s.value === source)
  return sourceObj ? sourceObj.label : source
}

function getModeLabel(mode) {
  const source = props.sources.find(s => s.value === props.source)
  if (!source) return mode
  const modeObj = source.modes.find(m => m.value === mode)
  return modeObj ? modeObj.label : mode
}

function getConfigLabel(key) {
  const labels = {
    'area': 'Регион',
    'pages': 'Количество страниц',
    'max_pages': 'Макс. страниц',
    'per_page': 'Вакансий на страницу',
    'items_per_page': 'Вакансий на страницу',
    'delay': 'Задержка (сек)',
    'text': 'Поисковый запрос',
    'keyword': 'Поисковый запрос',
    'keywords': 'Поисковый запрос',
    'q': 'Поисковый запрос',
    'town': 'Город',
    'catalogues': 'Каталоги',
    'experience': 'Опыт работы'
  }
  return labels[key] || key
}

function formatConfigValue(key, value) {
  if (key === 'area') {
    const regions = {
      '1': 'Москва',
      '2': 'Санкт-Петербург',
      '113': 'Россия (все регионы)',
      '66': 'Нижний Новгород',
      '88': 'Казань',
      '4': 'Новосибирск',
      '3': 'Екатеринбург'
    }
    return regions[value] || value
  }
  if (key === 'experience') {
    const experiences = {
      'noExperience': 'Без опыта',
      'between1And3': '1-3 года',
      'between3And6': '3-6 лет',
      'moreThan6': 'Более 6 лет'
    }
    return experiences[value] || value || 'Любой'
  }
  return value || 'Не указано'
}
</script>

<style lang="scss" scoped>
@import '../../scss/components/create-task-steps';
</style>
