/**
 * Маршруты модуля vacancies_parser
 */

export default {
  // Главная страница модуля (ParentLayout с редиректом)
  VacanciesParserMain: {
    path: '/vacancies-parser',
    component: '@/modules/vacancies_parser/client/ParentLayout.vue',
    redirect: 'VacanciesDashboard',
    meta: {
      title: 'Парсинг вакансий',
      requiresAuth: true
    }
  },
  
  // Дашборд
  VacanciesDashboard: {
    path: '/vacancies-parser/dashboard',
    component: '@/modules/vacancies_parser/client/Dashboard/DashboardView.vue',
    meta: {
      title: 'Панель управления',
      requiresAuth: true
    }
  },
  
  // Список задач парсинга
  VacanciesParser: {
    path: '/vacancies-parser/tasks',
    component: '@/modules/vacancies_parser/client/components/TasksList.vue',
    meta: {
      title: 'Задачи парсинга',
      requiresAuth: true
    }
  },
  
  // Детальный просмотр задачи
  VacanciesParserTaskDetail: {
    path: '/vacancies-parser/tasks/:id',
    component: '@/modules/vacancies_parser/client/components/TaskDetailView.vue',
    meta: {
      title: 'Детали задачи парсинга',
      requiresAuth: true
    }
  },
  
  // Результаты парсинга (список вакансий)
  VacanciesParserResults: {
    path: '/vacancies-parser/results',
    component: '@/modules/vacancies_parser/client/components/VacanciesResults.vue',
    meta: {
      title: 'Результаты парсинга',
      requiresAuth: true
    }
  },

  // Список вакансий с расширенными фильтрами
  VacanciesList: {
    path: '/vacancies-parser/vacancies',
    component: '@/modules/vacancies_parser/client/VacanciesList/VacanciesListView.vue',
    meta: {
      title: 'Вакансии',
      requiresAuth: true
    }
  },

  // Детальный просмотр вакансии
  VacancyDetail: {
    path: '/vacancies-parser/vacancies/:id',
    component: '@/modules/vacancies_parser/client/VacancyDetail/VacancyDetailView.vue',
    meta: {
      title: 'Детали вакансии',
      requiresAuth: true
    }
  },

  // Управление парсингом
  ParsingControl: {
    path: '/vacancies-parser/control',
    component: '@/modules/vacancies_parser/client/ParsingControl/ParsingControlView.vue',
    meta: {
      title: 'Управление парсингом',
      requiresAuth: true
    }
  }
}
