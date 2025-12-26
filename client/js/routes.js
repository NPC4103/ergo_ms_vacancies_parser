export default {
  "VacanciesParser": {
    "path": "/vacancies-parser",
    "component": "@/modules/vacancies_parser/client/ParentLayout.vue",
    "redirect": "VacanciesDashboard",
    "meta": {
      "requiresAuth": true
    }
  },
  "VacanciesDashboard": {
    "path": "/vacancies-parser/dashboard",
    "component": "@/modules/vacancies_parser/client/Dashboard/DashboardView.vue",
    "meta": {
      "title": "Панель управления парсером",
      "requiresAuth": true
    }
  },
  "VacanciesList": {
    "path": "/vacancies-parser/vacancies",
    "component": "@/modules/vacancies_parser/client/VacanciesList/VacanciesListView.vue",
    "meta": {
      "title": "Список вакансий",
      "requiresAuth": true
    }
  },
  "VacancyDetail": {
    "path": "/vacancies-parser/vacancies/:id",
    "component": "@/modules/vacancies_parser/client/VacancyDetail/VacancyDetailView.vue",
    "meta": {
      "title": "Детали вакансии",
      "requiresAuth": true
    }
  },
  "ParsingControl": {
    "path": "/vacancies-parser/parsing",
    "component": "@/modules/vacancies_parser/client/ParsingControl/ParsingControlView.vue",
    "meta": {
      "title": "Управление парсингом",
      "requiresAuth": true
    }
  },
  "VacancyStats": {
    "path": "/vacancies-parser/stats",
    "component": "@/modules/vacancies_parser/client/Stats/VacancyStatsView.vue",
    "meta": {
      "title": "Статистика вакансий",
      "requiresAuth": true
    }
  }
}

