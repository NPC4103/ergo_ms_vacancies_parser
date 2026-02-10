from celery import shared_task
from .scripts import parse_habr_vacancies, parse_habr_archived_vacancies, parse_habr_all_vacancies


@shared_task(bind=True)
def parse_habr_vacancies_task(self, access_token, pages=5, delay=1.0, get_details=True):
    """
    Celery задача для парсинга вакансий с Хабр Карьеры

    Args:
        access_token (str): Токен доступа к API
        pages (int): Количество страниц для парсинга
        delay (float): Задержка между запросами в секундах
        get_details (bool): Получать ли детальную информацию о вакансиях
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
        access_token=access_token,
        pages=pages,
        delay=delay,
        get_details=get_details
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
def parse_habr_archived_vacancies_task(self, access_token, pages=5, delay=1.0):
    """
    Celery задача для парсинга архивных вакансий с Хабр Карьеры

    Args:
        access_token (str): Токен доступа к API
        pages (int): Количество страниц для парсинга
        delay (float): Задержка между запросами в секундах
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
        access_token=access_token,
        pages=pages,
        delay=delay
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
def parse_habr_all_vacancies_task(self, access_token, pages=5, delay=1.0, get_details=True):
    """
    Celery задача для парсинга всех вакансий (активных и архивных) с Хабр Карьеры

    Args:
        access_token (str): Токен доступа к API
        pages (int): Количество страниц для парсинга
        delay (float): Задержка между запросами в секундах
        get_details (bool): Получать ли детальную информацию о вакансиях
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
        access_token=access_token,
        pages=pages,
        delay=delay,
        get_details=get_details
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
