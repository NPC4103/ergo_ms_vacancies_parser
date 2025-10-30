from celery import shared_task
from .scripts import parse_vacancies_by_text, parse_all_vacancies, HeadHunterParser
from .models import Vacancy

@shared_task
def parse_hh_vacancies_task(
    text_list=None,
    area=113,
    pages=2,
    delay=1.0,
    get_details=True,
    universal=False,
    pages_per_area=5,
    max_total_pages=100,
    areas_only=False,
    config=None
):
    """
    Celery-задача для парсинга вакансий с HeadHunter.
    Возвращает статистику по результатам парсинга.
    """
    import logging
    
    # Получаем логгер для модуля
    logger = logging.getLogger('celery.module.headhunter')
    
    logger.info(f"Запуск задачи parse_hh_vacancies_task с параметрами: text_list={text_list}, universal={universal}")
    
    result = None
    if universal:
        logger.info("Выполняется универсальный парсинг")
        result = parse_all_vacancies(
            pages_per_area=pages_per_area,
            delay=delay,
            max_total_pages=max_total_pages,
            areas_only=areas_only
        )
        logger.info(f"Универсальный парсинг завершен: {result}")
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
    elif text_list:
        logger.info(f"Выполняется парсинг по тексту: {text_list}")
        result = parse_vacancies_by_text(
            text_list=text_list,
            area=area,
            pages=pages,
            delay=delay,
            get_details=get_details
        )
        logger.info(f"Парсинг по тексту завершен: {result}")
        return {
            'mode': 'by_text',
            'total_vacancies': result.get('total_vacancies'),
            'new_vacancies': result.get('new_vacancies'),
            'updated_vacancies': result.get('updated_vacancies'),
            'total_in_db': result.get('total_in_db'),
        }
    else:
        error_msg = 'Необходимо указать text_list или universal=True'
        logger.error(error_msg)
        print(f"ОШИБКА: {error_msg}")  # Дополнительный вывод в консоль
        return {'error': error_msg}

@shared_task
def parse_vacancies_by_technologies(
    categories=None,
    top_n=50,
    use_aliases=False,
    area=113,
    pages=2,
    delay=1.5,
    get_details=True,
    max_queries=None
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
    import logging
    
    logger = logging.getLogger('celery.module.headhunter')
    
    logger.info('='*70)
    logger.info('Запуск парсинга вакансий по технологиям')
    logger.info('='*70)
    logger.info(f'Параметры: categories={categories}, top_n={top_n}, '
               f'use_aliases={use_aliases}, area={area}, pages={pages}')
    
    try:
        # Отложенный импорт генератора технологий, чтобы не падать при старте worker/beat,
        # если приложение competence_core не подключено в INSTALLED_APPS
        from django.apps import apps as django_apps
        if not django_apps.is_installed('modules.competence_core.api.skill_map'):
            return {'error': 'Приложение modules.competence_core.api.skill_map не подключено'}

        from .utils.technology_search_generator import TechnologySearchGenerator
        # Создаем генератор запросов
        generator = TechnologySearchGenerator()
        
        # Загружаем технологии
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
        
        # Получаем статистику по технологиям
        stats = generator.get_statistics()
        logger.info(f"Загружено технологий: {stats['total_technologies']}")
        logger.info(f"   По категориям: {stats['by_category']}")
        if use_aliases:
            logger.info(f"   Всего алиасов: {stats['total_aliases']}")
        
        # Генерируем поисковые запросы
        search_queries = generator.generate_search_queries(
            use_aliases=use_aliases,
            max_queries=max_queries
        )
        
        logger.info(f'Сгенерировано {len(search_queries)} поисковых запросов')
        logger.info(f'   Первые 10: {search_queries[:10]}')
        
        # Запускаем парсинг
        logger.info('Начинаем парсинг вакансий...')
        
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
            'technologies_count': stats['total_technologies'],
            'search_queries_count': len(search_queries),
            'search_queries': search_queries[:20],  # Первые 20 для отчета
            'total_vacancies': result.get('total_vacancies'),
            'new_vacancies': result.get('new_vacancies'),
            'updated_vacancies': result.get('updated_vacancies'),
            'total_in_db': result.get('total_in_db'),
        }
        
    except Exception as e:
        error_msg = f'Ошибка при парсинге по технологиям: {e}'
        logger.error(error_msg, exc_info=True)
        return {'error': error_msg}


@shared_task
def parse_vacancies_by_category(
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
    import logging
    
    logger = logging.getLogger('celery.module.headhunter')
    
    logger.info(f'Запуск парсинга по категории: {category}')
    
    try:
        from django.apps import apps as django_apps
        if not django_apps.is_installed('modules.competence_core.api.skill_map'):
            return {
                'mode': 'by_category',
                'category': category,
                'error': 'Приложение modules.competence_core.api.skill_map не подключено'
            }

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
        
    except Exception as e:
        error_msg = f'Ошибка при парсинге категории {category}: {e}'
        logger.error(error_msg, exc_info=True)
        return {'error': error_msg}


@shared_task
def parse_single_vacancy_task(vacancy_id, force_update=False):
    """
    Celery-задача для парсинга одной вакансии по ID.
    Возвращает результат сохранения/обновления.
    """
    import logging
    
    # Получаем логгер для модуля
    logger = logging.getLogger('celery.module.headhunter')
    
    logger.info(f"Запуск задачи parse_single_vacancy_task для вакансии {vacancy_id}, force_update={force_update}")
    
    parser = HeadHunterParser()
    existing_vacancy = Vacancy.objects.filter(hh_id=vacancy_id).first()
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
            else:
                return {'status': 'no_changes', 'message': 'Изменений не обнаружено'}
        else:
            return {'status': 'exists', 'message': f'Вакансия {vacancy_id} уже есть в базе'}
    else:
        vacancy.save()
        return {'status': 'created', 'message': f'Вакансия {vacancy_id} успешно сохранена'} 