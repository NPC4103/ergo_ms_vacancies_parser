import { ref } from 'vue'
import { vacanciesApi } from '../js/vacanciesApi'
import { useToast } from 'vue-toastification'

export function useParsing() {
  const toast = useToast()
  const parsing = ref(false)
  const taskId = ref(null)
  const taskStatus = ref(null)

  const parseByRoles = async (config = {}) => {
    parsing.value = true
    taskId.value = null
    taskStatus.value = null
    
    try {
      const response = await vacanciesApi.parseByRoles(config)
      taskId.value = response.data.task_id
      toast.success('Парсинг по ролям запущен')
      return response.data
    } catch (err) {
      toast.error('Ошибка при запуске парсинга по ролям')
      throw err
    } finally {
      parsing.value = false
    }
  }

  const parseByTechnologies = async (config = {}) => {
    parsing.value = true
    taskId.value = null
    taskStatus.value = null
    
    try {
      const response = await vacanciesApi.parseByTechnologies(config)
      taskId.value = response.data.task_id
      toast.success('Парсинг по технологиям запущен')
      return response.data
    } catch (err) {
      toast.error('Ошибка при запуске парсинга по технологиям')
      throw err
    } finally {
      parsing.value = false
    }
  }

  const checkTaskStatus = async (taskIdToCheck = null) => {
    const id = taskIdToCheck || taskId.value
    if (!id) return null
    
    try {
      const response = await vacanciesApi.getTaskStatus(id)
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
    parseByRoles,
    parseByTechnologies,
    checkTaskStatus,
    reset
  }
}

