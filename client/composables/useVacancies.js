import { ref, computed } from 'vue'
import { vacanciesApi } from '../js/vacanciesApi'
import { useToast } from 'vue-toastification'

export function useVacancies() {
  const toast = useToast()
  const vacancies = ref([])
  const loading = ref(false)
  const error = ref(null)
  const pagination = ref({
    count: 0,
    next: null,
    previous: null,
    page: 1,
    pageSize: 20
  })

  const loadVacancies = async (params = {}) => {
    loading.value = true
    error.value = null
    
    try {
      const response = await vacanciesApi.getVacancies({
        page: pagination.value.page,
        page_size: pagination.value.pageSize,
        ...params
      })
      
      vacancies.value = response.data.results || response.data
      
      if (response.data.count !== undefined) {
        pagination.value = {
          count: response.data.count,
          next: response.data.next,
          previous: response.data.previous,
          page: params.page || pagination.value.page,
          pageSize: params.page_size || pagination.value.pageSize
        }
      }
      
      return response.data
    } catch (err) {
      error.value = err
      toast.error('Ошибка при загрузке вакансий')
      throw err
    } finally {
      loading.value = false
    }
  }

  const loadVacancy = async (id) => {
    loading.value = true
    error.value = null
    
    try {
      const response = await vacanciesApi.getVacancy(id)
      return response.data
    } catch (err) {
      error.value = err
      toast.error('Ошибка при загрузке вакансии')
      throw err
    } finally {
      loading.value = false
    }
  }

  const loadStats = async (params = {}) => {
    loading.value = true
    error.value = null
    
    try {
      const response = await vacanciesApi.getStats(params)
      return response.data
    } catch (err) {
      error.value = err
      toast.error('Ошибка при загрузке статистики')
      throw err
    } finally {
      loading.value = false
    }
  }

  const parseSingle = async (vacancyId, forceUpdate = false) => {
    try {
      const response = await vacanciesApi.parseSingle(vacancyId, forceUpdate)
      toast.success('Парсинг вакансии запущен')
      return response.data
    } catch (err) {
      toast.error('Ошибка при запуске парсинга')
      throw err
    }
  }

  const getTaskStatus = async (taskId) => {
    try {
      const response = await vacanciesApi.getTaskStatus(taskId)
      return response.data
    } catch (err) {
      toast.error('Ошибка при получении статуса задачи')
      throw err
    }
  }

  const hasNextPage = computed(() => !!pagination.value.next)
  const hasPreviousPage = computed(() => !!pagination.value.previous)
  const totalPages = computed(() => 
    Math.ceil(pagination.value.count / pagination.value.pageSize)
  )

  return {
    vacancies,
    loading,
    error,
    pagination,
    loadVacancies,
    loadVacancy,
    loadStats,
    parseSingle,
    getTaskStatus,
    hasNextPage,
    hasPreviousPage,
    totalPages
  }
}

