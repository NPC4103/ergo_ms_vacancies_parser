/**
 * Маршруты модуля vacancies_parser
 */

export default {
  // Главная страница модуля (список задач)
  VacanciesParserMain: {
    path: '/vacancies-parser',
    component: '@/modules/vacancies_parser/client/components/TasksList.vue',
    meta: {
      title: 'Парсинг вакансий',
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
  }
}
