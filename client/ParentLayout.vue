<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Briefcase, BarChart3, List, Settings } from 'lucide-vue-next'

import NavigationButtons from '@/components/NavigationButtons.vue'

const route = useRoute()
const router = useRouter()

// Навигационные кнопки
const navigationButtons = computed(() => {
  return [
    { 
      icon: BarChart3, 
      title: 'Панель управления', 
      link: 'VacanciesDashboard'
    },
    { 
      icon: List, 
      title: 'Список вакансий', 
      link: 'VacanciesList'
    },
    { 
      icon: Settings, 
      title: 'Управление парсингом', 
      link: 'ParsingControl'
    }
  ]
})
</script>

<template>
  <div class="vacancies-parser-layout">
    <header class="module-header">
      <div class="header-content">
        <div class="header-icon">
          <Briefcase :size="32" />
        </div>
        <div class="header-text">
          <h1 class="header-title">Парсер вакансий</h1>
          <p class="header-subtitle">Анализ и мониторинг вакансий с HeadHunter</p>
        </div>
      </div>
    </header>

    <nav class="module-nav">
      <NavigationButtons :data="navigationButtons" />
    </nav>

    <main class="module-content">
      <RouterView />
    </main>
  </div>
</template>

<style lang="scss" scoped>
.vacancies-parser-layout {
  .module-header {
    margin-bottom: 2rem;
    padding: 2rem 0 1.5rem;
    border-bottom: 1px solid var(--bs-border-color, #e9ecef);
    
    .header-content {
      display: flex;
      align-items: center;
      gap: 1rem;
    }
    
    .header-icon {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 56px;
      height: 56px;
      border-radius: 12px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      flex-shrink: 0;
    }
    
    .header-text {
      flex: 1;
    }
    
    .header-title {
      font-size: 1.75rem;
      font-weight: 600;
      margin: 0 0 0.25rem 0;
      color: var(--bs-body-color, #212529);
      letter-spacing: -0.02em;
    }
    
    .header-subtitle {
      font-size: 0.9375rem;
      color: var(--bs-secondary-color, #6c757d);
      margin: 0;
      font-weight: 400;
    }
  }
  
  .module-nav {
    margin-bottom: 2rem;
  }
  
  .module-content {
    min-height: 400px;
  }
}

@media (max-width: 768px) {
  .vacancies-parser-layout {
    .module-header {
      padding: 1.5rem 0 1rem;
      
      .header-icon {
        width: 48px;
        height: 48px;
      }
      
      .header-title {
        font-size: 1.5rem;
      }
      
      .header-subtitle {
        font-size: 0.875rem;
      }
    }
  }
}
</style>
