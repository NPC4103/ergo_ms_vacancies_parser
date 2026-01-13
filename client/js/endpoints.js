/**
 * API endpoints для модуля vacancies_parser
 */

export const endpoints = {
  // Задачи парсинга
  tasks: {
    list: 'vacancies_parser/tasks/',
    detail: id => `vacancies_parser/tasks/${id}/`,
    create: 'vacancies_parser/tasks/',
    update: id => `vacancies_parser/tasks/${id}/`,
    delete: id => `vacancies_parser/tasks/${id}/`,
    progress: id => `vacancies_parser/tasks/${id}/progress/`,
    pause: id => `vacancies_parser/tasks/${id}/pause/`,
    resume: id => `vacancies_parser/tasks/${id}/resume/`,
    stop: id => `vacancies_parser/tasks/${id}/stop/`,
    items: id => `vacancies_parser/tasks/${id}/items/`,
    statistics: id => `vacancies_parser/tasks/${id}/statistics/`,
    sources: 'vacancies_parser/tasks/sources/'
  },
  
  // Элементы задач
  items: {
    list: 'vacancies_parser/items/',
    detail: id => `vacancies_parser/items/${id}/`
  },
  
  // Вакансии
  vacancies: {
    list: 'vacancies_parser/vacancies/',
    detail: id => `vacancies_parser/vacancies/${id}/`,
    changes: id => `vacancies_parser/vacancies/${id}/changes/`
  },
  
  // Статистика
  statistics: {
    list: 'vacancies_parser/statistics/',
    detail: id => `vacancies_parser/statistics/${id}/`
  }
}
