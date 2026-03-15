import { apiClient } from '@/js/api/manager'
import { endpoints, getSourceEndpoints } from './endpoints'

export const vacanciesApi = {
  // Получение списка вакансий
  async getVacancies(params = {}) {
    return await apiClient.get(endpoints.vacancies.list, { params })
  },

  // Получение детальной информации о вакансии
  async getVacancy(id) {
    return await apiClient.get(endpoints.vacancies.detail(id))
  },

  async getChanges(id, versionNumber = null) {
    const params = versionNumber ? { version: versionNumber } : {}
    return await apiClient.get(endpoints.vacancies.changes(id), { params })
  },

  // одинаковая структура для всех парсеров

  async getVersions(source, id) {
    const ep = getSourceEndpoints(source)
    return await apiClient.get(ep.vacancies.versions(id))
  },

  async getVersionDetail(source, id, versionNumber) {
    const ep = getSourceEndpoints(source)
    return await apiClient.get(ep.vacancies.versionDetail(id), {
      params: { version: versionNumber }
    })
  },

  async getStats(source, params = {}) {
    const ep = getSourceEndpoints(source)
    return await apiClient.get(ep.vacancies.stats, { params })
  },

  async getTaskStatus(source, taskId) {
    const ep = getSourceEndpoints(source)
    return await apiClient.get(ep.vacancies.taskStatus, {
      params: { task_id: taskId }
    })
  },

  async parseSingle(source, data) {
    const ep = getSourceEndpoints(source)
    return await apiClient.post(ep.vacancies.parseSingle, data)
  },

  async getDetails(source, data) {
    const ep = getSourceEndpoints(source)
    return await apiClient.post(ep.parsing.getDetails, data)
  },

  // ====== Source-specific parsing control ======

  async parseByText(source, data) {
    const ep = getSourceEndpoints(source)
    return await apiClient.post(ep.parsing.parseByText, data)
  },

  async parseAll(source, data) {
    const ep = getSourceEndpoints(source)
    return await apiClient.post(ep.parsing.parseAll, data)
  },

  async parseByConfig(source, data) {
    const ep = getSourceEndpoints(source)
    return await apiClient.post(ep.parsing.parseByConfig, data)
  },

  async parseByRoles(source, data) {
    const ep = getSourceEndpoints(source)
    return await apiClient.post(ep.parsing.parseByRoles, data)
  },

  async parseByTechnologies(source, data) {
    const ep = getSourceEndpoints(source)
    return await apiClient.post(ep.parsing.parseByTechnologies, data)
  },

  async parseByCatalogues(source, data) {
    const ep = getSourceEndpoints(source)
    return await apiClient.post(ep.parsing.parseByCatalogues, data)
  },

  async getCatalogues(source) {
    const ep = getSourceEndpoints(source)
    return await apiClient.get(ep.parsing.catalogues)
  }
}
