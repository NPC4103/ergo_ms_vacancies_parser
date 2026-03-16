import logging

from celery import shared_task

from .scripts import (
    parse_habr_vacancies,
    parse_habr_archived_vacancies,
    parse_habr_all_vacancies,
)

logger = logging.getLogger('modules.vacancies_parser.habr_career')


@shared_task(bind=True)
def parse_habr_vacancies_task(self, pages=5, delay=1.0, get_details=True, search_text=None):
    """
    Celery задача для парсинга вакансий с Хабр Карьеры

    Args:
        pages (int): Количество страниц для парсинга
        delay (float): Задержка между запросами в секундах
        get_details (bool): Получать ли детальную информацию о вакансиях
        search_text (str | None): Текстовый фильтр поиска вакансий
    """
    self.update_state(
        state='PROGRESS',
        meta={
            'current': 0,
            'total': pages,
            'status': 'Начинаем парсинг вакансий с Хабр Карьеры...'
        }
    )

    result = parse_habr_vacancies(
        pages=pages,
        delay=delay,
        get_details=get_details,
        search_text=search_text,
    )

    return {
        'status': 'SUCCESS',
        'result': result,
        'message': (
            f'Парсинг завершен. Обработано: {result["total"]}, '
            f'Новых: {result["new"]}, Обновлено: {result["updated"]}, '
            f'Ошибок: {result["errors"]}'
        ),
    }


@shared_task(bind=True)
def parse_habr_archived_vacancies_task(self, pages=5, delay=1.0, search_text=None):
    """
    Celery задача для парсинга архивных вакансий с Хабр Карьеры

    Args:
        pages (int): Количество страниц для парсинга
        delay (float): Задержка между запросами в секундах
        search_text (str | None): Текстовый фильтр поиска вакансий
    """
    self.update_state(
        state='PROGRESS',
        meta={
            'current': 0,
            'total': pages,
            'status': 'Начинаем парсинг архивных вакансий с Хабр Карьеры...'
        }
    )

    result = parse_habr_archived_vacancies(
        pages=pages,
        delay=delay,
        search_text=search_text,
    )

    return {
        'status': 'SUCCESS',
        'result': result,
        'message': (
            f'Парсинг архивных вакансий завершен. Обработано: {result["total"]}, '
            f'Новых: {result["new"]}, Обновлено: {result["updated"]}, '
            f'Ошибок: {result["errors"]}'
        ),
    }


@shared_task(bind=True)
def parse_habr_all_vacancies_task(
    self, pages=5, delay=1.0, get_details=True, search_text=None
):
    """
    Celery задача для парсинга всех вакансий (активных и архивных) с Хабр Карьеры

    Args:
        pages (int): Количество страниц для парсинга
        delay (float): Задержка между запросами в секундах
        get_details (bool): Получать ли детальную информацию о вакансиях
        search_text (str | None): Текстовый фильтр поиска вакансий
    """
    self.update_state(
        state='PROGRESS',
        meta={
            'current': 0,
            'total': pages * 2,
            'status': 'Начинаем парсинг всех вакансий с Хабр Карьеры...'
        }
    )

    result = parse_habr_all_vacancies(
        pages=pages,
        delay=delay,
        get_details=get_details,
        search_text=search_text,
    )

    return {
        'status': 'SUCCESS',
        'result': result,
        'message': (
            f'Парсинг всех вакансий завершен. '
            f'Всего обработано: {result["total"]["total"]}, '
            f'Новых: {result["total"]["new"]}, '
            f'Обновлено: {result["total"]["updated"]}, '
            f'Ошибок: {result["total"]["errors"]}'
        ),
    }


@shared_task(bind=True)
def parse_habr_vacancies_by_technologies_task(
    self,
    pages_per_query: int = 3,
    delay: float = 1.2,
    get_details: bool = False,
    max_queries: int = 30,
):
    """
    Парсинг Habr Career по списку технологий из competence_core.
    Для каждой технологии вызывается поиск с search_text=название.
    """
    try:
        from modules.vacancies_parser.api.core.utils.technology_search_generator import (
            TechnologySearchGenerator,
        )
    except Exception as e:
        logger.warning("competence_core недоступен для Habr by_technologies: %s", e)
        return {
            'status': 'FAILURE',
            'error': str(e),
            'message': 'Не удалось загрузить технологии из competence_core',
        }
    generator = TechnologySearchGenerator()
    generator.load_technologies(limit=max_queries)
    queries = generator.generate_search_queries(use_aliases=False, max_queries=max_queries)
    if not queries:
        return {
            'status': 'FAILURE',
            'error': 'Нет запросов',
            'message': 'Список технологий из competence_core пуст',
        }
    total_processed = 0
    total_new = 0
    total_updated = 0
    total_errors = 0
    for i, search_text in enumerate(queries, 1):
        self.update_state(
            state='PROGRESS',
            meta={
                'current': i,
                'total': len(queries),
                'status': f'Парсинг по запросу: {search_text}',
            },
        )
        try:
            result = parse_habr_vacancies(
                pages=pages_per_query,
                delay=delay,
                get_details=get_details,
                search_text=search_text,
            )
            total_processed += result['total']
            total_new += result['new']
            total_updated += result['updated']
            total_errors += result['errors']
        except Exception as e:
            logger.exception("Ошибка парсинга Habr по запросу %s: %s", search_text, e)
            total_errors += 1
    return {
        'status': 'SUCCESS',
        'result': {
            'queries_count': len(queries),
            'total_processed': total_processed,
            'new': total_new,
            'updated': total_updated,
            'errors': total_errors,
        },
        'message': (
            f'Парсинг по технологиям завершен. Запросов: {len(queries)}, '
            f'Обработано: {total_processed}, Новых: {total_new}, '
            f'Обновлено: {total_updated}, Ошибок: {total_errors}'
        ),
    }
