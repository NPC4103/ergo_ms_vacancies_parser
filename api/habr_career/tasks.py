from celery import shared_task
from .scripts import parse_habr_vacancies, parse_habr_archived_vacancies, parse_habr_all_vacancies


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
