import { ref } from 'vue'
import { vacanciesApi } from '../js/vacanciesApi'
import { useToast } from 'vue-toastification'

export function useParsing() {
  const toast = useToast()
  const parsing = ref(false)
  const taskId = ref(null)
  const taskStatus = ref(null)

  const _wrapParsing = async (label, fn) => {
    parsing.value = true
    taskId.value = null
    taskStatus.value = null

    try {
      const response = await fn()
      const data = response.data || response
      taskId.value = data.task_id || data.id
      toast.success(`${label} запущен`)
      return data
    } catch (err) {
      toast.error(`Ошибка при запуске: ${label}`)
      throw err
    } finally {
      parsing.value = false
    }
  }

  const parseByText = (source, config = {}) =>
    _wrapParsing('Парсинг по тексту', () => vacanciesApi.parseByText(source, config))

  const parseByRoles = (source, config = {}) =>
    _wrapParsing('Парсинг по ролям', () => vacanciesApi.parseByRoles(source, config))

  const parseByTechnologies = (source, config = {}) =>
    _wrapParsing('Парсинг по технологиям', () => vacanciesApi.parseByTechnologies(source, config))

  const parseByCatalogues = (source, config = {}) =>
    _wrapParsing('Парсинг по каталогам', () => vacanciesApi.parseByCatalogues(source, config))

  const parseAll = (source, config = {}) =>
    _wrapParsing('Универсальный парсинг', () => vacanciesApi.parseAll(source, config))

  const checkTaskStatus = async (source, taskIdToCheck = null) => {
    const id = taskIdToCheck || taskId.value
    if (!id) return null

    try {
      const response = await vacanciesApi.getTaskStatus(source, id)
      taskStatus.value = response.data
      return response.data
    } catch (err) {
      toast.error('Ошибка при проверке статуса задачи')
      throw err
    }
  }

  const reset = () => {
    parsing.value = false
    taskId.value = null
    taskStatus.value = null
  }

  return {
    parsing,
    taskId,
    taskStatus,
    parseByText,
    parseByRoles,
    parseByTechnologies,
    parseByCatalogues,
    parseAll,
    checkTaskStatus,
    reset
  }
}
