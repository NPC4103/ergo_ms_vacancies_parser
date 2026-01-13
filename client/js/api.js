/**
 * API клиент для модуля vacancies_parser
 */

import { apiClient } from '@/js/api/manager'
import { endpoints } from './endpoints'

/**
 * API для работы с задачами парсинга
 */
export const tasksApi = {
  /**
   * Получить список задач
   * @param {Object} params - Параметры фильтрации и пагинации
   * @returns {Promise}
   */
  async list(params = {}) {
    return apiClient.get(endpoints.tasks.list, { params })
  },
  
  /**
   * Получить детали задачи
   * @param {Number} id - ID задачи
   * @returns {Promise}
   */
  async get(id) {
    return apiClient.get(endpoints.tasks.detail(id))
  },
  
  /**
   * Создать новую задачу парсинга
   * @param {Object} data - Данные задачи
   * @returns {Promise}
   */
  async create(data) {
    return apiClient.post(endpoints.tasks.create, data)
  },
  
  /**
   * Обновить задачу
   * @param {Number} id - ID задачи
   * @param {Object} data - Обновленные данные
   * @returns {Promise}
   */
  async update(id, data) {
    return apiClient.patch(endpoints.tasks.update(id), data)
  },
  
  /**
   * Удалить задачу
   * @param {Number} id - ID задачи
   * @returns {Promise}
   */
  async delete(id) {
    return apiClient.delete(endpoints.tasks.delete(id))
  },
  
  /**
   * Получить прогресс выполнения задачи
   * @param {Number} id - ID задачи
   * @returns {Promise}
   */
  async getProgress(id) {
    return apiClient.get(endpoints.tasks.progress(id))
  },
  
  /**
   * Приостановить задачу
   * @param {Number} id - ID задачи
   * @returns {Promise}
   */
  async pause(id) {
    return apiClient.post(endpoints.tasks.pause(id))
  },
  
  /**
   * Возобновить задачу
   * @param {Number} id - ID задачи
   * @returns {Promise}
   */
  async resume(id) {
    return apiClient.post(endpoints.tasks.resume(id))
  },
  
  /**
   * Остановить задачу
   * @param {Number} id - ID задачи
   * @returns {Promise}
   */
  async stop(id) {
    return apiClient.post(endpoints.tasks.stop(id))
  },
  
  /**
   * Получить элементы задачи
   * @param {Number} id - ID задачи
   * @param {Object} params - Параметры фильтрации
   * @returns {Promise}
   */
  async getItems(id, params = {}) {
    return apiClient.get(endpoints.tasks.items(id), { params })
  },
  
  /**
   * Получить статистику задачи
   * @param {Number} id - ID задачи
   * @returns {Promise}
   */
  async getStatistics(id) {
    return apiClient.get(endpoints.tasks.statistics(id))
  },
  
  /**
   * Получить доступные источники и режимы парсинга
   * @returns {Promise}
   */
  async getSources() {
    return apiClient.get(endpoints.tasks.sources)
  }
}

/**
 * API для работы с вакансиями
 */
export const vacanciesApi = {
  /**
   * Получить список вакансий
   * @param {Object} params - Параметры фильтрации и пагинации
   * @returns {Promise}
   */
  async list(params = {}) {
    return apiClient.get(endpoints.vacancies.list, { params })
  },
  
  /**
   * Получить детали вакансии
   * @param {Number} id - ID вакансии
   * @returns {Promise}
   */
  async get(id) {
    return apiClient.get(endpoints.vacancies.detail(id))
  },
  
  /**
   * Получить историю изменений вакансии
   * @param {Number} id - ID вакансии
   * @returns {Promise}
   */
  async getChanges(id) {
    return apiClient.get(endpoints.vacancies.changes(id))
  }
}

/**
 * API для работы со статистикой
 */
export const statisticsApi = {
  /**
   * Получить список статистик
   * @param {Object} params - Параметры фильтрации
   * @returns {Promise}
   */
  async list(params = {}) {
    return apiClient.get(endpoints.statistics.list, { params })
  },
  
  /**
   * Получить детали статистики
   * @param {Number} id - ID статистики
   * @returns {Promise}
   */
  async get(id) {
    return apiClient.get(endpoints.statistics.detail(id))
  }
}
