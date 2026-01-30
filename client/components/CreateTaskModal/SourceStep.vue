<template>
  <div class="vp-step-content">
    <div class="vp-step-header">
      <h3 class="vp-step-title">Выберите источник и режим парсинга</h3>
      <p class="vp-step-description">
        Выберите платформу для парсинга вакансий и предпочтительный режим работы
      </p>
    </div>

    <div class="vp-form-group">
      <label class="vp-form-label">Название задачи</label>
      <input
        v-model="localData.name"
        type="text"
        class="vp-form-control"
        placeholder="Например: Парсинг Python вакансий Москва"
      >
    </div>

    <Select
      v-model="localData.source"
      :options="sourceOptions"
      label="Источник данных"
      placeholder="Выберите источник"
      :required="true"
      :error="errors.source"
      @change="handleSourceChange"
    />

    <Select
      v-model="localData.parsing_mode"
      :options="modeOptions"
      label="Режим парсинга"
      :placeholder="parsingModePlaceholder"
      :required="true"
      :disabled="!localData.source"
      :error="errors.parsing_mode"
      @change="handleModeChange"
    />

    <div v-if="localData.source && localData.parsing_mode" class="vp-source-info">
      <div class="vp-source-info-card" :class="getSourceCardClass(localData.source)">
        <component :is="getSourceIcon(localData.source)" :size="24" />
        <div>
          <div class="vp-source-info-title">{{ getSourceLabel(localData.source) }}</div>
          <div class="vp-source-info-subtitle">{{ getModeLabel(localData.parsing_mode) }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Database, Briefcase, Building2 } from 'lucide-vue-next'
import Select from '../Select.vue'
import { getSourceLogoUrl } from '../../js/sourceLogos'

const props = defineProps({
  modelValue: {
    type: Object,
    required: true
  },
  sources: {
    type: Array,
    required: true
  },
  errors: {
    type: Object,
    default: () => ({})
  }
})

const emit = defineEmits(['update:modelValue', 'source-changed', 'mode-changed'])

const localData = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const availableModes = computed(() => {
  if (!localData.value.source) return []
  const source = props.sources.find(s => s.value === localData.value.source)
  return source ? source.modes : []
})

const sourceOptions = computed(() => {
  return props.sources.map(source => {
    const iconUrl = getSourceLogoUrl(source.value)
    return {
      value: source.value,
      label: source.label,
      ...(iconUrl ? { iconUrl } : {}),
      icon: getSourceIcon(source.value)
    }
  })
})

const modeOptions = computed(() => {
  return availableModes.value.map(mode => ({
    value: mode.value,
    label: mode.label
  }))
})

const parsingModePlaceholder = computed(() =>
  localData.value.source ? 'Выберите режим' : 'Сначала выберите источник'
)

function handleSourceChange() {
  localData.value.parsing_mode = ''
  emit('source-changed', localData.value.source)
}

function handleModeChange() {
  emit('mode-changed', localData.value.parsing_mode)
}

function getSourceLabel(source) {
  const sourceObj = props.sources.find(s => s.value === source)
  return sourceObj ? sourceObj.label : source
}

function getModeLabel(mode) {
  const modeObj = availableModes.value.find(m => m.value === mode)
  return modeObj ? modeObj.label : mode
}

function getSourceCardClass(source) {
  const classes = {
    'headhunter': 'vp-source-info-danger',
    'habr_career': 'vp-source-info-info',
    'superjob': 'vp-source-info-success'
  }
  return classes[source] || ''
}

function getSourceIcon(source) {
  const icons = {
    'headhunter': Briefcase,
    'habr_career': Building2,
    'superjob': Database
  }
  return icons[source] || Database
}
</script>

<style lang="scss" scoped>
@import '../../scss/components/create-task-steps';
</style>
