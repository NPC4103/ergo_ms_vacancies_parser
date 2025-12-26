import { apiClient } from '@/js/api/manager'
import { endpoints } from './endpoints'

export const vacanciesApi = {
  // Получение списка вакансий
  async getVacancies(params = {}) {
    return await apiClient.get(endpoints.vacancies.list, { params })
  },

  // Получение детальной информации о вакансии
  async getVacancy(id) {
    return await apiClient.get(endpoints.vacancies.detail(id))
  },

  // Получение статистики
  async getStats(params = {}) {
    return await apiClient.get(endpoints.vacancies.stats, { params })
  },

  // Получение версий вакансии
  async getVersions(id) {
    return await apiClient.get(endpoints.vacancies.versions(id))
  },

  // Получение деталей версии
  async getVersionDetail(id, versionNumber) {
    return await apiClient.get(endpoints.vacancies.versionDetail(id), {
      params: { version: versionNumber }
    })
  },

  // Получение истории изменений
  async getChanges(id, versionNumber = null) {
    const params = versionNumber ? { version: versionNumber } : {}
    return await apiClient.get(endpoints.vacancies.changes(id), { params })
  },

  // Парсинг одной вакансии
  async parseSingle(vacancyId, forceUpdate = false) {
    return await apiClient.post(endpoints.vacancies.parseSingle, {
      vacancy_id: vacancyId,
      force_update: forceUpdate
    })
  },

  // Получение статуса задачи
  async getTaskStatus(taskId) {
    return await apiClient.get(endpoints.vacancies.taskStatus, {
      params: { task_id: taskId }
    })
  },

  // Парсинг по профессиональным ролям
  async parseByRoles(config = {}) {
    return await apiClient.post(endpoints.parsing.parseByRoles, config)
  },

  // Парсинг по технологиям
  async parseByTechnologies(config = {}) {
    return await apiClient.post(endpoints.parsing.parseByTechnologies, config)
  }
}

