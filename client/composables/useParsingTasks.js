/**
 * Composable для управления задачами парсинга
 */

import { ref, computed } from 'vue'
import { tasksApi } from '../js/api'
import { useToast } from 'vue-toastification'

export function useParsingTasks() {
  const toast = useToast()
  
  // Состояние
  const tasks = ref([])
  const currentTask = ref(null)
  const taskProgress = ref(null)
  const sources = ref([])
  const loading = ref(false)
  const error = ref(null)
  
  // Pagination
  const pagination = ref({
    page: 1,
    pageSize: 20,
    total: 0
  })
  
  // Filters
  const filters = ref({
    source: null,
    parsing_mode: null,
    status: null,
    search: ''
  })
  
  /**
   * Загрузить список задач
   */
  async function loadTasks(params = {}) {
    loading.value = true
    error.value = null
    
    try {
      const response = await tasksApi.list({
        page: pagination.value.page,
        page_size: pagination.value.pageSize,
        source: filters.value.source,
        parsing_mode: filters.value.parsing_mode,
        status: filters.value.status,
        search: filters.value.search,
        ...params
      })
      
      console.log('Tasks API response:', response) // DEBUG
      
      // handleResponse возвращает { data: ..., success: ..., message: ... }
      const data = response.data || response
      tasks.value = data.results || []
      pagination.value.total = data.count || 0
      
      console.log('Loaded tasks:', tasks.value.length) // DEBUG
      
      return response
    } catch (err) {
      console.error('Error loading tasks:', err) // DEBUG
      error.value = err.message || 'Ошибка загрузки задач'
      toast.error(error.value)
      throw err
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Загрузить детали задачи
   */
  async function loadTask(id) {
    loading.value = true
    error.value = null
    
    try {
      const response = await tasksApi.get(id)
      // handleResponse возвращает { data: ..., success: ..., message: ... }
      const data = response.data || response
      currentTask.value = data
      return data
    } catch (err) {
      error.value = err.message || 'Ошибка загрузки задачи'
      toast.error(error.value)
      throw err
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Создать новую задачу
   */
  async function createTask(data) {
    loading.value = true
    error.value = null
    
    try {
      const response = await tasksApi.create(data)
      toast.success('Задача создана и запущена')
      await loadTasks() // Перезагрузить список
      // handleResponse возвращает { data: ..., success: ..., message: ... }
      return response.data || response
    } catch (err) {
      error.value = err.message || 'Ошибка создания задачи'
      toast.error(error.value)
      throw err
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Удалить задачу
   */
  async function deleteTask(id) {
    loading.value = true
    error.value = null
    
    try {
      await tasksApi.delete(id)
      toast.success('Задача удалена')
      await loadTasks() // Перезагрузить список
    } catch (err) {
      error.value = err.message || 'Ошибка удаления задачи'
      toast.error(error.value)
      throw err
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Получить прогресс выполнения задачи
   */
  async function loadTaskProgress(id) {
    try {
      const response = await tasksApi.getProgress(id)
      // handleResponse возвращает { data: ..., success: ..., message: ... }
      const data = response.data || response
      taskProgress.value = data
      return data
    } catch (err) {
      console.error('Ошибка загрузки прогресса:', err)
      throw err
    }
  }
  
  /**
   * Приостановить задачу
   */
  async function pauseTask(id) {
    loading.value = true
    error.value = null
    
    try {
      await tasksApi.pause(id)
      toast.info('Задача приостанавливается...')
      
      // Обновить задачу после небольшой задержки
      setTimeout(async () => {
        await loadTask(id)
        await loadTasks()
      }, 1000)
    } catch (err) {
      error.value = err.message || 'Ошибка приостановки задачи'
      toast.error(error.value)
      throw err
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Возобновить задачу
   */
  async function resumeTask(id) {
    loading.value = true
    error.value = null
    
    try {
      await tasksApi.resume(id)
      toast.info('Задача возобновляется...')
      
      // Обновить задачу после небольшой задержки
      setTimeout(async () => {
        await loadTask(id)
        await loadTasks()
      }, 1000)
    } catch (err) {
      error.value = err.message || 'Ошибка возобновления задачи'
      toast.error(error.value)
      throw err
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Остановить задачу
   */
  async function stopTask(id) {
    loading.value = true
    error.value = null
    
    try {
      await tasksApi.stop(id)
      toast.warning('Задача останавливается...')
      
      // Обновить задачу после небольшой задержки
      setTimeout(async () => {
        await loadTask(id)
        await loadTasks()
      }, 1000)
    } catch (err) {
      error.value = err.message || 'Ошибка остановки задачи'
      toast.error(error.value)
      throw err
    } finally {
      loading.value = false
    }
  }
  
  /**
   * Загрузить доступные источники и режимы парсинга
   */
  async function loadSources() {
    try {
      const response = await tasksApi.getSources()
      // handleResponse возвращает { data: ..., success: ..., message: ... }
      const data = response.data || response
      sources.value = data.sources || []
      return data
    } catch (err) {
      console.error('Ошибка загрузки источников:', err)
      throw err
    }
  }
  
  /**
   * Установить фильтры
   */
  function setFilters(newFilters) {
    filters.value = { ...filters.value, ...newFilters }
    pagination.value.page = 1 // Сброс на первую страницу
    loadTasks()
  }
  
  /**
   * Сбросить фильтры
   */
  function resetFilters() {
    filters.value = {
      source: null,
      parsing_mode: null,
      status: null,
      search: ''
    }
    pagination.value.page = 1
    loadTasks()
  }
  
  /**
   * Изменить страницу
   */
  function changePage(page) {
    pagination.value.page = page
    loadTasks()
  }
  
  // Computed properties
  const hasTasks = computed(() => tasks.value.length > 0)
  const activeTasks = computed(() => tasks.value.filter(t => t.is_active))
  const finishedTasks = computed(() => tasks.value.filter(t => t.is_finished))
  
  return {
    // State
    tasks,
    currentTask,
    taskProgress,
    sources,
    loading,
    error,
    pagination,
    filters,
    
    // Computed
    hasTasks,
    activeTasks,
    finishedTasks,
    
    // Methods
    loadTasks,
    loadTask,
    createTask,
    deleteTask,
    loadTaskProgress,
    pauseTask,
    resumeTask,
    stopTask,
    loadSources,
    setFilters,
    resetFilters,
    changePage
  }
}
