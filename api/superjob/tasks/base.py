"""
Базовые задачи парсинга SuperJob: текстовый поиск, универсальный, конфиг, детали.
"""

import logging
from typing import Dict, Any, Optional

from celery import shared_task

from ..parsers.discovery import (
    parse_vacancies_by_text,
    parse_all_vacancies,
    get_vacancy_details,
)
from .utils import run_task_with_error_handling

logger = logging.getLogger('modules.vacancies_parser.superjob')

TASK_PREFIX = 'modules.vacancies_parser.api.superjob.tasks'


@shared_task(
    name=f'{TASK_PREFIX}.parse_superjob_vacancies_task',
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=3300,
    time_limit=3600,
)
def parse_superjob_vacancies_task(
    self,
    text: str = None,
    town: str = None,
    experience=None,
    employment=None,
    schedule=None,
    max_pages: int = 5,
    delay: float = 1.0,
    api_key: str = None,
) -> Dict[str, Any]:
    """Парсинг вакансий SuperJob по текстовому запросу."""

    def body():
        logger.info("Парсинг SuperJob по запросу: '%s'", text)
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': max_pages, 'status': f'Парсинг: {text}'},
        )
        result = parse_vacancies_by_text(
            text=text, town=town, experience=experience,
            employment=employment, schedule=schedule,
            max_pages=max_pages, delay=delay, api_key=api_key,
        )
        return {
            'status': 'SUCCESS',
            'result': result,
            'message': (
                f'Парсинг завершен. Найдено: {result["total_vacancies"]}, '
                f'Сохранено: {result["saved_vacancies"]}, '
                f'Обновлено: {result["updated_vacancies"]}'
            ),
        }

    return run_task_with_error_handling(self, body, task_logger=logger)


@shared_task(
    name=f'{TASK_PREFIX}.parse_all_superjob_vacancies_task',
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=6900,
    time_limit=7200,
)
def parse_all_superjob_vacancies_task(
    self,
    max_pages_per_query: int = 3,
    delay: float = 1.0,
    api_key: str = None,
) -> Dict[str, Any]:
    """Универсальный парсинг всех вакансий SuperJob."""

    def body():
        logger.info("Универсальный парсинг SuperJob запущен")
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 100, 'status': 'Универсальный парсинг вакансий'},
        )
        result = parse_all_vacancies(
            max_pages_per_query=max_pages_per_query, delay=delay, api_key=api_key,
        )
        return {
            'status': 'SUCCESS',
            'result': result,
            'message': (
                f'Универсальный парсинг завершен. '
                f'Запросов: {result["queries_processed"]}, '
                f'Вакансий: {result["total_vacancies"]}, '
                f'Сохранено: {result["total_saved"]}'
            ),
        }

    return run_task_with_error_handling(self, body, task_logger=logger)


@shared_task(
    name=f'{TASK_PREFIX}.get_superjob_vacancy_details_task',
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=1500,
    time_limit=1800,
)
def get_superjob_vacancy_details_task(
    self,
    vacancy_id: str,
    api_key: str = None,
) -> Dict[str, Any]:
    """Получение детальной информации о вакансии SuperJob."""

    def body():
        logger.info("Получение деталей вакансии SuperJob: %s", vacancy_id)
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': 1, 'status': f'Получаем детали: {vacancy_id}'},
        )
        result = get_vacancy_details(vacancy_id, api_key)
        if result:
            return {
                'status': 'SUCCESS',
                'result': result,
                'message': f'Детали вакансии: {result.get("profession", vacancy_id)}',
            }
        return {
            'status': 'FAILURE',
            'error': 'Вакансия не найдена или недоступна',
            'message': f'Не удалось получить вакансию: {vacancy_id}',
        }

    return run_task_with_error_handling(
        self, body, task_logger=logger,
        error_context={'vacancy_id': vacancy_id},
    )


@shared_task(
    name=f'{TASK_PREFIX}.parse_superjob_vacancies_by_config_task',
    bind=True,
    max_retries=2,
    default_retry_delay=120,
    soft_time_limit=5100,
    time_limit=5400,
)
def parse_superjob_vacancies_by_config_task(
    self,
    config: Dict[str, Any],
) -> Dict[str, Any]:
    """Парсинг вакансий SuperJob по переданной конфигурации."""

    def body():
        text = config.get('text')
        logger.info("Парсинг SuperJob по конфигурации")
        self.update_state(
            state='PROGRESS',
            meta={'current': 0, 'total': config.get('max_pages', 5), 'status': f'Парсинг: {text}'},
        )
        result = parse_vacancies_by_text(
            text=text,
            town=config.get('town'),
            experience=config.get('experience'),
            employment=config.get('employment'),
            schedule=config.get('schedule'),
            max_pages=config.get('max_pages', 5),
            delay=config.get('delay', 1.0),
            api_key=config.get('api_key'),
        )
        return {
            'status': 'SUCCESS',
            'result': result,
            'message': (
                f'Парсинг завершен. Найдено: {result["total_vacancies"]}, '
                f'Сохранено: {result["saved_vacancies"]}, '
                f'Обновлено: {result["updated_vacancies"]}'
            ),
        }

    return run_task_with_error_handling(self, body, task_logger=logger)
