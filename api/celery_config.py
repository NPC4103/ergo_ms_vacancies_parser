"""
Celery конфигурация для модуля vacancies_parser.

Определяет:
- Маршруты задач (task routes)
- Настройки очередей (task queues)
- Таймауты и лимиты (task annotations)
"""

from kombu import Queue, Exchange
from src.core.utils.celery import CeleryModuleConfig


class VacanciesParserCeleryConfig(CeleryModuleConfig):
    """Конфигурация Celery для модуля vacancies_parser"""
    
    def get_task_routes(self):
        """
        Маршруты задач модуля.
        
        Все задачи парсинга направляются в очередь 'vacancies_parser'.
        """
        return {
            'vacancies_parser.tasks.*': {'queue': 'vacancies_parser'},
        }
    
    def get_task_queues(self):
        """
        Настройки очереди модуля.
        
        Использует отдельную очередь 'vacancies_parser' для изоляции от других модулей.
        """
        return [
            Queue(
                'vacancies_parser',
                Exchange('vacancies_parser'),
                routing_key='vacancies_parser',
                queue_arguments={'x-max-priority': 10}  # Поддержка приоритетов
            )
        ]
    
    def get_task_annotations(self):
        """
        Таймауты и лимиты для задач модуля.
        
        Настройки оптимизированы для парсинга ~40k items/hour с параллелизмом ~10.
        """
        return {
            # Координирующие задачи
            'vacancies_parser.tasks.create_parsing_task': {
                'time_limit': 600,  # 10 минут (discovery может быть долгим)
                'soft_time_limit': 540,
                'rate_limit': '10/m',  # Лимит создания задач
            },
            'vacancies_parser.tasks.coordinate_parsing_task': {
                'time_limit': 7200,  # 2 часа (координация может быть долгой)
                'soft_time_limit': 7000,
                'rate_limit': None,  # Без лимита для координаторов
            },
            'vacancies_parser.tasks.finalize_parsing_task': {
                'time_limit': 300,  # 5 минут
                'soft_time_limit': 270,
                'rate_limit': None,
            },
            
            # Worker задачи
            'vacancies_parser.tasks.parse_items_worker': {
                'time_limit': 3600,  # 1 час (worker может обрабатывать много items)
                'soft_time_limit': 3540,
                'rate_limit': None,  # Без лимита для workers
                'max_retries': 0,  # Workers не делают retry
            },
            
            # Периодические задачи
            'vacancies_parser.tasks.release_expired_leases': {
                'time_limit': 120,  # 2 минуты
                'soft_time_limit': 110,
                'rate_limit': '1/m',  # Раз в минуту максимум
            },
            'vacancies_parser.tasks.monitor_tasks_progress': {
                'time_limit': 300,  # 5 минут
                'soft_time_limit': 270,
                'rate_limit': '1/m',
            },
            
            # Управляющие задачи
            'vacancies_parser.tasks.pause_task': {
                'time_limit': 60,
                'soft_time_limit': 50,
            },
            'vacancies_parser.tasks.resume_task': {
                'time_limit': 60,
                'soft_time_limit': 50,
            },
            'vacancies_parser.tasks.stop_task': {
                'time_limit': 120,
                'soft_time_limit': 110,
            },
        }


# Экземпляр конфигурации (автоматически обнаруживается системой)
celery_config = VacanciesParserCeleryConfig()
