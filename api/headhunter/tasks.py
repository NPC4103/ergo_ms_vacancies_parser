import json
import logging
import time
import random
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import List, Optional, Sequence, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial
import asyncio

from celery import chord, shared_task
from django.apps import apps as django_apps
from django.db.models import Count, Avg, Min, Max
from django.utils import timezone

from .scripts import parse_vacancies_by_text, parse_all_vacancies, HeadHunterParser, ParsingMetrics
from .models import Vacancy


logger = logging.getLogger('modules.vacancies_parser.headhunter')
SKILL_MAP_APP = 'modules.competence_core.api.skill_map'
PROFESSIONAL_ROLES_CONFIG = Path(__file__).parent / 'config' / 'professional_roles_config.json'


def _load_target_category_id() -> str:
    """
    Загружает ID целевой категории ролей (для IT) из конфигурации.
    По умолчанию возвращает '11' (IT категория), если конфиг недоступен или ID не задан.
    
    Returns:
        str: ID категории (по умолчанию '11' для IT)
    """
    # Категория 11 - IT по умолчанию
    DEFAULT_CATEGORY_ID = '11'
    
    try:
        if PROFESSIONAL_ROLES_CONFIG.exists():
            with open(PROFESSIONAL_ROLES_CONFIG, 'r', encoding='utf-8') as config_file:
                config_data = json.load(config_file)
            category_id = config_data.get('target_category', {}).get('id')
            if category_id:
                logger.debug(f'Загружена категория {category_id} из конфига')
                return str(category_id)
        else:
            logger.debug(f'Файл конфигурации {PROFESSIONAL_ROLES_CONFIG} не найден, используем категорию по умолчанию: {DEFAULT_CATEGORY_ID}')
    except Exception as exc:
        logger.warning('Не удалось загрузить target_category.id из конфига: %s, используем категорию по умолчанию: %s', exc, DEFAULT_CATEGORY_ID)
    
    return DEFAULT_CATEGORY_ID


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=6900,
    time_limit=7200,
)
def parse_hh_segment_by_technologies(
    self,
    date_from: str,
    date_to: str,
    categories: Optional[List[str]] = None,
    top_n: int = 50,
    use_aliases: bool = False,
    area: int = 113,
    pages: int = 2,
    delay: float = 1.5,
    get_details: bool = True,
    max_queries: Optional[int] = None,
    tech_min_popularity: int = 0,
    use_jitter: bool = True,
    rotate_user_agent: bool = True,
    use_proxy: bool = False,
    custom_proxies: Optional[List[Dict[str, str]]] = None
):
    """
    Celery-задача для парсинга вакансий по технологиям в заданном временном сегменте.

    Args:
        date_from (str): Дата начала сегмента (YYYY-MM-DD)
        date_to (str): Дата окончания сегмента (YYYY-MM-DD)
        categories (List[str]): Список категорий технологий
        top_n (int): Количество топовых технологий
        use_aliases (bool): Использовать алиасы технологий
        area (int): ID региона
        pages (int): Количество страниц на запрос
        delay (float): Задержка между запросами
        get_details (bool): Получать детали вакансий
        max_queries (int): Максимальное количество запросов
        tech_min_popularity (int): Минимальная популярность технологий

    Returns:
        dict: Статистика парсинга сегмента
    """
    logger.info('='*70)
    logger.info(f'Парсинг сегмента {date_from} - {date_to} по технологиям')
    logger.info('='*70)

    if not _skill_map_installed():
        msg = f'Приложение {SKILL_MAP_APP} не подключено'
        logger.warning(msg)
        return {'error': msg, 'segment': f'{date_from}_{date_to}'}

    try:
        from .utils.technology_search_generator import TechnologySearchGenerator
        from .scripts import HeadHunterParser, ParsingMetrics
        generator = TechnologySearchGenerator()

        # Создаем парсер с улучшенными настройками обхода блокировок
        metrics = ParsingMetrics()
        parser = HeadHunterParser(
            metrics=metrics,
            use_jitter=use_jitter,
            rotate_user_agent=rotate_user_agent,
            use_proxy=use_proxy,
            custom_proxies=custom_proxies
        )

        # Загружаем технологии
        # Загружаем технологии
        if categories:
            logger.info(f'Загрузка технологий категорий: {categories}')
            generator.load_technologies(
                categories=categories,
                min_popularity=tech_min_popularity,
                limit=top_n
            )
        else:
            logger.info(f'Загрузка технологий (лимит: {top_n})')
            generator.load_technologies(
                min_popularity=tech_min_popularity,
                limit=top_n
            )

        # Генерируем поисковые запросы
        search_queries = generator.generate_search_queries(
            use_aliases=use_aliases,
            max_queries=max_queries
        )

        logger.info(f'Сгенерировано запросов: {len(search_queries)}')

        if not search_queries:
            msg = 'Не найдено подходящих технологий для парсинга'
            logger.warning(msg)
            return {
                'error': msg,
                'segment': f'{date_from}_{date_to}',
                'technologies_count': 0,
                'search_queries_count': 0
            }

        # Парсим вакансии для сегмента с автоматическим разделением при необходимости
        logger.info(f'Запуск парсинга {len(search_queries)} запросов для сегмента {date_from}-{date_to}')

        # Проверяем количество вакансий для первого запроса
        from datetime import datetime
        start_date = datetime.fromisoformat(date_from.replace('T', ' '))
        end_date = datetime.fromisoformat(date_to.replace('T', ' '))

        # Если сегмент больше 1 дня, проверяем на превышение лимита
        segment_days = (end_date - start_date).days
        if segment_days > 1:
            # Проверяем примерное количество вакансий по первому запросу
            sample_result = parser.search_vacancies(
                text=search_queries[0] if search_queries else 'программист',
                area=area,
                per_page=1,
                page=0,
                date_from=date_from,
                date_to=date_to
            )

            if sample_result and 'found' in sample_result:
                estimated_total = sample_result['found']
                # Если больше 1500 вакансий на запрос, разделяем сегмент
                if estimated_total > 1500:
                    logger.warning(f'Сегмент {date_from}-{date_to} содержит ~{estimated_total} вакансий, '
                                 f'разделяем на меньшие части')
                    result = _split_segment_and_parse(
                        search_queries, start_date, end_date, area, pages, delay, get_details,
                        parser, date_from, date_to
                    )
                else:
                    result = parse_vacancies_by_text(
                        text_list=search_queries,
                        area=area,
                        pages=pages,
                        delay=delay,
                        get_details=get_details,
                        date_from=date_from,
                        date_to=date_to
                    )
            else:
                # Если не можем проверить, парсим как есть
                result = parse_vacancies_by_text(
                    text_list=search_queries,
                    area=area,
                    pages=pages,
                    delay=delay,
                    get_details=get_details,
                    date_from=date_from,
                    date_to=date_to
                )
        else:
            # Для сегментов в 1 день парсим напрямую
            result = parse_vacancies_by_text(
                text_list=search_queries,
                area=area,
                pages=pages,
                delay=delay,
                get_details=get_details,
                date_from=date_from,
                date_to=date_to
            )

        # Добавляем информацию о сегменте
        result.update({
            'segment': f'{date_from}_{date_to}',
            'technologies_count': len(generator.technologies),
            'search_queries_count': len(search_queries),
            'search_queries': search_queries[:10]  # Первые 10 для логов
        })

        logger.info(f'Сегмент {date_from}-{date_to} завершен: {result.get("new_vacancies", 0)} новых, '
                   f'{result.get("updated_vacancies", 0)} обновлено')

        return result

    except Exception as e:
        logger.exception(f'Ошибка при парсинге сегмента {date_from}-{date_to}')
        return {
            'error': str(e),
            'segment': f'{date_from}_{date_to}',
            'technologies_count': 0,
            'search_queries_count': 0
        }


def _split_segment_and_parse(search_queries, start_date, end_date, area, pages, delay, get_details,
                           parser, orig_date_from, orig_date_to):
    """Разделяет сегмент на меньшие части при превышении лимита вакансий"""
    from datetime import timedelta

    # Разделяем на 2 равные части
    mid_date = start_date + (end_date - start_date) / 2

    logger.info(f'Разделение сегмента {orig_date_from}-{orig_date_to} на: '
               f'{start_date.date()}-{mid_date.date()} и {mid_date.date()}-{end_date.date()}')

    # Парсим первую половину
    result1 = parse_vacancies_by_text(
        text_list=search_queries,
        area=area,
        pages=pages,
        delay=delay,
        get_details=get_details,
        date_from=start_date.isoformat(),
        date_to=mid_date.isoformat()
    )

    # Парсим вторую половину
    result2 = parse_vacancies_by_text(
        text_list=search_queries,
        area=area,
        pages=pages,
        delay=delay,
        get_details=get_details,
        date_from=mid_date.isoformat(),
        date_to=end_date.isoformat()
    )

    # Объединяем результаты
    combined_result = {
        'total_vacancies': result1.get('total_vacancies', 0) + result2.get('total_vacancies', 0),
        'new_vacancies': result1.get('new_vacancies', 0) + result2.get('new_vacancies', 0),
        'updated_vacancies': result1.get('updated_vacancies', 0) + result2.get('updated_vacancies', 0),
        'total_in_db': max(result1.get('total_in_db', 0), result2.get('total_in_db', 0)),
        'segment_split': True,
        'sub_segments': [
            f'{start_date.date()}_{mid_date.date()}',
            f'{mid_date.date()}_{end_date.date()}'
        ]
    }

    return combined_result


def _skill_map_installed() -> bool:
    """Проверяет, подключено ли приложение компетенций."""
    return django_apps.is_installed(SKILL_MAP_APP)

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=6900,
    time_limit=7200,
)
def parse_hh_vacancies_task(
    self,
    text_list: Optional[Sequence[str]] = None,
    area: int = 113,
    pages: int = 2,
    delay: float = 1.0,
    get_details: bool = True,
    universal: bool = False,
    pages_per_area: int = 5,
    max_total_pages: int = 100,
    areas_only: bool = False,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    config: Optional[dict] = None
):
    """
    Celery-задача для парсинга вакансий с HeadHunter.
    Возвращает статистику по результатам парсинга.
    """
    logger.info(
        "Запуск задачи parse_hh_vacancies_task: text_list=%s, universal=%s",
        text_list,
        universal,
    )
    
    if not universal and not text_list:
        error_msg = 'Необходимо указать text_list или universal=True'
        logger.error(error_msg)
        return {'error': error_msg}
    
    try:
        if universal:
            logger.info("Выполняется универсальный парсинг")
            result = parse_all_vacancies(
                pages_per_area=pages_per_area,
                delay=delay,
                max_total_pages=max_total_pages,
                areas_only=areas_only
            )
            logger.info("Универсальный парсинг завершен")
            return {
                'mode': 'universal',
                'areas_processed': result.get('areas_processed'),
                'roles_processed': result.get('roles_processed'),
                'pages_processed': result.get('pages_processed'),
                'total_vacancies': result.get('total_vacancies'),
                'new_vacancies': result.get('new_vacancies'),
                'updated_vacancies': result.get('updated_vacancies'),
                'total_in_db': result.get('total_in_db'),
            }
        
        assert text_list is not None
        queries = list(text_list)
        logger.info("Выполняется парсинг по списку текстов (%d)", len(queries))
        result = parse_vacancies_by_text(
            text_list=queries,
            area=area,
            pages=pages,
            delay=delay,
            get_details=get_details,
            date_from=date_from,
            date_to=date_to
        )
        logger.info("Парсинг по тексту завершен")
        return {
            'mode': 'by_text',
            'total_vacancies': result.get('total_vacancies'),
            'new_vacancies': result.get('new_vacancies'),
            'updated_vacancies': result.get('updated_vacancies'),
            'total_in_db': result.get('total_in_db'),
        }
    except Exception as exc:
        logger.error('Ошибка выполнения parse_hh_vacancies_task', exc_info=True)
        raise self.retry(exc=exc)

@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=120,
    soft_time_limit=5100,
    time_limit=5400,
)
def parse_vacancies_by_technologies(
    self,
    categories: Optional[List[str]] = None,
    top_n: int = 50,
    use_aliases: bool = False,
    area: int = 113,
    pages: int = 2,
    delay: float = 1.5,
    get_details: bool = True,
    max_queries: Optional[int] = None
):
    """
    Celery-задача для парсинга вакансий по технологиям из базы данных.
    
    Автоматически генерирует поисковые запросы на основе технологий
    и их синонимов, затем запускает парсинг вакансий.
    
    Args:
        categories (List[str]): Список категорий технологий для парсинга
                               (LANG, FRAMEWORK, DB, TOOL, PLATFORM, PROTOCOL, LIBRARY, SERVICE)
                               Если None - используются все категории
        top_n (int): Количество топовых технологий (по популярности)
        use_aliases (bool): Использовать ли алиасы технологий как отдельные запросы
        area (int): ID региона для поиска (113 = Россия)
        pages (int): Количество страниц для парсинга на запрос
        delay (float): Задержка между запросами в секундах
        get_details (bool): Получать ли детальную информацию о вакансиях
        max_queries (int): Максимальное количество поисковых запросов
    
    Returns:
        dict: Статистика парсинга
    """
    logger.info('='*70)
    logger.info('Запуск парсинга вакансий по технологиям')
    logger.info('='*70)
    logger.info(f'Параметры: categories={categories}, top_n={top_n}, '
               f'use_aliases={use_aliases}, area={area}, pages={pages}')
    
    if not _skill_map_installed():
        msg = f'Приложение {SKILL_MAP_APP} не подключено'
        logger.warning(msg)
        return {'error': msg}

    try:
        from .utils.technology_search_generator import TechnologySearchGenerator
        generator = TechnologySearchGenerator()
        
        if categories:
            logger.info(f'Загрузка технологий категорий: {categories}')
            generator.load_technologies(
                categories=categories,
                limit=top_n,
                include_aliases=use_aliases
            )
        else:
            logger.info(f'Загрузка топ-{top_n} технологий')
            generator.load_technologies(
                limit=top_n,
                include_aliases=use_aliases
            )
        
        stats = generator.get_statistics()
        logger.info(f"Загружено технологий: {stats.get('total_technologies')}")
        if use_aliases:
            logger.info(f"Всего алиасов: {stats.get('total_aliases')}")
        
        search_queries = generator.generate_search_queries(
            use_aliases=use_aliases,
            max_queries=max_queries
        )
        
        logger.info('Сгенерировано %d поисковых запросов', len(search_queries))
        
        result = parse_vacancies_by_text(
            text_list=search_queries,
            area=area,
            pages=pages,
            delay=delay,
            get_details=get_details
        )
        
        logger.info('Парсинг завершен')
        logger.info('='*70)
        
        return {
            'mode': 'by_technologies',
            'technologies_count': stats.get('total_technologies'),
            'search_queries_count': len(search_queries),
            'search_queries': search_queries[:20],
            'total_vacancies': result.get('total_vacancies'),
            'new_vacancies': result.get('new_vacancies'),
            'updated_vacancies': result.get('updated_vacancies'),
            'total_in_db': result.get('total_in_db'),
        }
        
    except Exception as exc:
        logger.error('Ошибка при парсинге по технологиям', exc_info=True)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=90,
    soft_time_limit=3300,
    time_limit=3600,
)
def parse_vacancies_by_category(
    self,
    category,
    use_aliases=False,
    area=113,
    pages=2,
    delay=1.5,
    get_details=True,
    max_queries=50
):
    """
    Celery-задача для парсинга вакансий по конкретной категории технологий.
    
    Args:
        category (str): Категория технологий (LANG, FRAMEWORK, DB, и т.д.)
        use_aliases (bool): Использовать ли алиасы технологий
        area (int): ID региона для поиска
        pages (int): Количество страниц для парсинга
        delay (float): Задержка между запросами
        get_details (bool): Получать ли детальную информацию
        max_queries (int): Максимальное количество запросов
    
    Returns:
        dict: Статистика парсинга
    """
    logger.info(f'Запуск парсинга по категории: {category}')
    
    if not _skill_map_installed():
        return {
            'mode': 'by_category',
            'category': category,
            'error': f'Приложение {SKILL_MAP_APP} не подключено'
        }

    try:
        from .utils.technology_search_generator import TechnologySearchGenerator
        generator = TechnologySearchGenerator()
        
        # Генерируем запросы для категории
        search_queries = generator.generate_by_category(
            category=category,
            use_aliases=use_aliases,
            max_per_category=max_queries
        )
        
        logger.info(f'Сгенерировано {len(search_queries)} запросов для {category}')
        
        if not search_queries:
            return {
                'mode': 'by_category',
                'category': category,
                'error': 'Не найдено технологий для данной категории'
            }
        
        # Запускаем парсинг
        result = parse_vacancies_by_text(
            text_list=search_queries,
            area=area,
            pages=pages,
            delay=delay,
            get_details=get_details
        )
        
        logger.info(f'Парсинг категории {category} завершен')
        
        return {
            'mode': 'by_category',
            'category': category,
            'search_queries_count': len(search_queries),
            'search_queries': search_queries,
            'total_vacancies': result.get('total_vacancies'),
            'new_vacancies': result.get('new_vacancies'),
            'updated_vacancies': result.get('updated_vacancies'),
            'total_in_db': result.get('total_in_db'),
        }
        
    except Exception as exc:
        logger.error('Ошибка при парсинге категории %s', category, exc_info=True)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=1500,
    time_limit=1800,
)
def parse_single_vacancy_task(self, vacancy_id, force_update=False):
    """
    Celery-задача для парсинга одной вакансии по ID.
    Возвращает результат сохранения/обновления.
    """
    logger.info(f"Запуск задачи parse_single_vacancy_task для вакансии {vacancy_id}, force_update={force_update}")
    
    try:
        parser = HeadHunterParser()
        vacancy_manager = getattr(Vacancy, 'objects')
        existing_vacancy = vacancy_manager.filter(hh_id=vacancy_id).first()
        if existing_vacancy and not force_update:
            msg = f'Вакансия {vacancy_id} уже есть в базе'
            logger.info(msg)
            return {'status': 'exists', 'message': msg}
        
        vacancy_data = parser.get_vacancy_details(vacancy_id)
        if not vacancy_data or not isinstance(vacancy_data, dict) or 'id' not in vacancy_data:
            msg = f'Вакансия {vacancy_id} не найдена или данные некорректны'
            logger.error(msg)
            return {'status': 'error', 'message': msg}
        
        vacancy = parser.parse_vacancy(vacancy_data)
        if not vacancy:
            msg = 'Ошибка при парсинге вакансии'
            logger.error(msg)
            return {'status': 'error', 'message': msg}
        if existing_vacancy:
            if force_update:
                new_data = {
                    'title': vacancy.title,
                    'company_name': vacancy.company_name,
                    'salary_from': vacancy.salary_from,
                    'salary_to': vacancy.salary_to,
                    'salary_currency': vacancy.salary_currency,
                    'salary_gross': vacancy.salary_gross,
                    'city': vacancy.city,
                    'address': vacancy.address,
                    'description': vacancy.description,
                    'requirements': vacancy.requirements,
                    'responsibilities': vacancy.responsibilities,
                    'employment_type': vacancy.employment_type,
                    'experience_level': vacancy.experience_level,
                    'key_skills': vacancy.key_skills,
                    'schedule_type': vacancy.schedule_type,
                    'professional_role': vacancy.professional_role,
                    'employer_name': vacancy.employer_name,
                    'premium': vacancy.premium,
                    'has_test': vacancy.has_test,
                    'response_letter_required': vacancy.response_letter_required,
                }
                if existing_vacancy.has_changes(new_data):
                    existing_vacancy.create_version(new_data)
                    for field, value in new_data.items():
                        setattr(existing_vacancy, field, value)
                    existing_vacancy.save()
                    return {'status': 'updated', 'message': f'Вакансия {vacancy_id} обновлена'}
                return {'status': 'no_changes', 'message': 'Изменений не обнаружено'}
            return {'status': 'exists', 'message': f'Вакансия {vacancy_id} уже есть в базе'}
        else:
            vacancy.save()
            return {'status': 'created', 'message': f'Вакансия {vacancy_id} успешно сохранена'}
    except Exception as exc:
        logger.error('Ошибка при обработке вакансии %s', vacancy_id, exc_info=True)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=90,
    soft_time_limit=3600,
    time_limit=3900,
)
def parse_vacancies_batch_task(
    self,
    vacancy_ids: List[str],
    force_update: bool = False,
) -> Dict[str, Any]:
    """
    Батчевая Celery-задача для парсинга нескольких вакансий по ID.

    Использует асинхронный парсер для параллельных запросов к API HeadHunter.
    """
    import asyncio

    from .async_parser import AsyncHeadHunterParser, AsyncParsingConfig
    from .scripts import ParsingMetrics

    logger.info(
        "Запуск задачи parse_vacancies_batch_task: count=%d, force_update=%s",
        len(vacancy_ids),
        force_update,
    )

    if not vacancy_ids:
        return {'status': 'no_ids', 'message': 'Список vacancy_ids пуст'}

    async def _fetch_batch(ids: List[str]) -> List[Any]:
        metrics = ParsingMetrics()
        config = AsyncParsingConfig(
            max_concurrent_requests=20,
            request_delay=0.1,
        )
        async with AsyncHeadHunterParser(config=config, metrics=metrics) as parser:
            return await parser.get_vacancy_details_batch(ids)

    try:
        # 1. Асинхронно получаем детали по всем ID
        results = asyncio.run(_fetch_batch(vacancy_ids))

        # 2. Парсим все вакансии
        parser = HeadHunterParser()
        vacancy_manager = getattr(Vacancy, 'objects')
        
        # Поля для отслеживания изменений и обновления (как в parse_hh_by_text_and_date)
        CHANGE_TRACKED_FIELDS = [
            'title', 'company_name', 'salary_from', 'salary_to', 'salary_currency',
            'salary_gross', 'city', 'address', 'description', 'requirements',
            'responsibilities', 'employment_type', 'experience_level', 'key_skills',
            'schedule_type', 'professional_role', 'employer_name', 'premium',
            'has_test', 'response_letter_required'
        ]
        UPDATABLE_FIELDS = list(dict.fromkeys(CHANGE_TRACKED_FIELDS + [
            'skills', 'url', 'company_url', 'alternate_url', 'apply_alternate_url',
            'employer_id', 'employer_trusted', 'employer_blacklisted', 'published_at'
        ]))

        parsed_vacancies: List[Vacancy] = []
        vacancy_id_to_data: Dict[str, Dict[str, Any]] = {}
        errors = 0

        for vacancy_id, vacancy_data in results:
            try:
                if not vacancy_data or not isinstance(vacancy_data, dict) or 'id' not in vacancy_data:
                    logger.error(
                        'Вакансия %s не найдена или данные некорректны в batch-задаче',
                        vacancy_id,
                    )
                    errors += 1
                    continue

                vacancy = parser.parse_vacancy(vacancy_data)
                if not vacancy:
                    logger.error('Ошибка при парсинге вакансии %s в batch-задаче', vacancy_id)
                    errors += 1
                    continue

                if not vacancy.hh_id:
                    vacancy.hh_id = str(vacancy_id)

                parsed_vacancies.append(vacancy)
                vacancy_id_to_data[str(vacancy_id)] = vacancy_data

            except Exception as exc:  # noqa: BLE001
                logger.error(
                    'Ошибка при парсинге вакансии %s в batch-задаче', vacancy_id, exc_info=True
                )
                errors += 1

        if not parsed_vacancies:
            return {
                'status': 'error',
                'message': 'Не удалось распарсить ни одной вакансии',
                'total': len(vacancy_ids),
                'created': 0,
                'updated': 0,
                'exists': 0,
                'no_changes': 0,
                'errors': errors,
            }

        # 3. Загружаем все существующие вакансии одним запросом
        all_vacancy_ids = [v.hh_id for v in parsed_vacancies if v.hh_id]
        existing_vacancies = {
            v.hh_id: v for v in vacancy_manager.filter(hh_id__in=all_vacancy_ids)
        }

        # 4. Разделяем на новые и существующие, обрабатываем батчами
        BATCH_SIZE = 100
        created = 0
        updated = 0
        exists = 0
        no_changes = 0

        for batch_start in range(0, len(parsed_vacancies), BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, len(parsed_vacancies))
            batch_vacancies = parsed_vacancies[batch_start:batch_end]

            new_vacancies: List[Vacancy] = []
            to_update: List[Vacancy] = []

            for vacancy in batch_vacancies:
                if not vacancy.hh_id:
                    errors += 1
                    continue

                existing = existing_vacancies.get(vacancy.hh_id)
                if existing:
                    if not force_update:
                        exists += 1
                        continue

                    # Проверяем изменения
                    new_data = {field: getattr(vacancy, field) for field in CHANGE_TRACKED_FIELDS}
                    if existing.has_changes(new_data):
                        existing.create_version(new_data)
                        # Обновляем поля для bulk_update
                        for field in UPDATABLE_FIELDS:
                            setattr(existing, field, getattr(vacancy, field))
                        to_update.append(existing)
                        updated += 1
                    else:
                        no_changes += 1
                else:
                    new_vacancies.append(vacancy)

            # Батчевое создание новых вакансий
            if new_vacancies:
                try:
                    new_ids = [v.hh_id for v in new_vacancies if v.hh_id]
                    count_before = vacancy_manager.filter(hh_id__in=new_ids).count()
                    
                    vacancy_manager.bulk_create(new_vacancies, ignore_conflicts=True)
                    
                    count_after = vacancy_manager.filter(hh_id__in=new_ids).count()
                    actually_created = count_after - count_before
                    created += actually_created
                    
                    if actually_created < len(new_vacancies):
                        logger.warning(
                            'При bulk_create: попытка создать %d, реально создано %d, конфликтов %d',
                            len(new_vacancies), actually_created, len(new_vacancies) - actually_created
                        )
                except Exception as bulk_exc:  # noqa: BLE001
                    errors += len(new_vacancies)
                    logger.error('Ошибка при bulk_create в batch-задаче', exc_info=True)

            # Батчевое обновление существующих вакансий
            if to_update:
                try:
                    vacancy_manager.bulk_update(
                        to_update,
                        fields=UPDATABLE_FIELDS,
                        batch_size=BATCH_SIZE
                    )
                except Exception as bulk_exc:  # noqa: BLE001
                    errors += len(to_update)
                    logger.error('Ошибка при bulk_update в batch-задаче', exc_info=True)

        total = len(vacancy_ids)
        logger.info(
            'Batch-задача завершена: total=%d, created=%d, updated=%d, '
            'exists=%d, no_changes=%d, errors=%d',
            total,
            created,
            updated,
            exists,
            no_changes,
            errors,
        )

        return {
            'status': 'completed',
            'total': total,
            'created': created,
            'updated': updated,
            'exists': exists,
            'no_changes': no_changes,
            'errors': errors,
        }
    except Exception as exc:  # noqa: BLE001
        logger.error('Ошибка выполнения parse_vacancies_batch_task', exc_info=True)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=300,
    soft_time_limit=7200,
    time_limit=7500,
)
def check_vacancies_status_task(
    self,
    batch_size: int = 100,
    delay: float = 0.2,
    max_vacancies: int = 1000
):
    """
    Celery-задача для проверки статуса активных вакансий.
    
    Проверяет, не закрыты ли вакансии на hh.ru, и помечает их как неактивные.
    
    Args:
        batch_size: Размер пакета для обработки
        delay: Задержка между запросами в секундах
        max_vacancies: Максимальное количество вакансий для проверки за один запуск
    
    Returns:
        dict: Статистика проверки
    """
    from .scripts import HeadHunterParser, ParsingMetrics
    
    logger.info('='*70)
    logger.info('Запуск проверки статуса вакансий')
    logger.info('Параметры: batch_size=%d, delay=%.1f, max_vacancies=%d', batch_size, delay, max_vacancies)
    logger.info('='*70)
    
    try:
        metrics = ParsingMetrics()
        parser = HeadHunterParser(metrics=metrics)
        
        # Получаем активные вакансии для проверки (самые старые первыми)
        active_vacancies = Vacancy.objects.filter(  # type: ignore[attr-defined]
            is_active=True
        ).order_by('updated_at')[:max_vacancies]
        
        total_count = active_vacancies.count()
        logger.info('Найдено %d активных вакансий для проверки', total_count)
        
        if total_count == 0:
            return {
                'status': 'completed',
                'checked': 0,
                'archived': 0,
                'still_active': 0,
                'errors': 0
            }
        
        archived_count = 0
        still_active_count = 0
        error_count = 0
        
        # Обрабатываем пакетами
        vacancy_ids = list(active_vacancies.values_list('id', 'hh_id'))
        
        for i, (db_id, hh_id) in enumerate(vacancy_ids, 1):
            try:
                # Проверяем статус вакансии
                vacancy_data = parser.check_vacancy_exists(hh_id)
                
                if vacancy_data is None:
                    # Вакансия закрыта или удалена
                    Vacancy.objects.filter(  # type: ignore[attr-defined]
                        id=db_id
                    ).update(
                        is_active=False,
                        updated_at=timezone.now()
                    )
                    archived_count += 1
                    logger.debug('Вакансия %s помечена как неактивная', hh_id)
                else:
                    still_active_count += 1
                
                # Задержка между запросами
                if i < len(vacancy_ids):
                    time.sleep(delay)
                
                # Логируем прогресс каждые batch_size записей
                if i % batch_size == 0:
                    logger.info(
                        'Прогресс: %d/%d (%.1f%%), закрыто: %d',
                        i, total_count, (i / total_count) * 100, archived_count
                    )
                    
            except Exception as e:
                error_count += 1
                metrics.record_error(f"Ошибка проверки вакансии {hh_id}: {e}")
                logger.warning('Ошибка при проверке вакансии %s: %s', hh_id, e)
        
        logger.info('='*70)
        logger.info('Проверка завершена')
        logger.info('Проверено: %d, закрыто: %d, активно: %d, ошибок: %d',
                   total_count, archived_count, still_active_count, error_count)
        logger.info('='*70)
        
        metrics.log_summary()
        
        return {
            'status': 'completed',
            'checked': total_count,
            'archived': archived_count,
            'still_active': still_active_count,
            'errors': error_count,
            'metrics': metrics.to_dict()
        }
        
    except Exception as exc:
        logger.error('Ошибка при проверке статуса вакансий', exc_info=True)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=1,
    default_retry_delay=60,
    soft_time_limit=300,
    time_limit=360,
)
def update_vacancy_details_task(self, vacancy_id: str):
    """
    Celery-задача для обновления деталей конкретной вакансии.
    
    Args:
        vacancy_id: ID вакансии на hh.ru
        
    Returns:
        dict: Результат обновления
    """
    from .scripts import HeadHunterParser
    
    logger.info('Обновление деталей вакансии %s', vacancy_id)
    
    try:
        parser = HeadHunterParser()
        
        # Получаем вакансию из БД
        vacancy = Vacancy.objects.filter(hh_id=vacancy_id).first()  # type: ignore[attr-defined]
        if not vacancy:
            return {'status': 'not_found', 'message': f'Вакансия {vacancy_id} не найдена в БД'}
        
        # Получаем актуальные данные
        vacancy_data = parser.get_vacancy_details(vacancy_id)
        
        if not vacancy_data:
            # Вакансия закрыта
            vacancy.is_active = False
            vacancy.save(update_fields=['is_active', 'updated_at'])
            return {'status': 'archived', 'message': f'Вакансия {vacancy_id} закрыта'}
        
        if vacancy_data.get('archived'):
            vacancy.is_active = False
            vacancy.save(update_fields=['is_active', 'updated_at'])
            return {'status': 'archived', 'message': f'Вакансия {vacancy_id} архивирована'}
        
        # Парсим и обновляем
        parsed = parser.parse_vacancy(vacancy_data)
        if parsed:
            new_data = {
                'title': parsed.title,
                'description': parsed.description,
                'requirements': parsed.requirements,
                'responsibilities': parsed.responsibilities,
                'salary_from': parsed.salary_from,
                'salary_to': parsed.salary_to,
                'key_skills': parsed.key_skills,
            }
            
            if vacancy.has_changes(new_data):
                vacancy.create_version(new_data)
                for field, value in new_data.items():
                    setattr(vacancy, field, value)
                vacancy.save()
                return {'status': 'updated', 'message': f'Вакансия {vacancy_id} обновлена'}
            
            return {'status': 'no_changes', 'message': 'Изменений не обнаружено'}
        
        return {'status': 'parse_error', 'message': 'Ошибка парсинга данных'}
        
    except Exception as exc:
        logger.error('Ошибка при обновлении вакансии %s', vacancy_id, exc_info=True)
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=7200,
    time_limit=7500,
)
def parse_vacancies_by_time_period_parallel(
    self,
    date_from: str,
    date_to: str,
    keywords: Optional[List[str]] = None,
    area: int = 113,
    segment_days: int = 2,
    segments_count: int = 10,
    max_workers: int = 3,
    concurrent_queries: int = 1,
    api_delay: float = 0.5,
    show_sample: int = 5
):
    """
    МАСТЕР Celery-задача для распределенного парсинга вакансий.

    Эта задача РАЗБИВАЕТ работу на подзадачи и распределяет их между worker'ами:
    1. Разбивает период на сегменты по времени
    2. Создает подзадачи для каждого поискового запроса
    3. Каждая подзадача обрабатывается отдельным worker'ом
    4. Агрегирует результаты всех подзадач

    Args:
        date_from (str): Дата начала периода (YYYY-MM-DD)
        date_to (str): Дата окончания периода (YYYY-MM-DD)
        keywords (List[str]): Список ключевых слов для поиска
        area (int): ID региона (113 = Россия)
        segment_days (int): Длительность сегмента в днях
        segments_count (int): Максимальное количество сегментов
        max_workers (int): Потоков на одного worker'а
        concurrent_queries (int): Одновременных запросов (для совместимости)
        api_delay (float): Задержка между API запросами
        show_sample (int): Количество примеров в выводе

    Returns:
        dict: Агрегированная статистика от всех подзадач
    """
    # parse_single_query_segment_task определена ниже в этом же файле

    start_time = time.time()
    logger.info('МАСТЕР ЗАДАЧА: Запуск распределенного парсинга')
    logger.info('='*100)
    logger.info(f'Период: {date_from} - {date_to}')
    logger.info(f'Запросов: {len(keywords) if keywords else "автогенерация"}')
    logger.info(f'Конфигурация: workers={max_workers}, delay={api_delay}')
    logger.info('='*100)

    if not keywords:
        # Автогенерация запросов
        if _skill_map_installed():
            from .utils.technology_search_generator import TechnologySearchGenerator
            generator = TechnologySearchGenerator()
            generator.load_technologies(limit=20, include_aliases=True)
            keywords = generator.generate_search_queries(use_aliases=True, max_queries=10)
        else:
            keywords = ["Python", "JavaScript", "Java", "C++", "PHP", "C#"]

    # Убеждаемся, что keywords - это список
    if not keywords:
        keywords = []

    # Создаем подзадачи для каждого ключевого слова с ограничением параллельности
    sub_tasks = []
    batch_size = 50  # Ограничение количества одновременно отправляемых задач
    batch_delay = 1.0  # Задержка между батчами в секундах

    for i, keyword in enumerate(keywords):
        task = parse_single_query_segment_task.delay(  # type: ignore[misc]
            keyword=keyword,
            date_from=date_from,
            date_to=date_to,
            area=area,
            segment_days=segment_days,
            segments_count=segments_count,
            max_workers=max_workers,
            api_delay=api_delay,
            show_sample=show_sample
        )
        sub_tasks.append((keyword, task))
        logger.info(f'Отправлена подзадача для: "{keyword}" (task_id: {task.id})')

        # Задержка между батчами для предотвращения перегрузки
        if (i + 1) % batch_size == 0 and i + 1 < len(keywords):
            logger.info(f'Пауза {batch_delay} сек после отправки {batch_size} задач...')
            time.sleep(batch_delay)

    # В Celery нельзя блокировать задачу ожиданием других задач!
    # Вместо этого возвращаем информацию о запущенных подзадачах
    logger.info(f'Отправлено {len(sub_tasks)} подзадач для параллельной обработки')

    sub_task_info = [{'keyword': keyword, 'task_id': str(task.id)} for keyword, task in sub_tasks]

    # Возвращаем информацию без блокировки
    total_stats = {
        'processed': 0,  # Будет подсчитано позже
        'saved': 0,
        'updated': 0,
        'unchanged': 0,
        'errors': 0,
        'queries_sent': len(sub_tasks),
        'sub_tasks': sub_task_info,
        'note': 'Результаты доступны в Flower или через отдельный запрос агрегации'
    }

    elapsed_time = time.time() - start_time
    logger.info('='*100)
    logger.info('МАСТЕР ЗАДАЧА: ПОДЗАДАЧИ ОТПРАВЛЕНЫ')
    logger.info(f'Отправлено задач: {len(sub_tasks)}')
    logger.info(f'Время на подготовку: {elapsed_time:.1f} сек')
    logger.info(f'Производительность: {len(keywords) / elapsed_time:.1f} задач/сек')
    logger.info('Мониторьте выполнение через Flower: http://localhost:5555')
    logger.info('='*100)

    return {
        'mode': 'distributed_parallel',
        'status': 'tasks_dispatched',  # Задачи отправлены, но не завершены
        'master_task_id': self.request.id,
        'sub_tasks_count': len(sub_tasks),
        'date_from': date_from,
        'date_to': date_to,
        'keywords': keywords,
        'config': {
            'segment_days': segment_days,
            'segments_count': segments_count,
            'max_workers': max_workers,
            'api_delay': api_delay
        },
        'total_statistics': total_stats,
        'performance': {
            'elapsed_time': elapsed_time,
            'tasks_dispatched_per_second': len(keywords) / elapsed_time if elapsed_time > 0 else 0
        },
        'sub_tasks': sub_task_info,
        'monitoring': {
            'flower_url': 'http://localhost:5555',
            'note': 'Мониторьте выполнение подзадач через Flower'
        }
    }


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    soft_time_limit=3600,
    time_limit=3900,
)
def parse_single_query_segment_task(
    self,
    keyword: str,
    date_from: str,
    date_to: str,
    area: int = 113,
    segment_days: int = 2,
    segments_count: int = 10,
    max_workers: int = 3,
    api_delay: float = 0.5,
    show_sample: int = 5
):
    """
    ПОДЗАДАЧА: Парсинг одного ключевого слова с сегментацией по времени.

    Выполняет полную логику парсинга для одного поискового запроса
    с внутренней многопоточной обработкой сегментов.
    """
    import time as time_module
    start_time = time_module.time()  # Запоминаем время начала
    logger.info(f'ПОДЗАДАЧА: Обработка "{keyword}" за период {date_from}-{date_to}')

    try:
        # Инициализация (здесь должна быть логика из management команды)
        parser = HeadHunterParser()

        params = {
            'area': area,
            'date_from': date_from,
            'date_to': date_to,
            'segment_days': segment_days,
            'segments_count': segments_count,
            'show_sample': show_sample,
            'max_workers': max_workers,
            'api_delay': api_delay
        }

        # Реальная логика сбора и обработки сегментов
        segments_data = _collect_segments_celery(parser, keyword, params)

        # Инициализация статистики
        query_stats = {
            'processed': 0,
            'saved': 0,
            'updated': 0,
            'unchanged': 0,
            'errors': 0,
            'samples': []
        }

        # Обработка сегментов
        _process_segments_parallel_celery(segments_data, keyword, params, query_stats)

        elapsed = time_module.time() - start_time
        logger.info(f'ПОДЗАДАЧА "{keyword}" завершена: {query_stats["processed"]} вакансий за {elapsed:.1f} сек')

        return {
            'keyword': keyword,
            'task_id': self.request.id,
            'date_from': date_from,
            'date_to': date_to,
            'statistics': query_stats,
            'segments_processed': len(segments_data),
            'performance': {
                'elapsed_time': time_module.time() - start_time,
                'vacancies_per_second': query_stats['processed'] / max(time_module.time() - start_time, 0.001) if query_stats['processed'] > 0 else 0
            }
        }

    except Exception as exc:
        logger.error(f'Ошибка в подзадаче "{keyword}": {exc}', exc_info=True)
        raise self.retry(exc=exc)


# Вспомогательные функции для Celery задач
def _collect_segments_generator_celery(parser: HeadHunterParser, search_text: str, params: Dict[str, Any]):
    """Генератор сегментов для Celery задачи"""
    # Параметры сегментации
    segment_days = params['segment_days']
    segments_count = params['segments_count']
    area = params['area']
    date_from = params['date_from']
    date_to = params['date_to']
    api_delay = params['api_delay']

    # Преобразование строковых дат в объекты date
    start_date = datetime.strptime(date_from, '%Y-%m-%d').date()
    end_date = datetime.strptime(date_to, '%Y-%m-%d').date()

    # Проверка корректности диапазона
    if start_date >= end_date:
        logger.warning(f'Некорректный диапазон дат: {date_from} - {date_to}')
        return

    # Расчет общего периода в днях
    total_days = (end_date - start_date).days + 1

    # Автоматический расчет размера сегментов
    if segments_count <= 0:
        # Автоматический расчет: примерно по segment_days дней на сегмент
        segments_count = max(1, (total_days + segment_days - 1) // segment_days)
    else:
        # Корректировка размера сегментов под желаемое количество
        segment_days = max(1, total_days // segments_count)

    logger.info(f'Сегментация: {total_days} дней, {segments_count} сегментов по {segment_days} дней')

    # Генерация сегментов
    current_date = start_date
    segment_index = 0

    while current_date <= end_date and segment_index < segments_count:
        # Расчет конца сегмента
        segment_end = min(current_date + timedelta(days=segment_days - 1), end_date)

        # Получение количества вакансий для сегмента
        try:
            vacancies_count = _get_vacancies_count_celery(
                parser=parser,
                search_text=search_text,
                area=area,
                segment_start=current_date,
                segment_end=segment_end,
                api_delay=api_delay
            )

            segment_data = {
                'index': segment_index,
                'start': current_date.strftime('%Y-%m-%d'),
                'end': segment_end.strftime('%Y-%m-%d'),
                'vacancies_count': vacancies_count,
                'start_date': current_date,
                'end_date': segment_end
            }

            logger.info(f'Сегмент {segment_index}: {current_date} - {segment_end}, вакансий: {vacancies_count}')
            yield segment_data

        except Exception as e:
            logger.error(f'Ошибка при обработке сегмента {segment_index}: {e}')
            # Продолжаем с пустым сегментом
            yield {
                'index': segment_index,
                'start': current_date.strftime('%Y-%m-%d'),
                'end': segment_end.strftime('%Y-%m-%d'),
                'vacancies_count': 0,
                'start_date': current_date,
                'end_date': segment_end
            }

        # Переход к следующему сегменту
        current_date = segment_end + timedelta(days=1)
        segment_index += 1


def _collect_segments_celery(parser: HeadHunterParser, search_text: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Собирает все сегменты для Celery задачи"""
    return list(_collect_segments_generator_celery(parser, search_text, params))


def _get_vacancies_count_celery(
    parser: HeadHunterParser,
    search_text: str,
    area: int,
    segment_start: date,
    segment_end: date,
    api_delay: float = 0.5
) -> int:
    """Получает количество найденных вакансий для диапазона дат"""
    try:
        # Форматируем даты
        date_from_str = segment_start.strftime('%Y-%m-%d')
        date_to_str = segment_end.strftime('%Y-%m-%d')

        # Делаем запрос для получения количества
        result = parser.search_vacancies(
            text=search_text,
            area=area,
            per_page=1,  # Минимум для получения количества
            page=0,
            date_from=date_from_str,
            date_to=date_to_str
        )

        if result and 'found' in result:
            return result['found']
        else:
            logger.warning(f'Не удалось получить количество вакансий для {search_text}')
            return 0

    except Exception as e:
        logger.error(f'Ошибка при получении количества вакансий: {e}')
        return 0


def _process_segments_parallel_celery(all_segments, search_text, params, query_stats):
    """Параллельная обработка сегментов для Celery"""
    max_workers = params.get('max_workers', 3)
    api_delay = params.get('api_delay', 0.5)

    if max_workers <= 1 or len(all_segments) <= 1:
        # Последовательная обработка
        for seg_idx, segment in enumerate(all_segments, start=1):
            _process_single_segment_celery(
                segment=segment,
                seg_idx=seg_idx,
                search_text=search_text,
                params=params,
                query_stats=query_stats
            )
        return

    logger.info(f'Параллельная обработка {len(all_segments)} сегментов ({max_workers} потоков)')

    # Параллельная обработка с ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Подготовка задач
        future_to_segment = {}
        for seg_idx, segment in enumerate(all_segments, start=1):
            future = executor.submit(
                _process_single_segment_celery,
                segment=segment,
                seg_idx=seg_idx,
                search_text=search_text,
                params=params,
                query_stats=query_stats
            )
            future_to_segment[future] = (seg_idx, segment)

        # Сбор результатов
        for future in as_completed(future_to_segment):
            seg_idx, segment = future_to_segment[future]
            try:
                result = future.result()
                if result:
                    # Агрегация статистики
                    query_stats['processed'] += result.get('processed', 0)
                    query_stats['saved'] += result.get('saved', 0)
                    query_stats['updated'] += result.get('updated', 0)
                    query_stats['unchanged'] += result.get('unchanged', 0)
                    query_stats['errors'] += result.get('errors', 0)

                    # Добавление примеров
                    if result.get('samples'):
                        query_stats['samples'].extend(result['samples'])

            except Exception as e:
                logger.error(f'Ошибка в сегменте {seg_idx}: {e}')
                query_stats['errors'] += 1


def _process_single_segment_celery(segment: Dict[str, Any], seg_idx: int,
                                 search_text: str, params: Dict[str, Any],
                                 query_stats: Dict[str, Any]) -> Dict[str, Any]:
    """Обработка одного сегмента для Celery"""
    try:
        # Создаем новый парсер для сегмента
        parser = HeadHunterParser()
        area = params['area']
        api_delay = params.get('api_delay', 0.5)

        # Получаем данные сегмента
        start_date = segment['start_date']
        end_date = segment['end_date']

        # Получаем данные вакансий для сегмента
        vacancies_data = _fetch_segment_vacancies_data_celery(
            parser=parser,
            search_text=search_text,
            area=area,
            segment_start=start_date,
            segment_end=end_date,
            api_delay=api_delay
        )

        # Сохраняем вакансии в БД
        stats = _save_vacancies_batch_celery(vacancies_data, search_text)

        # Формируем примеры для статистики
        samples = []
        if vacancies_data:
            for item in vacancies_data[:5]:  # Первые 5 вакансий как примеры
                samples.append({
                    'id': item.get('id', ''),
                    'title': item.get('name', ''),
                    'company': item.get('employer', {}).get('name', '') if item.get('employer') else ''
                })

        return {
            'processed': len(vacancies_data),
            'saved': stats['saved'],
            'updated': stats['updated'],
            'unchanged': stats['unchanged'],
            'errors': stats['errors'],
            'samples': samples
        }

    except Exception as e:
        logger.error(f'Критическая ошибка в сегменте {seg_idx}: {e}')
        return {
            'processed': 0,
            'saved': 0,
            'updated': 0,
            'unchanged': 0,
            'errors': 1,
            'samples': []
        }


def _fetch_segment_vacancies_data_celery(parser: HeadHunterParser, search_text: str,
                                       area: int, segment_start: date, segment_end: date,
                                       api_delay: float = 0.5) -> List[Dict[str, Any]]:
    """Получение данных вакансий для сегмента"""
    vacancies_data = []

    try:
        date_from_str = segment_start.strftime('%Y-%m-%d')
        date_to_str = segment_end.strftime('%Y-%m-%d')

        # Получаем все вакансии из сегмента
        page = 0
        per_page = 100  # Максимум для API

        while True:
            result = parser.search_vacancies(
                text=search_text,
                area=area,
                per_page=per_page,
                page=page,
                date_from=date_from_str,
                date_to=date_to_str
            )

            if not result or 'items' not in result:
                break

            items = result['items']
            if not items:
                break

            # Получаем детальную информацию по каждой вакансии
            for item in items:
                vacancy_id = item.get('id')
                if vacancy_id:
                    vacancy_details = parser.get_vacancy_details(vacancy_id)
                    if vacancy_details:
                        vacancies_data.append(vacancy_details)

                        # Задержка между запросами
                        if api_delay > 0:
                            time.sleep(api_delay)

            page += 1

            # Проверка на последнюю страницу
            if len(items) < per_page:
                break

    except Exception as e:
        logger.error(f'Ошибка при получении данных сегмента: {e}')

    return vacancies_data


def _save_vacancies_batch_celery(vacancies_data: List[Dict[str, Any]], search_text: str) -> Dict[str, int]:
    """Сохранение пакета вакансий в БД"""
    stats = {'saved': 0, 'updated': 0, 'unchanged': 0, 'errors': 0}

    for vacancy_data in vacancies_data:
        vacancy_id: Optional[str] = None
        try:
            vacancy_id = vacancy_data.get('id')
            if not vacancy_id:
                continue

            # Поиск существующей вакансии
            vacancy, created = Vacancy.objects.get_or_create(  # type: ignore[attr-defined]
                hh_id=str(vacancy_id),
                defaults={
                    'title': vacancy_data.get('name', ''),
                    'company_name': vacancy_data.get('employer', {}).get('name', '') if vacancy_data.get('employer') else '',
                    'salary_from': vacancy_data.get('salary', {}).get('from'),
                    'salary_to': vacancy_data.get('salary', {}).get('to'),
                    'salary_currency': vacancy_data.get('salary', {}).get('currency') if vacancy_data.get('salary') else None,
                    'salary_gross': vacancy_data.get('salary', {}).get('gross') if vacancy_data.get('salary') else None,
                    'city': vacancy_data.get('area', {}).get('name') if vacancy_data.get('area') else None,
                    'description': vacancy_data.get('description', ''),
                    'requirements': vacancy_data.get('snippet', {}).get('requirement') if vacancy_data.get('snippet') else None,
                    'url': vacancy_data.get('alternate_url', ''),
                    'published_at': vacancy_data.get('published_at'),
                }
            )

            if created:
                stats['saved'] += 1
            else:
                # Проверка на изменения (упрощенная версия)
                # В реальной реализации нужно сравнивать все поля
                stats['unchanged'] += 1

        except Exception as e:
            vacancy_id_str = str(vacancy_id) if vacancy_id else 'unknown'
            logger.error(f'Ошибка при сохранении вакансии {vacancy_id_str}: {e}')
            stats['errors'] += 1

    return stats


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=18000,
    time_limit=21600,
)
def parse_vacancies_by_professional_roles(
    self,
    area: int = 113,
    pages: int = 3,
    delay: float = 2.0,
    get_details: bool = True,
    max_concurrent_roles: int = 5,
    batch_size: int = 10,
    force_refresh_roles: bool = False,
    no_delays: bool = False,
    parallel_workers: int = 1,  # Количество параллельных задач для ролей
    incremental: bool = False,  # Инкрементальный парсинг
    skip_existing_roles: bool = False,  # Пропускать уже парсированные роли
    # Дополнительные параметры фильтрации из API HH
    experience: Optional[str] = None,
    employment: Optional[str] = None,
    schedule: Optional[str] = None,
    only_with_salary: bool = False,
    period: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    salary_from: Optional[int] = None,
    salary_to: Optional[int] = None
):
    """
    Celery-задача для парсинга вакансий по профессиональным ролям IT.

    Получает актуальный список IT ролей и парсит вакансии по каждой роли
    с использованием параметра professional_role в API.

    Args:
        area (int): ID региона для поиска (по умолчанию Россия)
        pages (int): Количество страниц для каждой роли
        delay (float): Задержка между запросами
        get_details (bool): Получать ли детальную информацию о вакансиях
        max_concurrent_roles (int): Максимум параллельных ролей
        batch_size (int): Размер батча для обработки
        force_refresh_roles (bool): Принудительно обновить список ролей из API

    Returns:
        dict: Статистика парсинга
    """
    from .utils.professional_roles_config import ProfessionalRolesManager

    logger.info('Запуск парсинга вакансий по профессиональным ролям IT')
    logger.info(f'Параметры: area={area}, pages={pages}, delay={delay}, get_details={get_details}, parallel_workers={parallel_workers}')

    try:
        # Инициализируем менеджер ролей
        roles_manager = ProfessionalRolesManager()

        # Получаем список IT ролей
        it_roles = roles_manager.get_it_roles(force_refresh=force_refresh_roles)

        if not it_roles:
            return {
                'mode': 'by_professional_roles',
                'error': 'Не удалось получить список IT ролей',
                'total_roles': 0,
                'parsed_roles': 0,
                'total_vacancies': 0,
                'new_vacancies': 0
            }

        logger.info(f'Будет обработано {len(it_roles)} IT ролей')

        # ФИЛЬТРАЦИЯ РОЛЕЙ для оптимизации
        if skip_existing_roles or incremental:
            filtered_roles = _filter_roles_for_parsing(it_roles, skip_existing_roles, incremental)
            if len(filtered_roles) != len(it_roles):
                logger.info(f'После фильтрации: {len(filtered_roles)} из {len(it_roles)} ролей')
                it_roles = filtered_roles

        # ДОБАВЛЯЕМ ФИЛЬТР ПО ДАТЕ для инкрементального парсинга
        date_from_filter = None
        if incremental:
            from django.db.models import Max
            try:
                latest_vacancy = Vacancy.objects.aggregate(latest=Max('published_at'))['latest']
                if latest_vacancy:
                    # Парсим вакансии начиная с дня после последней
                    date_from_filter = (latest_vacancy - timedelta(days=1)).strftime('%Y-%m-%d')
                    logger.info(f'Инкрементальный режим: парсинг с даты {date_from_filter}')
            except Exception as e:
                logger.warning(f'Не удалось определить дату последней вакансии: {e}')

        # РАСПАРАЛЛЕЛИВАНИЕ: если указано больше 1 worker'а
        if parallel_workers > 1:
            parallel_workers = max(1, min(parallel_workers, len(it_roles)))

            # Корректируем delay для параллельной работы
            if not no_delays:
                original_delay = delay
                # При параллельной работе увеличиваем delay для снижения нагрузки
                delay = max(delay, 0.5) * (0.8 + parallel_workers * 0.2)  # Увеличиваем на 20-60%
                logger.info(
                    f'[ADJUST] Скорректирован delay для {parallel_workers} воркеров: '
                    f'{original_delay:.2f} → {delay:.2f} сек'
                )

            logger.info(f'Запуск РАСПАРАЛЛЕЛИВАНИЯ: {parallel_workers} параллельных задач')

            # Собираем фрагменты ролей и строим подпроцессы Celery
            chord_header = _build_parallel_role_signatures(
                it_roles=it_roles,
                parallel_workers=parallel_workers,
                area=area,
                pages=pages,
                delay=delay,
                get_details=get_details,
                max_concurrent_roles=max_concurrent_roles,
                batch_size=batch_size,
                no_delays=no_delays,
                experience=experience,
                employment=employment,
                schedule=schedule,
                only_with_salary=only_with_salary,
                period=period,
                date_from=date_from,
                date_to=date_to,
                salary_from=salary_from,
                salary_to=salary_to
            )
            
            # Логируем распределение ролей для отладки
            if chord_header:
                roles_per_worker = len(it_roles) // parallel_workers
                remainder = len(it_roles) % parallel_workers
                for worker_idx in range(parallel_workers):
                    worker_roles_count = roles_per_worker + (1 if worker_idx < remainder else 0)
                    logger.info(
                        f'[DISTRIBUTION] Worker {worker_idx + 1} получит {worker_roles_count} ролей '
                        f'(из {len(it_roles)} всего)'
                    )

            if not chord_header:
                return {
                    'mode': 'by_professional_roles_parallel',
                    'error': 'Не удалось подготовить задачи для парсинга ролей',
                    'total_roles': len(it_roles),
                    'parsed_roles': 0
                }

            finalize_signature = finalize_role_fragments.s(
                total_roles=len(it_roles),
                area=area,
                pages=pages,
                get_details=get_details,
                parallel_workers=parallel_workers
            ).set(queue='headhunter')

            # Делегируем выполнение в Celery-chord, чтобы результаты агрегировались автоматически
            return self.replace(chord(chord_header)(finalize_signature))

        # Создаем парсер
        parser = HeadHunterParser(
            metrics=ParsingMetrics(),
            use_jitter=True,
            rotate_user_agent=True,
            use_proxy=False
        )

        total_vacancies = 0
        total_new_vacancies = 0
        total_updated_vacancies = 0
        parsed_roles = 0
        total_roles = len(it_roles)
        task_start_time = time.time()  # Время начала всей задачи

        # Обрабатываем роли батчами для контроля нагрузки
        # Если batch_size = 0 или >= количества ролей, обрабатываем все сразу
        effective_batch_size = batch_size if batch_size > 0 and batch_size < len(it_roles) else len(it_roles)

        for i in range(0, len(it_roles), effective_batch_size):
            batch_roles = it_roles[i:i + effective_batch_size]
            batch_num = i//effective_batch_size + 1
            total_batches = (len(it_roles) + effective_batch_size - 1)//effective_batch_size

            if total_batches > 1:
                logger.info(f'Обработка батча {batch_num}/{total_batches} ({len(batch_roles)} ролей)')
            else:
                logger.info(f'Обработка всех {len(it_roles)} ролей за один проход')

            # Для каждой роли в батче выполняем поиск
            for role in batch_roles:
                role_start_time = time.time()  # Время начала обработки роли
                try:
                    logger.info(f'Парсинг роли: {role.name} (ID: {role.id})')

                    role_vacancies = 0
                    role_new_vacancies = 0
                    role_updated_vacancies = 0
                    role_errors = 0

                    # Оптимизированные параметры для максимального покрытия (лимит 2000 вакансий)
                    # Если pages <= 20: используем 100 вакансий на страницу (20 × 100 = 2000)
                    # Если pages > 20: используем 10 вакансий на страницу (200 × 10 = 2000)
                    if pages <= 20:
                        per_page_limit = 100  # 100 вакансий на страницу (лимит API HH)
                        max_pages_per_role = 20  # Максимум 20 страниц
                    else:
                        per_page_limit = 10   # 10 вакансий на страницу
                        max_pages_per_role = 200  # Максимум 200 страниц (200 × 10 = 2000)
                    
                    actual_pages = min(pages if pages > 0 else max_pages_per_role, max_pages_per_role)

                    # Сначала получаем общее количество вакансий и страниц для роли
                    logger.info(f'[INFO] Получение информации о количестве вакансий для роли {role.name} (ID: {role.id})...')
                    info_params = {
                        'professional_role': role.id,
                        'area': area,
                        'per_page': 1,  # Минимум для получения метаданных
                        'page': 0
                    }
                    logger.debug(f'[DEBUG] Параметры информационного запроса: {info_params}')
                    
                    # Добавляем дополнительные параметры фильтрации для информационного запроса
                    if experience:
                        info_params['experience'] = experience
                    if employment:
                        info_params['employment'] = employment
                    if schedule:
                        info_params['schedule'] = schedule
                    if only_with_salary:
                        info_params['only_with_salary'] = only_with_salary
                    if period:
                        info_params['period'] = period
                    if date_from:
                        info_params['date_from'] = date_from
                    if date_to:
                        info_params['date_to'] = date_to
                    if salary_from or salary_to:
                        info_params['currency'] = 'RUR'
                        if salary_from:
                            info_params['salary_from'] = salary_from
                        if salary_to:
                            info_params['salary_to'] = salary_to
                    
                    try:
                        info_result = parser.search_vacancies(**info_params)
                    except Exception as e:
                        logger.warning(f'Роль {role.name}: ошибка при получении информации о количестве вакансий: {e}, используем запрошенное количество страниц')
                        info_result = None
                    
                    if not info_result or 'found' not in info_result:
                        logger.warning(f'Роль {role.name}: не удалось получить информацию о количестве вакансий, используем запрошенное количество страниц')
                        total_found = 0
                        total_pages_api = actual_pages
                    else:
                        total_found = info_result.get('found', 0)
                        # ВАЖНО: API возвращает pages для per_page=1, нужно пересчитать для нашего per_page_limit
                        pages_api_info = info_result.get('pages', 0)  # Страниц при per_page=1
                        
                        # Пересчитываем количество страниц для нашего per_page_limit
                        if total_found > 0 and per_page_limit > 0:
                            total_pages_api = (total_found + per_page_limit - 1) // per_page_limit  # Округление вверх
                        else:
                            total_pages_api = 0
                        
                        logger.debug(f'Роль {role.name}: API вернул found={total_found}, pages (при per_page=1)={pages_api_info}, пересчитано для per_page={per_page_limit}: {total_pages_api} страниц')
                        
                        # Рассчитываем оптимальное количество страниц на основе лимита 2000 вакансий
                        max_vacancies_limit = 2000
                        if total_found > 0:
                            # Рассчитываем количество страниц для достижения лимита
                            pages_needed_for_limit = (max_vacancies_limit + per_page_limit - 1) // per_page_limit  # Округление вверх
                            
                            # Берем минимум из: нужного для лимита, доступного в API, запрошенного
                            pages_needed = min(
                                pages_needed_for_limit,
                                total_pages_api,
                                actual_pages
                            )
                            
                            actual_pages = pages_needed
                            logger.info(f'Роль {role.name}: найдено {total_found} вакансий, доступно {total_pages_api} страниц (при {per_page_limit} вакансий/страницу), будем парсить {actual_pages} страниц (лимит: {max_vacancies_limit} вакансий)')
                        else:
                            logger.info(f'Роль {role.name}: вакансий не найдено, пропускаем')
                            continue

                    logger.info(f'Начинаем парсинг роли {role.name} (ID: {role.id}): {actual_pages} страниц по {per_page_limit} вакансий')
                    total_expected = actual_pages * per_page_limit  # Ожидаемое количество вакансий

                    # Парсим страницы с улучшенным логированием
                    for page in range(actual_pages):
                        try:
                            # Поиск вакансий по профессиональной роли с оптимизированными параметрами
                            search_params = {
                                'professional_role': role.id,
                                'area': area,
                                'per_page': per_page_limit,
                                'page': page
                            }

                            # Добавляем дополнительные параметры фильтрации
                            if experience:
                                search_params['experience'] = experience
                            if employment:
                                search_params['employment'] = employment
                            if schedule:
                                search_params['schedule'] = schedule
                            if only_with_salary:
                                search_params['only_with_salary'] = only_with_salary
                            if period:
                                search_params['period'] = period
                            if date_from:
                                search_params['date_from'] = date_from
                            if date_to:
                                search_params['date_to'] = date_to
                            if salary_from or salary_to:
                                # Для зарплаты используем currency=RUR по умолчанию
                                search_params['currency'] = 'RUR'
                                if salary_from:
                                    search_params['salary_from'] = salary_from
                                if salary_to:
                                    search_params['salary_to'] = salary_to

                            search_result = parser.search_vacancies(**search_params)

                            if not search_result or 'items' not in search_result:
                                logger.info(f'Роль {role.name}: страница {page + 1}/{actual_pages} - нет результатов, завершаем парсинг роли')
                                break

                            page_vacancies = search_result['items']
                            page_vacancy_count = len(page_vacancies)
                            role_vacancies += page_vacancy_count

                            # Прогресс для роли
                            progress_percent = ((page + 1) / actual_pages) * 100
                            logger.info(f'Роль {role.name}: страница {page + 1}/{actual_pages} ({progress_percent:.1f}%) - найдено {page_vacancy_count} вакансий (всего: {role_vacancies})')

                            # Обрабатываем каждую вакансию на странице (пакетно для ускорения деталей)
                            page_new = 0
                            page_updated = 0
                            page_errors = 0

                            vacancy_ids: List[str] = []
                            new_vacancies_buffer: Dict[str, Vacancy] = {}
                            existing_vacancies_buffer: Dict[str, Vacancy] = {}
                            vacancy_snippets: Dict[str, Dict[str, Any]] = {}

                            for vacancy_data in page_vacancies:
                                vacancy_id = str(vacancy_data.get('id')) if vacancy_data.get('id') else ''
                                if not vacancy_id:
                                    logger.warning(f'Пропускаем вакансию без ID в роли {role.name}')
                                    page_errors += 1
                                    continue

                                vacancy_ids.append(vacancy_id)
                                vacancy_snippets[vacancy_id] = vacancy_data

                                existing_vacancy = Vacancy.objects.filter(hh_id=vacancy_id).first()
                                if existing_vacancy:
                                    existing_vacancies_buffer[vacancy_id] = existing_vacancy
                                else:
                                    vacancy_obj = _create_vacancy_from_api_data(vacancy_data, role.id, role.name)
                                    new_vacancies_buffer[vacancy_id] = vacancy_obj

                            # Загружаем детали пачками, чтобы минимизировать суммарную задержку
                            details_map: Dict[str, Any] = {}
                            if get_details and vacancy_ids:
                                detail_chunk_size = 25  # как в технологиях: небольшие пачки, но без больших пауз
                                for i in range(0, len(vacancy_ids), detail_chunk_size):
                                    chunk_ids = vacancy_ids[i:i + detail_chunk_size]
                                    try:
                                        chunk_details = asyncio.run(_fetch_vacancy_details_batch_async(
                                            parser, chunk_ids, '[Roles] '
                                        ))
                                        if chunk_details:
                                            details_map.update(chunk_details)
                                    except Exception as e:  # noqa: BLE001
                                        logger.warning(f'Ошибка при пакетной загрузке деталей ролей: {e}')
                                    # Минимальная пауза между пачками, только если задержки разрешены
                                    if not no_delays and delay > 0 and i + detail_chunk_size < len(vacancy_ids):
                                        time.sleep(min(delay * 0.2, 0.5))

                            # Применяем детали и сохраняем
                            for vacancy_id in vacancy_ids:
                                try:
                                    if vacancy_id in existing_vacancies_buffer:
                                        existing_vacancy = existing_vacancies_buffer[vacancy_id]
                                        details = details_map.get(vacancy_id)
                                        updated = False
                                        if details:
                                            details = _merge_snippet_into_details(details, vacancy_snippets.get(vacancy_id, {}))
                                            updated = _update_vacancy_from_api_data(existing_vacancy, details)
                                        existing_vacancy.updated_at = timezone.now()
                                        existing_vacancy.save()
                                        if updated:
                                            page_updated += 1
                                            role_updated_vacancies += 1
                                    else:
                                        vacancy_obj = new_vacancies_buffer.get(vacancy_id)
                                        if not vacancy_obj:
                                            continue
                                        details = details_map.get(vacancy_id)
                                        if details:
                                            details = _merge_snippet_into_details(details, vacancy_snippets.get(vacancy_id, {}))
                                            _update_vacancy_from_api_data(vacancy_obj, details)
                                        vacancy_obj.save()
                                        page_new += 1
                                        role_new_vacancies += 1
                                        total_new_vacancies += 1

                                except Exception as e:  # noqa: BLE001
                                    logger.error(f'Ошибка обработки вакансии {vacancy_id} для роли {role.name}: {e}')
                                    page_errors += 1
                                    role_errors += 1
                                    continue

                            # Логируем результаты обработки страницы
                            logger.info(f'Роль {role.name}: страница {page + 1} обработана - новых: {page_new}, обновлено: {page_updated}, ошибок: {page_errors}')

                        except Exception as e:
                            logger.error(f'Ошибка при парсинге страницы {page + 1} для роли {role.name}: {e}')
                            role_errors += 1
                            continue

                        # Задержка между страницами для обхода rate limiting
                        if not no_delays and page < actual_pages - 1:
                            time.sleep(delay)

                    # Логируем итоги парсинга роли
                    logger.info(f'Роль {role.name} завершена: обработано {role_vacancies} вакансий, '
                               f'новых: {role_new_vacancies}, обновлено: {role_updated_vacancies}, ошибок: {role_errors}')

                    total_vacancies += role_vacancies

                    # Общий прогресс
                    parsed_roles += 1
                    overall_progress = (parsed_roles / total_roles) * 100

                    # Расчет примерного времени
                    elapsed_time = time.time() - task_start_time
                    avg_time_per_role = elapsed_time / parsed_roles
                    remaining_roles = total_roles - parsed_roles
                    estimated_remaining = remaining_roles * avg_time_per_role

                    logger.info(f'ПРОГРЕСС: {parsed_roles}/{total_roles} ролей ({overall_progress:.1f}%) завершено')
                    logger.info(f'Статистика: вакансий={total_vacancies}, новых={total_new_vacancies}, обновлено={total_updated_vacancies}')
                    if remaining_roles > 0:
                        logger.info(f'Осталось: {remaining_roles} ролей, ~{estimated_remaining/60:.1f} мин (общее время: {elapsed_time/60:.1f} мин)')
                    total_updated_vacancies += role_updated_vacancies

                except Exception as e:
                    logger.error(f'Ошибка обработки роли {role.name}: {e}')
                    continue

                # Задержка между ролями
                if not no_delays and delay > 0:
                    time.sleep(delay)

            # Дополнительная задержка между батчами (только если батчи включены)
            if not no_delays and effective_batch_size < len(it_roles) and i + effective_batch_size < len(it_roles):
                batch_delay = delay * 2
                logger.info(f'Задержка между батчами: {batch_delay} сек')
                time.sleep(batch_delay)

        total_time = time.time() - task_start_time
        parser.metrics.log_summary()

        chunk_results = [{
            'roles_processed': parsed_roles,
            'total_vacancies': total_vacancies,
            'new_vacancies': total_new_vacancies,
            'updated_vacancies': total_updated_vacancies,
            'total_time_minutes': total_time / 60,
        }]

        result = _aggregate_role_results(
            chunk_results=chunk_results,
            total_roles=len(it_roles),
            area=area,
            pages=pages,
            get_details=get_details,
            mode='by_professional_roles',
            metrics=parser.metrics.to_dict()
        )

        logger.info(f'ПАРСИНГ ЗАВЕРШЕН! Обработано {parsed_roles}/{len(it_roles)} ролей за {total_time/60:.1f} мин')
        logger.info(f'ФИНАЛЬНАЯ СТАТИСТИКА: {total_vacancies} вакансий, {total_new_vacancies} новых, {total_updated_vacancies} обновлено')
        logger.info(f'Производительность: {total_vacancies/total_time:.1f} вакансий/сек, {parsed_roles/total_time*60:.1f} ролей/час')

        return result

    except Exception as e:
        error_msg = f'Критическая ошибка в задаче парсинга по ролям: {str(e)}'
        logger.error(error_msg, exc_info=True)

        return {
            'mode': 'by_professional_roles',
            'error': error_msg,
            'total_roles': 0,
            'parsed_roles': 0,
            'total_vacancies': 0,
            'new_vacancies': 0
        }


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    soft_time_limit=300,
    time_limit=600,
)
def get_professional_roles_task(self):
    """
    Celery-задача для получения списка всех профессиональных ролей с API HeadHunter.

    Returns:
        dict: Словарь с результатами запроса
            - success (bool): Успешность выполнения
            - roles (list): Список ролей или пустой список при ошибке
            - categories_count (int): Количество категорий (если успех)
            - total_roles (int): Общее количество ролей (если успех)
            - error (str): Сообщение об ошибке (если неудача)
    """
    try:
        logger.info('Начало выполнения задачи получения профессиональных ролей')

        target_category_id = _load_target_category_id()
        logger.info('Фильтрация ролей по категории %s (IT)', target_category_id)

        # Создаем парсер
        parser = HeadHunterParser()

        # Получаем роли (ограничиваемся целевой категорией)
        roles = parser.get_professional_roles(category_id=target_category_id)

        if roles is None:
            logger.error('Не удалось получить профессиональные роли - ответ None')
            return {
                'success': False,
                'roles': [],
                'error': 'Не удалось получить данные с API HeadHunter'
            }

        if not roles:
            logger.warning('Получен пустой список профессиональных ролей')
            return {
                'success': False,
                'roles': [],
                'error': 'Получен пустой список ролей'
            }

        # Получаем статистику по категориям
        raw_data = parser._make_request(f"{parser.base_url}/professional_roles")
        categories_count = 1  # По умолчанию 1 категория (IT)
        if raw_data and 'categories' in raw_data:
            # Проверяем, существует ли целевая категория в списке
            categories_count = 1 if any(
                str(category.get('id')) == target_category_id
                for category in raw_data['categories']
            ) else 1  # Если категория не найдена, но роли есть, считаем что категория 1

        total_roles = len(roles)

        logger.info(f'Успешно получено {total_roles} профессиональных ролей из {categories_count} категорий')

        return {
            'success': True,
            'roles': roles,
            'categories_count': categories_count,
            'total_roles': total_roles
        }

    except Exception as e:
        error_msg = f'Ошибка при получении профессиональных ролей: {str(e)}'
        logger.error(error_msg, exc_info=True)

        return {
            'success': False,
            'roles': [],
            'error': error_msg
        }


def _filter_roles_for_parsing(it_roles, skip_existing_roles, incremental):
    """
    Фильтрует роли для оптимизации парсинга.

    Args:
        it_roles: Список всех ролей
        skip_existing_roles: Пропускать роли, парсированные сегодня
        incremental: Использовать инкрементальный режим

    Returns:
        Отфильтрованный список ролей
    """
    if not skip_existing_roles and not incremental:
        return it_roles

    filtered_roles = []

    for role in it_roles:
        should_include = True

        if skip_existing_roles:
            # Проверяем, парсилась ли эта роль сегодня
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            recent_vacancies = Vacancy.objects.filter(
                professional_role=str(role.id),
                created_at__gte=today_start
            ).exists()

            if recent_vacancies:
                logger.debug(f'Пропускаем роль {role.name} - уже парсилась сегодня')
                should_include = False

        if should_include:
            filtered_roles.append(role)

    return filtered_roles


async def _fetch_vacancy_details_batch_async(parser, vacancy_ids, worker_prefix):
    """
    Асинхронно получает детали нескольких вакансий одновременно.
    Возвращает словарь {vacancy_id: details} и статистику ошибок.
    """
    import aiohttp
    import asyncio

    errors_count = 0
    errors_403_count = 0
    last_error = None

    async def fetch_single(vacancy_id):
        nonlocal errors_count, errors_403_count, last_error
        try:
            details = await asyncio.get_event_loop().run_in_executor(
                None, parser.get_vacancy_details, str(vacancy_id)
            )
            return vacancy_id, details, None
        except Exception as e:
            errors_count += 1
            error_msg = str(e).lower()
            if '403' in error_msg or 'forbidden' in error_msg:
                errors_403_count += 1
            last_error = e
            # Логируем только каждую 10-ю ошибку, чтобы не засорять логи
            if errors_count % 10 == 0 or errors_count <= 3:
                logger.warning(f'{worker_prefix}Ошибка получения деталей вакансии {vacancy_id}: {e}')
            return vacancy_id, None, e

    # Создаем задачи для параллельного выполнения
    tasks = [fetch_single(vid) for vid in vacancy_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    details_map = {}
    for result in results:
        if isinstance(result, Exception):
            errors_count += 1
            continue
        if isinstance(result, tuple) and len(result) == 3:
            vacancy_id, details, error = result
            if details:
                details_map[vacancy_id] = details

    # Логируем итоговую статистику
    total = len(vacancy_ids)
    success = len(details_map)
    if errors_count > 0:
        logger.warning(
            f'{worker_prefix}Загрузка деталей завершена: {success}/{total} успешно, '
            f'ошибок: {errors_count} (403: {errors_403_count})'
        )
    else:
        logger.debug(f'{worker_prefix}Загрузка деталей завершена: {success}/{total} успешно')

    return details_map


def _build_parallel_role_signatures(
    it_roles: List[Any],
    parallel_workers: int,
    area: int,
    pages: int,
    delay: float,
    get_details: bool,
    max_concurrent_roles: int,
    batch_size: int,
    no_delays: bool,
    experience: Optional[str] = None,
    employment: Optional[str] = None,
    schedule: Optional[str] = None,
    only_with_salary: bool = False,
    period: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    salary_from: Optional[int] = None,
    salary_to: Optional[int] = None,
) -> List[Any]:
    """
    Формирует список Celery-задач для распараллеленного парсинга ролей.
    """
    if not it_roles:
        return []

    parallel_workers = max(1, min(parallel_workers, len(it_roles)))

    roles_per_worker = len(it_roles) // parallel_workers
    remainder = len(it_roles) % parallel_workers

    headers = []
    start_idx = 0

    for worker_idx in range(parallel_workers):
        worker_roles_count = roles_per_worker + (1 if worker_idx < remainder else 0)
        end_idx = start_idx + worker_roles_count
        worker_roles = it_roles[start_idx:end_idx]
        start_idx = end_idx

        if not worker_roles:
            continue

        headers.append(
            parse_single_role_batch.s(
                [role.id for role in worker_roles],
                area,
                pages,
                delay,
                get_details,
                max_concurrent_roles,
                batch_size,
                no_delays,
                worker_idx + 1,
                experience,
                employment,
                schedule,
                only_with_salary,
                period,
                date_from,
                date_to,
                salary_from,
                salary_to,
            ).set(queue='headhunter')
        )

    return headers


@shared_task(
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    soft_time_limit=900,
    time_limit=1200,
)
def finalize_role_fragments(
    self,
    chunk_results: List[Dict[str, Any]],
    total_roles: int,
    area: int,
    pages: int,
    get_details: bool,
    parallel_workers: int,
):
    """
    Callback-задача для агрегации результатов фрагментарного парсинга ролей.
    """
    logger.info(
        'Агрегация результатов фрагментов ролей: %d фрагментов, %d воркеров',
        len(chunk_results),
        parallel_workers,
    )

    summary = _aggregate_role_results(
        chunk_results=chunk_results,
        total_roles=total_roles,
        area=area,
        pages=pages,
        get_details=get_details,
        mode='by_professional_roles_parallel',
        metrics=None,
        extra={
            'parallel_workers': parallel_workers,
            'chunk_count': len(chunk_results),
        },
    )

    return summary


def _aggregate_role_results(
    chunk_results: List[Dict[str, Any]],
    total_roles: int,
    area: int,
    pages: int,
    get_details: bool,
    mode: str,
    metrics: Optional[Dict[str, Any]] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Агрегирует метрики по фрагментам парсинга ролей.
    """
    parsed_roles = sum(result.get('roles_processed', 0) for result in chunk_results)
    total_vacancies = sum(result.get('total_vacancies', 0) for result in chunk_results)
    new_vacancies = sum(result.get('new_vacancies', 0) for result in chunk_results)
    updated_vacancies = sum(result.get('updated_vacancies', 0) for result in chunk_results)
    total_time_minutes = sum(result.get('total_time_minutes', 0.0) for result in chunk_results)

    summary: Dict[str, Any] = {
        'mode': mode,
        'status': 'completed',
        'total_roles': total_roles,
        'parsed_roles': parsed_roles,
        'total_vacancies': total_vacancies,
        'new_vacancies': new_vacancies,
        'updated_vacancies': updated_vacancies,
        'area': area,
        'pages_per_role': pages,
        'get_details': get_details,
        'fragments': len(chunk_results),
        'total_time_minutes': total_time_minutes,
    }

    if metrics:
        summary['metrics'] = metrics

    if extra:
        summary.update(extra)

    return summary


@shared_task(
    bind=True,
    max_retries=5,        # Увеличиваем количество повторных попыток
    default_retry_delay=60,  # Увеличиваем задержку между попытками
    soft_time_limit=9000,  # 2.5 часа на подзадачу
    time_limit=10800,     # 3 часа максимум
)
def parse_single_role_batch(
    self,
    role_ids: List[str],
    area: int,
    pages: int,
    delay: float,
    get_details: bool,
    max_concurrent_roles: int,
    batch_size: int,
    no_delays: bool,
    worker_id: int,
    experience: Optional[str] = None,
    employment: Optional[str] = None,
    schedule: Optional[str] = None,
    only_with_salary: bool = False,
    period: Optional[int] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    salary_from: Optional[int] = None,
    salary_to: Optional[int] = None,
):
    """
    Подзадача для парсинга батча ролей в параллельном режиме.

    Args:
        role_ids: Список ID ролей для обработки
        worker_id: ID worker'а (для логирования)

    Returns:
        Статистика обработки батча ролей
    """
    from .utils.professional_roles_config import ProfessionalRolesManager

    logger.info(f'[Worker {worker_id}] Начинаем обработку батча из {len(role_ids)} ролей')

    # Добавляем внутреннюю задержку старта для координации воркеров
    if worker_id == 1:
        start_delay = 5  # Первый воркер ждет 5 сек
    elif worker_id == 2:
        start_delay = 30  # Второй воркер ждет 30 сек
    elif worker_id == 3:
        start_delay = 60  # Третий воркер ждет 60 сек
    else:
        start_delay = 60 + (worker_id-3) * 30  # Остальные ждут 90+ сек

    logger.info(f'[Worker {worker_id}] Ожидание {start_delay} сек перед стартом...')
    time.sleep(start_delay)
    logger.info(f'[Worker {worker_id}] Начинаем парсинг после задержки')

    try:
        # Получаем объекты ролей по ID
        roles_manager = ProfessionalRolesManager()
        all_roles = roles_manager.get_it_roles()
        it_roles = [role for role in all_roles if str(role.id) in role_ids]

        if len(it_roles) != len(role_ids):
            logger.warning(f'Worker {worker_id}: Найдено {len(it_roles)} из {len(role_ids)} запрошенных ролей')

        # Запускаем обычную логику парсинга для этого батча
        return _parse_roles_batch(
            it_roles, area, pages, delay, get_details,
            max_concurrent_roles, batch_size, no_delays, worker_id, 1,  # parallel_workers=1 для подзадач
            experience, employment, schedule, only_with_salary,
            period, date_from, date_to, salary_from, salary_to
        )

    except Exception as e:
        logger.error(f'Worker {worker_id}: Критическая ошибка в батче: {e}', exc_info=True)

        # Умная логика повторных попыток
        retry_delay = min(60 * (2 ** self.request.retries), 600)  # Экспоненциальная задержка, макс 10 мин

        # Если это ошибка API (rate limit), увеличиваем задержку
        if '400' in str(e) or 'rate' in str(e).lower() or 'block' in str(e).lower():
            retry_delay = min(retry_delay * 2, 1200)  # Удваиваем задержку для API ошибок, макс 20 мин

        logger.warning(f'Worker {worker_id}: Повторная попытка через {retry_delay} сек (попытка {self.request.retries + 1}/5)')
        raise self.retry(countdown=retry_delay, exc=e)


def _parse_roles_batch(it_roles, area, pages, delay, get_details,
                      max_concurrent_roles, batch_size, no_delays, worker_id=None, parallel_workers=1,
                      experience=None, employment=None, schedule=None, only_with_salary=False,
                      period=None, date_from=None, date_to=None, salary_from=None, salary_to=None):
    """
    Основная логика парсинга батча ролей (выделена в отдельную функцию).
    """
    worker_prefix = f'[Worker {worker_id}] ' if worker_id else ''
    logger.info(f'{worker_prefix}Начат парсинг батча из {len(it_roles)} ролей')

    # Создаем парсер
    parser = HeadHunterParser(
        metrics=ParsingMetrics(),
        use_jitter=True,
        rotate_user_agent=True,
        use_proxy=False
    )

    total_vacancies = 0
    total_new_vacancies = 0
    total_updated_vacancies = 0
    parsed_roles = 0
    total_roles = len(it_roles)
    task_start_time = time.time()

    # Счетчики для защиты от блокировок и статистики ошибок
    consecutive_403_errors = 0
    max_consecutive_403 = 3  # После 3 подряд 403 останавливаем worker
    total_403_errors = 0  # Общее количество 403 ошибок
    total_details_errors = 0  # Ошибки при загрузке деталей
    total_other_errors = 0  # Другие ошибки

    # Обрабатываем роли батчами для контроля нагрузки
    effective_batch_size = batch_size if batch_size > 0 and batch_size < len(it_roles) else len(it_roles)

    for i in range(0, len(it_roles), effective_batch_size):
        batch_roles = it_roles[i:i + effective_batch_size]
        batch_num = i//effective_batch_size + 1
        total_batches = (len(it_roles) + effective_batch_size - 1)//effective_batch_size

        if total_batches > 1:
            logger.info(f'{worker_prefix}Обработка батча {batch_num}/{total_batches} ({len(batch_roles)} ролей)')
        else:
            logger.info(f'{worker_prefix}Обработка всех {len(it_roles)} ролей за один проход')

        # Для каждой роли в батче выполняем поиск
        for role in batch_roles:
            role_start_time = time.time()
            try:
                logger.info(f'{worker_prefix}Парсинг роли: {role.name} (ID: {role.id})')

                role_vacancies = 0
                role_new_vacancies = 0
                role_updated_vacancies = 0
                role_errors = 0

                # Оптимизированные параметры для максимального покрытия (лимит 2000 вакансий)
                # Если pages <= 20: используем 100 вакансий на страницу (20 × 100 = 2000)
                # Если pages > 20: используем 10 вакансий на страницу (200 × 10 = 2000)
                if pages <= 20:
                    per_page_limit = 100  # 100 вакансий на страницу (лимит API HH)
                    max_pages_per_role = 20  # Максимум 20 страниц
                else:
                    per_page_limit = 10   # 10 вакансий на страницу
                    max_pages_per_role = 200  # Максимум 200 страниц (200 × 10 = 2000)
                
                actual_pages = min(pages if pages > 0 else max_pages_per_role, max_pages_per_role)

                # Сначала получаем общее количество вакансий и страниц для роли
                logger.info(f'{worker_prefix}[INFO] Получение информации о количестве вакансий для роли {role.name} (ID: {role.id})...')
                info_params = {
                    'professional_role': role.id,
                    'area': area,
                    'per_page': 1,  # Минимум для получения метаданных
                    'page': 0
                }
                logger.debug(f'{worker_prefix}[DEBUG] Параметры информационного запроса: {info_params}')
                
                try:
                    info_result = parser.search_vacancies(**info_params)
                except Exception as e:
                    logger.warning(f'{worker_prefix}Роль {role.name}: ошибка при получении информации о количестве вакансий: {e}, используем запрошенное количество страниц')
                    info_result = None
                
                if not info_result or 'found' not in info_result:
                    logger.warning(f'{worker_prefix}Роль {role.name}: не удалось получить информацию о количестве вакансий, используем запрошенное количество страниц')
                    total_found = 0
                    total_pages_api = actual_pages
                else:
                    total_found = info_result.get('found', 0)
                    # ВАЖНО: API возвращает pages для per_page=1, нужно пересчитать для нашего per_page_limit
                    pages_api_info = info_result.get('pages', 0)  # Страниц при per_page=1
                    
                    # Пересчитываем количество страниц для нашего per_page_limit
                    if total_found > 0 and per_page_limit > 0:
                        total_pages_api = (total_found + per_page_limit - 1) // per_page_limit  # Округление вверх
                    else:
                        total_pages_api = 0
                    
                    logger.debug(f'{worker_prefix}Роль {role.name}: API вернул found={total_found}, pages (при per_page=1)={pages_api_info}, пересчитано для per_page={per_page_limit}: {total_pages_api} страниц')
                    
                    # Рассчитываем оптимальное количество страниц на основе лимита 2000 вакансий
                    max_vacancies_limit = 2000
                    if total_found > 0:
                        # Рассчитываем количество страниц для достижения лимита
                        pages_needed_for_limit = (max_vacancies_limit + per_page_limit - 1) // per_page_limit  # Округление вверх
                        
                        # Берем минимум из: нужного для лимита, доступного в API, запрошенного
                        pages_needed = min(
                            pages_needed_for_limit,
                            total_pages_api,
                            actual_pages
                        )
                        
                        actual_pages = pages_needed
                        logger.info(f'{worker_prefix}Роль {role.name}: найдено {total_found} вакансий, доступно {total_pages_api} страниц (при {per_page_limit} вакансий/страницу), будем парсить {actual_pages} страниц (лимит: {max_vacancies_limit} вакансий)')
                    else:
                        logger.info(f'{worker_prefix}Роль {role.name}: вакансий не найдено, пропускаем')
                        continue

                logger.info(f'{worker_prefix}Начинаем парсинг роли {role.name}: {actual_pages} страниц по {per_page_limit} вакансий')

                # Парсим страницы с улучшенным логированием
                for page in range(actual_pages):
                    try:
                        # Поиск вакансий по профессиональной роли с оптимизированными параметрами
                        search_params = {
                            'professional_role': role.id,
                            'area': area,
                            'per_page': per_page_limit,
                            'page': page
                        }

                        try:
                            search_result = parser.search_vacancies(**search_params)
                            # Сбрасываем счетчик 403 ошибок при успешном запросе
                            consecutive_403_errors = 0
                        except Exception as api_error:
                            error_msg = str(api_error).lower()
                            if '403' in error_msg or 'forbidden' in error_msg or 'доступ запрещён' in error_msg:
                                consecutive_403_errors += 1
                                # Простая пауза 2 секунды при 403
                                logger.warning(f'{worker_prefix}Доступ запрещён (403) для роли {role.name} на странице {page + 1}. '
                                              f'Пауза 2 сек...')
                                time.sleep(2.0)
                                continue

                            elif '400' in error_msg or 'rate' in error_msg or 'block' in error_msg:
                                logger.warning(f'{worker_prefix}Роль {role.name}: API rate limit на странице {page + 1}, пауза 30 сек')
                                time.sleep(30)  # Длительная пауза при rate limit
                                continue
                            else:
                                logger.error(f'{worker_prefix}Роль {role.name}: API ошибка на странице {page + 1}: {api_error}')
                                continue

                        if not search_result or 'items' not in search_result:
                                logger.info(f'{worker_prefix}Роль {role.name}: страница {page + 1}/{actual_pages} - нет результатов')
                                break

                        page_vacancies = search_result['items']
                        page_vacancy_count = len(page_vacancies)
                        role_vacancies += page_vacancy_count

                        progress_percent = ((page + 1) / actual_pages) * 100
                        logger.info(f'{worker_prefix}Роль {role.name}: {page + 1}/{actual_pages} ({progress_percent:.1f}%) - {page_vacancy_count} вакансий')

                        # АСИНХРОННАЯ ОБРАБОТКА ДЕТАЛЕЙ ВАКАНСИЙ для ускорения
                        vacancy_ids = []
                        vacancy_objects = []

                        # Создаем объекты вакансий и собираем ID для асинхронной загрузки
                        for vacancy_data in page_vacancies:
                                try:
                                    vacancy_id = vacancy_data.get('id')
                                    if not vacancy_id:
                                        continue

                                    vacancy_obj = _create_vacancy_from_api_data(vacancy_data, role.id, role.name)
                                    vacancy_objects.append(vacancy_obj)
                                    vacancy_ids.append(vacancy_id)

                                except Exception as e:
                                    logger.error(f'{worker_prefix}Ошибка обработки данных вакансии: {e}')
                                    role_errors += 1

                        # АСИНХРОННАЯ ЗАГРУЗКА ДЕТАЛЕЙ (если нужно и есть ID)
                        if get_details and vacancy_ids:
                            try:
                                logger.debug(f'{worker_prefix}Асинхронная загрузка деталей для {len(vacancy_ids)} вакансий')

                                # Запускаем асинхронную загрузку в отдельном event loop
                                details_map = asyncio.run(_fetch_vacancy_details_batch_async(
                                    parser, vacancy_ids, worker_prefix
                                ))

                                # Обновляем объекты деталями
                                for vacancy_obj in vacancy_objects:
                                    vacancy_id = vacancy_obj.hh_id
                                    if vacancy_id in details_map and details_map[vacancy_id]:
                                        _update_vacancy_from_api_data(vacancy_obj, details_map[vacancy_id])

                            except Exception as e:
                                error_msg = str(e).lower()
                                if '403' in error_msg or 'forbidden' in error_msg or 'доступ запрещён' in error_msg:
                                    consecutive_403_errors += 1
                                    total_403_errors += 1
                                    total_details_errors += 1
                                    if consecutive_403_errors >= max_consecutive_403:
                                        logger.error(f'{worker_prefix}СЛИШКОМ МНОГО 403 ОШИБОК ПРИ ЗАГРУЗКЕ ДЕТАЛЕЙ ({consecutive_403_errors}/{max_consecutive_403}). '
                                                    f'Останавливаем worker {worker_id} на 5 секунд...')
                                        time.sleep(5)  # 5 секунд паузы
                                        consecutive_403_errors = 0
                                        continue

                                    # Простая пауза 2 секунды при 403
                                    # Логируем только каждую 5-ю ошибку
                                    if consecutive_403_errors % 5 == 0 or consecutive_403_errors <= 3:
                                        logger.warning(f'{worker_prefix}Доступ запрещён (403) при загрузке деталей (всего: {consecutive_403_errors}). Пауза 2 сек...')
                                    time.sleep(2.0)
                                    continue

                                # Для других ошибок логируем только первую
                                total_other_errors += 1
                                total_details_errors += 1
                                logger.warning(f'{worker_prefix}Ошибка асинхронной загрузки деталей: {e}. Пропускаем детали для этой страницы.')
                                
                                # Fallback: синхронная загрузка только для критичных случаев (не используем, т.к. это может привести к еще большим 403)
                                # Вакансии сохранятся без деталей, детали можно загрузить позже

                        # ПАКЕТНОЕ СОХРАНЕНИЕ В БД (максимальная производительность!)
                        if vacancy_objects:
                            try:
                                # Bulk create с оптимизациями
                                created_count = 0
                                batch_size_db = 100  # Увеличен размер батча для БД

                                for i in range(0, len(vacancy_objects), batch_size_db):
                                    batch = vacancy_objects[i:i + batch_size_db]
                                    try:
                                        result = Vacancy.objects.bulk_create(
                                            batch,
                                            ignore_conflicts=True,
                                            batch_size=batch_size_db
                                        )
                                        created_count += len(batch)
                                    except Exception as batch_error:
                                        logger.warning(f'{worker_prefix}Ошибка батча {i//batch_size_db + 1}: {batch_error}')
                                        # Fallback: сохраняем по одной с игнорированием ошибок
                                        for vacancy in batch:
                                            try:
                                                vacancy.save()
                                                created_count += 1
                                            except Exception:
                                                pass  # Игнорируем дубликаты и другие ошибки

                                role_new_vacancies += created_count
                                logger.debug(f'{worker_prefix}Создано {created_count} вакансий из {len(vacancy_objects)}')

                            except Exception as e:
                                logger.error(f'{worker_prefix}Критическая ошибка пакетного сохранения: {e}')
                                role_errors += len(vacancy_objects)

                    except Exception as e:
                        logger.error(f'{worker_prefix}Ошибка страницы {page + 1} для роли {role.name}: {e}')
                        continue

                    # Задержка между страницами (минимум 0.1 сек даже при no_delays для предотвращения блокировки)
                    if page < actual_pages - 1:
                        actual_delay = max(0.1, delay) if no_delays else delay
                        time.sleep(actual_delay)

                # Итоги роли
                logger.info(f'{worker_prefix}Роль {role.name} завершена: {role_vacancies} вакансий, '
                           f'новых: {role_new_vacancies}, обновлено: {role_updated_vacancies}')

                total_vacancies += role_vacancies
                total_new_vacancies += role_new_vacancies
                total_updated_vacancies += role_updated_vacancies
                parsed_roles += 1

            except Exception as e:
                logger.error(f'{worker_prefix}Ошибка роли {role.name}: {e}')
                continue

            # Задержка между ролями (минимум 0.1 сек даже при no_delays)
            if delay > 0:
                actual_delay = max(0.1, delay) if no_delays else delay
                time.sleep(actual_delay)

        # Задержка между батчами (минимум 0.5 сек даже при no_delays)
        if effective_batch_size < len(it_roles) and i + effective_batch_size < len(it_roles):
            batch_delay = max(0.5, delay * 2) if no_delays else (delay * 2)
            logger.info(f'{worker_prefix}Задержка между батчами: {batch_delay} сек')
            time.sleep(batch_delay)

    # Финальная статистика
    total_time = time.time() - task_start_time
    logger.info(f'{worker_prefix}🎉 Батч завершен за {total_time/60:.1f} мин: '
               f'{total_vacancies} вакансий, {total_new_vacancies} новых, {total_updated_vacancies} обновлено')

    return {
        'worker_id': worker_id,
        'roles_processed': parsed_roles,
        'total_vacancies': total_vacancies,
        'new_vacancies': total_new_vacancies,
        'updated_vacancies': total_updated_vacancies,
        'total_time_minutes': total_time / 60,
        'status': 'completed',
        'errors': {
            'total_403_errors': total_403_errors,
            'total_details_errors': total_details_errors,
            'total_other_errors': total_other_errors
        },
        'metrics': parser.metrics.to_dict() if parser.metrics else {}
    }


def _create_vacancy_from_api_data(vacancy_data: Dict[str, Any], role_id: str, role_name: str) -> Vacancy:
    """Создает объект Vacancy из данных API HeadHunter"""
    vacancy = Vacancy()

    # Основная информация
    vacancy.title = vacancy_data.get('name', '')
    vacancy.description = vacancy_data.get('description', '')
    if vacancy_data.get('snippet'):
        vacancy.requirements = vacancy_data['snippet'].get('requirement') or ''
        vacancy.responsibilities = vacancy_data['snippet'].get('responsibility') or ''

    # Зарплата
    salary_data = vacancy_data.get('salary')
    if salary_data:
        vacancy.salary_from = salary_data.get('from')
        vacancy.salary_to = salary_data.get('to')
        vacancy.salary_currency = salary_data.get('currency')
        vacancy.salary_gross = salary_data.get('gross', True)

    # Компания
    employer_data = vacancy_data.get('employer')
    if employer_data:
        vacancy.company_name = employer_data.get('name', '')
        vacancy.employer_id = str(employer_data.get('id', ''))
        vacancy.employer_name = employer_data.get('name', '')
        vacancy.employer_trusted = employer_data.get('trusted', False)

    # Локация
    area_data = vacancy_data.get('area')
    if area_data:
        vacancy.city = area_data.get('name')

    address_data = vacancy_data.get('address')
    if address_data:
        vacancy.address = address_data.get('raw')

    # Тип работы
    if vacancy_data.get('employment'):
        vacancy.employment_type = vacancy_data['employment'].get('name') or ''
    if vacancy_data.get('experience'):
        vacancy.experience_level = vacancy_data['experience'].get('name') or ''
    if vacancy_data.get('schedule'):
        vacancy.schedule_type = vacancy_data['schedule'].get('name') or ''

    # Роль и ID
    vacancy.professional_role = role_id
    vacancy.hh_id = str(vacancy_data.get('id', ''))
    vacancy.url = vacancy_data.get('alternate_url', '')

    # Даты
    published_at = vacancy_data.get('published_at')
    if published_at:
        from datetime import datetime
        vacancy.published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))

    return vacancy


def _update_vacancy_from_api_data(vacancy: Vacancy, details: Dict[str, Any]) -> bool:
    """Обновляет объект Vacancy детальной информацией из API"""
    has_changes = False

    # Сохраняем старые значения для сравнения
    old_description = vacancy.description
    old_key_skills = vacancy.key_skills
    old_responsibilities = vacancy.responsibilities
    old_requirements = vacancy.requirements
    old_is_active = vacancy.is_active
    old_has_test = vacancy.has_test
    old_response_letter_required = vacancy.response_letter_required
    old_premium = vacancy.premium

    # Обновляем описание и требования из детальной информации
    if 'description' in details and details['description'] != old_description:
        vacancy.description = details['description']
        has_changes = True

    if 'key_skills' in details and details['key_skills'] != old_key_skills:
        vacancy.key_skills = details['key_skills']
        has_changes = True

    # Обновляем обязанности, если они есть в деталях
    if 'responsibilities' in details:
        new_responsibilities = details['responsibilities'] or ''
        if new_responsibilities != old_responsibilities:
            vacancy.responsibilities = new_responsibilities
            has_changes = True

    # Обновляем требования, если они есть в деталях
    if 'requirements' in details:
        new_requirements = details['requirements'] or ''
        if new_requirements != old_requirements:
            vacancy.requirements = new_requirements
            has_changes = True

    # Обновляем статус вакансии
    if 'archived' in details:
        new_is_active = not details['archived']
        if new_is_active != old_is_active:
            vacancy.is_active = new_is_active
            has_changes = True

    # Обновляем дополнительные поля
    if details.get('has_test', False) != old_has_test:
        vacancy.has_test = details.get('has_test', False)
        has_changes = True

    if details.get('response_letter_required', False) != old_response_letter_required:
        vacancy.response_letter_required = details.get('response_letter_required', False)
        has_changes = True

    if details.get('premium', False) != old_premium:
        vacancy.premium = details.get('premium', False)
        has_changes = True

    return has_changes


def _merge_snippet_into_details(details: Dict[str, Any], search_vacancy: Dict[str, Any]) -> Dict[str, Any]:
    """
    Добавляет snippet из поисковой выдачи в детальные данные, если его нет.
    Это помогает не терять укороченный текст требований/обязанностей.
    """
    if 'snippet' not in details and search_vacancy.get('snippet'):
        details = dict(details)
        details['snippet'] = search_vacancy.get('snippet')

    # Если в деталях нет responsibilities/requirements, но есть в snippet — проставляем
    snippet = search_vacancy.get('snippet') or {}
    if 'responsibilities' not in details and snippet.get('responsibility'):
        details['responsibilities'] = snippet.get('responsibility')
    if 'requirements' not in details and snippet.get('requirement'):
        details['requirements'] = snippet.get('requirement')

    return details