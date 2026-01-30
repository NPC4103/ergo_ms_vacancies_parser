<template>
  <div class="vp-step-indicator">
    <div 
      v-for="(step, index) in steps" 
      :key="index"
      class="vp-step-item"
      :class="{
        'vp-step-active': currentStep === index,
        'vp-step-completed': currentStep > index,
        'vp-step-disabled': currentStep < index
      }"
    >
      <div class="vp-step-number">
        <Check v-if="currentStep > index" :size="16" />
        <span v-else>{{ index + 1 }}</span>
      </div>
      <div class="vp-step-label">{{ step.label }}</div>
    </div>
  </div>
</template>

<script setup>
import { Check } from 'lucide-vue-next'

defineProps({
  steps: {
    type: Array,
    required: true
  },
  currentStep: {
    type: Number,
    required: true
  }
})
</script>

<style lang="scss" scoped>
@import '../../scss/components/step-indicator';
</style>
