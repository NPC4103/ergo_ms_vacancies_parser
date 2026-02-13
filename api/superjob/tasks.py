import logging
from typing import Dict, List, Any

from celery import shared_task

from .scripts import (
    parse_vacancies_by_text,
    parse_all_vacancies,
    parse_vacancies_by_catalogues,
    get_vacancy_details,
)

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def parse_superjob_vacancies_task(self,
                                  text: str = None,
                                  town: str = None,
                                  experience=None,
                                  employment=None,
                                  schedule=None,
                                  max_pages: int = 5,
                                  delay: float = 1.0,
                                  api_key: str = None) -> Dict[str, Any]:
    """Парсинг вакансий SuperJob по текстовому запросу."""
    try:
        logger.info(f"Парсинг SuperJob по запросу: '{text}'")

        self.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': max_pages,
                'status': f'Парсинг вакансий по запросу: {text}',
            }
        )

        result = parse_vacancies_by_text(
            text=text,
            town=town,
            experience=experience,
            employment=employment,
            schedule=schedule,
            max_pages=max_pages,
            delay=delay,
            api_key=api_key,
        )

        logger.info(f"Парсинг SuperJob завершен: {result}")

        return {
            'status': 'SUCCESS',
            'result': result,
            'message': (
                f'Парсинг завершен. Найдено: {result["total_vacancies"]}, '
                f'Сохранено: {result["saved_vacancies"]}, '
                f'Обновлено: {result["updated_vacancies"]}'
            ),
        }

    except Exception as e:
        logger.error(f"Ошибка парсинга SuperJob: {e}")
        return {
            'status': 'FAILURE',
            'error': str(e),
            'message': f'Ошибка при парсинге вакансий: {e}',
        }


@shared_task(bind=True)
def parse_all_superjob_vacancies_task(self,
                                      max_pages_per_query: int = 3,
                                      delay: float = 1.0,
                                      api_key: str = None) -> Dict[str, Any]:
    """Универсальный парсинг всех вакансий SuperJob."""
    try:
        logger.info("Универсальный парсинг SuperJob запущен")

        self.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': 100,
                'status': 'Универсальный парсинг вакансий',
            }
        )

        result = parse_all_vacancies(
            max_pages_per_query=max_pages_per_query,
            delay=delay,
            api_key=api_key,
        )

        logger.info(f"Универсальный парсинг SuperJob завершен: {result}")

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

    except Exception as e:
        logger.error(f"Ошибка универсального парсинга SuperJob: {e}")
        return {
            'status': 'FAILURE',
            'error': str(e),
            'message': f'Ошибка при универсальном парсинге: {e}',
        }


@shared_task(bind=True)
def get_superjob_vacancy_details_task(self,
                                      vacancy_id: str,
                                      api_key: str = None) -> Dict[str, Any]:
    """Получение детальной информации о вакансии SuperJob."""
    try:
        logger.info(f"Получение деталей вакансии SuperJob: {vacancy_id}")

        self.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': 1,
                'status': f'Получаем детали вакансии: {vacancy_id}',
            }
        )

        result = get_vacancy_details(vacancy_id, api_key)

        if result:
            logger.info(f"Детали вакансии получены: {vacancy_id}")
            return {
                'status': 'SUCCESS',
                'result': result,
                'message': f'Детали вакансии: {result.get("profession", vacancy_id)}',
            }

        logger.warning(f"Вакансия не найдена: {vacancy_id}")
        return {
            'status': 'FAILURE',
            'error': 'Вакансия не найдена или недоступна',
            'message': f'Не удалось получить вакансию: {vacancy_id}',
        }

    except Exception as e:
        logger.error(f"Ошибка получения деталей вакансии SuperJob: {e}")
        return {
            'status': 'FAILURE',
            'error': str(e),
            'message': f'Ошибка при получении деталей: {e}',
        }


@shared_task(bind=True)
def parse_superjob_by_catalogues_task(self, catalogue_ids: List[int] = None, max_pages_per_catalogue: int = 10,
    delay: float = 1.0, api_key: str = None) -> Dict[str, Any]:
    """Парсинг вакансий SuperJob по каталогам (отраслям)."""
    try:
        mode = f"{len(catalogue_ids)} выбранных" if catalogue_ids else "всех"
        logger.info(f"Парсинг SuperJob по каталогам ({mode})")

        self.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': len(catalogue_ids) if catalogue_ids else 0,
                'status': f'Парсинг вакансий по каталогам ({mode})',
            }
        )

        result = parse_vacancies_by_catalogues(
            catalogue_ids=catalogue_ids,
            max_pages_per_catalogue=max_pages_per_catalogue,
            delay=delay,
            api_key=api_key,
        )

        logger.info(f"Парсинг SuperJob по каталогам завершен: {result}")

        return {
            'status': 'SUCCESS',
            'result': result,
            'message': (
                f'Парсинг по каталогам завершен. '
                f'Каталогов: {result["catalogues_processed"]}/{result["total_catalogues"]}, '
                f'Вакансий: {result["total_vacancies"]}, '
                f'Сохранено: {result["total_saved"]}'
            ),
        }

    except Exception as e:
        logger.error(f"Ошибка парсинга SuperJob по каталогам: {e}")
        return {
            'status': 'FAILURE',
            'error': str(e),
            'message': f'Ошибка при парсинге по каталогам: {e}',
        }


@shared_task(bind=True)
def parse_superjob_vacancies_by_config_task(self, config: Dict[str, Any]) -> Dict[str, Any]:
    """Парсинг вакансий SuperJob по переданной конфигурации."""
    try:
        logger.info("Парсинг SuperJob по конфигурации")

        text = config.get('text')
        town = config.get('town')
        experience = config.get('experience')
        employment = config.get('employment')
        schedule = config.get('schedule')
        max_pages = config.get('max_pages', 5)
        delay = config.get('delay', 1.0)
        api_key = config.get('api_key')

        self.update_state(
            state='PROGRESS',
            meta={
                'current': 0,
                'total': max_pages,
                'status': f'Парсинг по конфигурации: {text}',
            }
        )

        result = parse_vacancies_by_text(
            text=text,
            town=town,
            experience=experience,
            employment=employment,
            schedule=schedule,
            max_pages=max_pages,
            delay=delay,
            api_key=api_key,
        )

        logger.info(f"Парсинг SuperJob по конфигу завершен: {result}")

        return {
            'status': 'SUCCESS',
            'result': result,
            'message': (
                f'Парсинг завершен. Найдено: {result["total_vacancies"]}, '
                f'Сохранено: {result["saved_vacancies"]}, '
                f'Обновлено: {result["updated_vacancies"]}'
            ),
        }

    except Exception as e:
        logger.error(f"Ошибка парсинга SuperJob по конфигу: {e}")
        return {
            'status': 'FAILURE',
            'error': str(e),
            'message': f'Ошибка при парсинге по конфигурации: {e}',
        }
