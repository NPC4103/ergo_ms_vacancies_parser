<template>
  <div class="vp-select-wrapper" :class="{ 'vp-select-disabled': disabled, 'vp-select-error': hasError }">
    <label v-if="label" class="vp-select-label">
      {{ label }}
      <span v-if="required" class="vp-required">*</span>
    </label>
    
    <div 
      class="vp-select-container" 
      :class="{ 
        'vp-select-focused': isOpen, 
        'vp-select-disabled': disabled,
        'vp-select-open': isOpen
      }"
      @click="handleContainerClick"
      v-click-outside="handleClickOutside"
    >
      <select
        :id="selectId"
        ref="selectRef"
        :value="modelValue === null ? '' : modelValue"
        :disabled="disabled"
        :required="required"
        class="vp-select-native"
        @change="handleChange"
        @focus="handleFocus"
        @blur="handleBlur"
      >
        <option
          v-for="option in options"
          :key="getOptionValue(option)"
          :value="getOptionValue(option) === null ? '' : getOptionValue(option)"
        >
          {{ getOptionLabel(option) }}
        </option>
      </select>
      
      <div 
        class="vp-select-display"
        :class="{ 'vp-select-placeholder': !selectedOption }"
        @click="toggleDropdown"
      >
        <div class="vp-select-content">
          <span v-if="selectedOption?.iconUrl" class="vp-select-icon">
            <img :src="selectedOption.iconUrl" alt="" class="vp-select-icon-img" />
          </span>
          <span v-else-if="selectedOption?.icon" class="vp-select-icon">
            <component :is="selectedOption.icon" :size="18" />
          </span>
          <span class="vp-select-text">
            {{ selectedOption ? getOptionLabel(selectedOption) : placeholder }}
          </span>
        </div>
        <ChevronDown 
          :size="18" 
          class="vp-select-arrow"
          :class="{ 'vp-select-arrow-open': isOpen }"
        />
      </div>

      <!-- Кастомный dropdown -->
      <Transition name="vp-dropdown">
        <div v-if="isOpen" class="vp-select-dropdown">
          <div class="vp-select-options">
            <div
              v-for="option in options"
              :key="getOptionValue(option)"
              class="vp-select-option"
              :class="{
                'vp-select-option-selected': isOptionSelected(option),
                'vp-select-option-hover': hoveredIndex === getOptionIndex(option)
              }"
              @click="selectOption(option)"
              @mouseenter="hoveredIndex = getOptionIndex(option)"
              @mouseleave="hoveredIndex = null"
            >
              <span v-if="option.iconUrl" class="vp-select-option-icon">
                <img :src="option.iconUrl" alt="" class="vp-select-icon-img" />
              </span>
              <span v-else-if="option.icon" class="vp-select-option-icon">
                <component :is="option.icon" :size="18" />
              </span>
              <span class="vp-select-option-text">{{ getOptionLabel(option) }}</span>
              <Check v-if="isOptionSelected(option)" :size="16" class="vp-select-option-check" />
            </div>
          </div>
        </div>
      </Transition>
    </div>
    
    <div v-if="helpText" class="vp-select-help">
      <Info :size="14" />
      <span v-html="helpText"></span>
    </div>
    
    <div v-if="hasError && errorMessage" class="vp-select-error-message">
      {{ errorMessage }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ChevronDown, Info, Check } from 'lucide-vue-next'

const props = defineProps({
  modelValue: {
    type: [String, Number, null],
    default: null
  },
  options: {
    type: Array,
    required: true
  },
  label: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: 'Выберите значение'
  },
  required: {
    type: Boolean,
    default: false
  },
  disabled: {
    type: Boolean,
    default: false
  },
  helpText: {
    type: String,
    default: ''
  },
  error: {
    type: String,
    default: ''
  },
  optionValue: {
    type: String,
    default: 'value'
  },
  optionLabel: {
    type: String,
    default: 'label'
  }
})

const emit = defineEmits(['update:modelValue', 'change', 'focus', 'blur'])

const selectRef = ref(null)
const isOpen = ref(false)
const hoveredIndex = ref(null)
const selectId = `vp-select-${Math.random().toString(36).substr(2, 9)}`

const hasError = computed(() => !!props.error)
const errorMessage = computed(() => props.error)

const selectedOption = computed(() => {
  if (props.modelValue === null || props.modelValue === undefined || props.modelValue === '') {
    return null
  }
  return props.options.find(opt => getOptionValue(opt) === props.modelValue) || null
})

function getOptionValue(option) {
  if (typeof option === 'string' || typeof option === 'number') {
    return option
  }
  return option[props.optionValue] ?? option.value ?? option
}

function getOptionLabel(option) {
  if (typeof option === 'string' || typeof option === 'number') {
    return option
  }
  return option[props.optionLabel] ?? option.label ?? option.name ?? String(option)
}

function getOptionIndex(option) {
  return props.options.findIndex(opt => getOptionValue(opt) === getOptionValue(option))
}

function isOptionSelected(option) {
  return getOptionValue(option) === props.modelValue
}

function selectOption(option) {
  if (props.disabled) return
  
  const value = getOptionValue(option)
  const normalizedValue = value === '' ? null : value
  
  emit('update:modelValue', normalizedValue)
  emit('change', normalizedValue)
  
  // Обновляем нативный select для совместимости
  if (selectRef.value) {
    selectRef.value.value = value === null ? '' : value
  }
  
  isOpen.value = false
  hoveredIndex.value = null
}

function toggleDropdown() {
  if (props.disabled) return
  isOpen.value = !isOpen.value
  if (!isOpen.value) {
    hoveredIndex.value = null
  }
}

function handleContainerClick(event) {
  if (props.disabled) return
  // Предотвращаем закрытие при клике внутри контейнера
  event.stopPropagation()
}

function handleClickOutside() {
  if (isOpen.value) {
    isOpen.value = false
    hoveredIndex.value = null
  }
}

function handleChange(event) {
  const value = event.target.value
  const normalizedValue = value === '' ? null : value
  emit('update:modelValue', normalizedValue)
  emit('change', normalizedValue)
}

function handleFocus(event) {
  if (!props.disabled) {
    // Не открываем автоматически при фокусе
  }
  emit('focus', event)
}

function handleBlur(event) {
  emit('blur', event)
}

// Директива для клика вне элемента
const vClickOutside = {
  mounted(el, binding) {
    el.clickOutsideEvent = (event) => {
      if (!(el === event.target || el.contains(event.target))) {
        binding.value(event)
      }
    }
    document.addEventListener('click', el.clickOutsideEvent)
  },
  unmounted(el) {
    document.removeEventListener('click', el.clickOutsideEvent)
  }
}

onMounted(() => {
  if (selectRef.value) {
    selectRef.value.addEventListener('focus', handleFocus)
    selectRef.value.addEventListener('blur', handleBlur)
  }
})

onUnmounted(() => {
  if (selectRef.value) {
    selectRef.value.removeEventListener('focus', handleFocus)
    selectRef.value.removeEventListener('blur', handleBlur)
  }
})
</script>

<style lang="scss" scoped>
@import '../scss/components/select';
</style>
