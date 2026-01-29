"""
Утилиты для worker задач парсинга.

Используется для:
- Обработки отдельных TaskItems через scheduler
- Claiming items
- Парсинга и сохранения результатов
"""

import logging
from typing import List, Optional

from .base import BaseParsingTaskMixin

logger = logging.getLogger('celery.module.vacancies_parser.tasks.worker')


def validate_worker_params(**kwargs) -> bool:
    """
    Валидация параметров worker задачи.
    
    Args:
        **kwargs: Параметры задачи
    
    Returns:
        bool: True если параметры валидны
    
    Raises:
        ValueError: При невалидных параметрах
    """
    if 'task_id' not in kwargs:
        raise ValueError("Отсутствует обязательный параметр: task_id")
    
    if 'worker_id' not in kwargs:
        raise ValueError("Отсутствует обязательный параметр: worker_id")
    
    return True


def claim_items_for_worker(task_id: int, worker_id: str, limit: int = 10) -> List:
    """
    Получение items для обработки через scheduler.
    
    Args:
        task_id: ID ParsingTask
        worker_id: ID worker'а
        limit: Максимальное количество items
    
    Returns:
        List: Список TaskItems для обработки
    """
    from ..scheduler import default_scheduler
    
    return default_scheduler.claim_items_for_worker(
        task_id=task_id,
        worker_id=worker_id,
        limit=limit
    )


def process_item(item, parser, task, error_handler):
    """
    Обработка одного item.
    
    Args:
        item: TaskItem для обработки
        parser: Парсер для извлечения данных
        task: ParsingTask
        error_handler: Обработчик ошибок
    
    Returns:
        dict: Результат обработки
    """
    from ..normalized_models import NormalizedVacancy
    
    # Парсинг item
    vacancy_data = parser.parse_item(item.source_item_id, item.url)
    
    # Удаляем поля lookup из defaults
    defaults_data = {k: v for k, v in vacancy_data.items() 
                    if k not in ('source', 'source_id')}
    defaults_data['task_item'] = item
    
    # Сохранение в NormalizedVacancy
    vacancy, created = NormalizedVacancy.objects.update_or_create(
        source=task.source,
        source_id=item.source_item_id,
        defaults=defaults_data
    )
    
    # Отметка item как completed
    item.mark_completed(
        result_vacancy_id=vacancy.id,
        extracted_data=vacancy_data
    )
    
    # Обновление счетчика задачи
    task.increment_completed()
    
    return {
        'success': True,
        'vacancy_id': vacancy.id,
        'created': created
    }


def handle_item_error(item, exception, task, error_handler):
    """
    Обработка ошибки при обработке item.
    
    Args:
        item: TaskItem с ошибкой
        exception: Исключение
        task: ParsingTask
        error_handler: Обработчик ошибок
    """
    from ..parsers.base import BlockedError, NetworkError, ValidationError
    
    error_type = error_handler.classify_error(exception)
    
    # Обработка ошибок по типу
    if error_type.value == 'blocked' or isinstance(exception, BlockedError):
        item.mark_blocked(str(exception))
    elif error_type.value == 'network' or isinstance(exception, NetworkError):
        item.mark_failed(str(exception), 'network')
    elif error_type.value == 'validation' or isinstance(exception, ValidationError):
        item.mark_failed(str(exception), 'validation')
    else:
        item.mark_failed(str(exception), 'unknown')
    
    # Обновление счетчика failed
    task.increment_failed()
    
    # Логирование
    error_handler.handle_error(exception, {
        'task_id': task.id,
        'item_id': item.id,
        'source_item_id': item.source_item_id,
    })


class WorkerTaskMixin(BaseParsingTaskMixin):
    """
    Mixin для worker задач парсинга.
    
    Предоставляет общую логику для:
    - Claiming items через scheduler
    - Обработки items
    - Обработки ошибок items
    - Обновления прогресса задачи
    """
    
    def validate_params(self, **kwargs) -> bool:
        """Валидация параметров worker задачи"""
        return validate_worker_params(**kwargs)
    
    def claim_items(self, task_id: int, worker_id: str, limit: int = 10) -> List:
        """Получение items для обработки через scheduler"""
        return claim_items_for_worker(task_id, worker_id, limit)
    
    def process_item(self, item, parser, task):
        """Обработка одного item"""
        error_handler = self.get_error_handler()
        return process_item(item, parser, task, error_handler)
    
    def handle_item_error(self, item, exception, task):
        """Обработка ошибки при обработке item"""
        error_handler = self.get_error_handler()
        return handle_item_error(item, exception, task, error_handler)
