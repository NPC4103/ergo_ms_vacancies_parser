import time
import logging
import requests
from datetime import datetime
from typing import Dict, List, Optional, Any

from django.utils import timezone

from .models import SuperJobVacancy

logger = logging.getLogger(__name__)

EMPLOYMENT_TYPE_MAP = {
    6: 'Полный рабочий день',
    10: 'Неполный день',
    12: 'Сменный график',
    13: 'Частичная занятость',
    7: 'Временная работа',
    9: 'Вахтовый метод',
}

EXPERIENCE_MAP = {
    1: 'Без опыта',
    2: 'От 1 года',
    3: 'От 3 лет',
    4: 'От 6 лет',
}

PLACE_OF_WORK_MAP = {
    1: 'На территории работодателя',
    2: 'На дому',
    3: 'Разъездной характер',
}


class SuperJobAPIClient:
    """Клиент для работы с API SuperJob"""

    BASE_URL = "https://api.superjob.ru/2.0"

    def __init__(self, api_key: str = None):
        self.api_key = api_key
        self.headers = {}
        if api_key:
            self.headers['X-Api-App-Id'] = api_key

    def search_vacancies(self,
                         keyword: str = None,
                         town: str = None,
                         experience: int = None,
                         type_of_work: int = None,
                         place_of_work: int = None,
                         catalogues: str = None,
                         payment_from: int = None,
                         payment_to: int = None,
                         page: int = 0,
                         count: int = 100) -> Dict[str, Any]:
        """Поиск вакансий через API SuperJob"""
        url = f"{self.BASE_URL}/vacancies/"

        params = {'page': page, 'count': count}

        if keyword:
            params['keyword'] = keyword
        if town:
            params['town'] = town
        if experience is not None:
            params['experience'] = experience
        if type_of_work is not None:
            params['type_of_work'] = type_of_work
        if place_of_work is not None:
            params['place_of_work'] = place_of_work
        if catalogues:
            params['catalogues'] = catalogues
        if payment_from is not None:
            params['payment_from'] = payment_from
        if payment_to is not None:
            params['payment_to'] = payment_to

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Ошибка при запросе к SuperJob API: {e}")
            return {"objects": [], "total": 0, "error": str(e)}

    def get_vacancy_details(self, vacancy_id: str) -> Optional[Dict[str, Any]]:
        """Получение детальной информации о вакансии"""
        url = f"{self.BASE_URL}/vacancies/{vacancy_id}/"

        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Ошибка при получении деталей вакансии {vacancy_id}: {e}")
            return None

    def get_catalogues(self) -> List[Dict[str, Any]]:
        """Получение списка всех каталогов (отраслей) SuperJob."""
        url = f"{self.BASE_URL}/catalogues/"

        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Ошибка при получении каталогов SuperJob: {e}")
            return []


def _parse_unixtime(timestamp) -> Optional[datetime]:
    """Безопасный парсинг unix timestamp в aware datetime."""
    if not timestamp:
        return None
    try:
        dt = datetime.fromtimestamp(int(timestamp))
        return timezone.make_aware(dt)
    except (ValueError, TypeError, OSError):
        return None


def _extract_object_field(data: Dict, field: str) -> Optional[str]:
    """Извлекает title из вложенного объекта {id, title}."""
    obj = data.get(field)
    if isinstance(obj, dict):
        return obj.get('title')
    return None


def _map_object_field(data: Dict, field: str, mapping: Dict) -> Optional[str]:
    """Маппит id вложенного объекта через словарь, fallback на title."""
    obj = data.get(field)
    if not isinstance(obj, dict):
        return None
    obj_id = obj.get('id')
    if obj_id in mapping:
        return mapping[obj_id]
    return obj.get('title')


def _build_full_description(vacancy_data: Dict[str, Any]) -> str:
    """Собирает полное описание вакансии из всех разделов ответа API."""
    sections = []

    work = vacancy_data.get('work')
    if work:
        sections.append(f"Обязанности:\n{work}")

    candidat = vacancy_data.get('candidat')
    if candidat:
        sections.append(f"Требования:\n{candidat}")

    compensation = vacancy_data.get('compensation')
    if compensation:
        sections.append(f"Условия:\n{compensation}")

    firm_activity = vacancy_data.get('firm_activity')
    if firm_activity:
        sections.append(f"О компании:\n{firm_activity}")

    return '\n\n'.join(sections)


def parse_vacancy_data(vacancy_data: Dict[str, Any]) -> Dict[str, Any]:
    """Парсинг данных вакансии из ответа API SuperJob в формат модели."""
    payment_from = vacancy_data.get('payment_from')
    payment_to = vacancy_data.get('payment_to')
    salary_from = payment_from if payment_from and payment_from > 0 else None
    salary_to = payment_to if payment_to and payment_to > 0 else None

    catalogues = vacancy_data.get('catalogues', [])
    professional_role = None
    catalogue_skills = []
    for catalogue in catalogues:
        if not professional_role and catalogue.get('title'):
            professional_role = catalogue['title']
        for position in catalogue.get('positions', []):
            if position.get('title'):
                catalogue_skills.append(position['title'])

    published_at = _parse_unixtime(vacancy_data.get('date_published'))
    if not published_at:
        published_at = timezone.now()

    return {
        'title': vacancy_data.get('profession', ''),
        'company_name': vacancy_data.get('firm_name', ''),
        'salary_from': salary_from,
        'salary_to': salary_to,
        'salary_currency': vacancy_data.get('currency'),
        'salary_gross': not vacancy_data.get('agreement', False),
        'city': _extract_object_field(vacancy_data, 'town'),
        'address': vacancy_data.get('address') or '',
        'description': _build_full_description(vacancy_data),
        'requirements': vacancy_data.get('candidat', ''),
        'responsibilities': vacancy_data.get('work', ''),
        'employment_type': _map_object_field(vacancy_data, 'type_of_work', EMPLOYMENT_TYPE_MAP),
        'experience_level': _map_object_field(vacancy_data, 'experience', EXPERIENCE_MAP),
        'schedule_type': _map_object_field(vacancy_data, 'place_of_work', PLACE_OF_WORK_MAP),
        'skills': catalogue_skills,
        'key_skills': [],
        'superjob_id': str(vacancy_data.get('id', '')),
        'url': vacancy_data.get('link', ''),
        'company_url': vacancy_data.get('client_logo') or None,
        'professional_role': professional_role,
        'employer_id': str(vacancy_data.get('id_client', '')),
        'employer_name': vacancy_data.get('firm_name', ''),
        'employer_trusted': False,
        'premium': False,
        'published_at': published_at,
    }


def save_vacancy_to_db(vacancy_data: Dict[str, Any]) -> Optional[SuperJobVacancy]:
    """Сохранение или обновление вакансии в базе данных."""
    try:
        superjob_id = vacancy_data.get('superjob_id')
        if not superjob_id:
            logger.warning("Отсутствует superjob_id для вакансии")
            return None

        existing = SuperJobVacancy.objects.filter(superjob_id=superjob_id).first()

        if existing:
            if existing.has_changes(vacancy_data):
                existing.create_version(vacancy_data)
                for field, value in vacancy_data.items():
                    if hasattr(existing, field):
                        setattr(existing, field, value)
                existing.save()
                logger.info(f"Обновлена вакансия: {existing.title}")
            return existing

        vacancy = SuperJobVacancy.objects.create(**vacancy_data)
        logger.info(f"Создана новая вакансия: {vacancy.title}")
        return vacancy

    except Exception as e:
        logger.error(f"Ошибка при сохранении вакансии: {e}")
        return None


def parse_vacancies_by_text(
    text: str,
    town: str = None,
    experience: int = None,
    employment: int = None,
    schedule: int = None,
    max_pages: int = 5,
    delay: float = 1.0,
    api_key: str = None) -> Dict[str, Any]:
    """Парсинг вакансий по текстовому запросу."""
    client = SuperJobAPIClient(api_key)
    total_vacancies = 0
    saved_vacancies = 0
    updated_vacancies = 0
    errors = 0

    logger.info(f"Начинаем парсинг вакансий по запросу: '{text}'")

    for page in range(max_pages):
        try:
            search_result = client.search_vacancies(
                keyword=text,
                town=town,
                experience=experience,
                type_of_work=employment,
                place_of_work=schedule,
                page=page,
                count=100,
            )

            vacancies = search_result.get('objects', [])
            if not vacancies:
                logger.info(f"Страница {page + 1}: вакансий не найдено, завершаем")
                break

            total_vacancies += len(vacancies)
            logger.info(f"Страница {page + 1}: найдено {len(vacancies)} вакансий")

            for vac_data in vacancies:
                try:
                    parsed = parse_vacancy_data(vac_data)
                    vacancy = save_vacancy_to_db(parsed)
                    if vacancy:
                        if vacancy.current_version == 1:
                            saved_vacancies += 1
                        else:
                            updated_vacancies += 1
                    else:
                        errors += 1
                except Exception as e:
                    logger.error(f"Ошибка при обработке вакансии: {e}")
                    errors += 1

            if not search_result.get('more', False):
                break

            if page < max_pages - 1:
                time.sleep(delay)

        except Exception as e:
            logger.error(f"Ошибка на странице {page + 1}: {e}")
            errors += 1

    result = {
        'total_vacancies': total_vacancies,
        'saved_vacancies': saved_vacancies,
        'updated_vacancies': updated_vacancies,
        'errors': errors,
        'search_query': text,
    }

    logger.info(f"Парсинг завершен: {result}")
    return result


def parse_all_vacancies(max_pages_per_query: int = 3,
                        delay: float = 1.0,
                        api_key: str = None) -> Dict[str, Any]:
    """Универсальный парсинг вакансий по набору популярных запросов."""
    search_queries = [
        'Python', 'JavaScript', 'Java', 'C++', 'C#', 'PHP', 'Go',
        'React', 'Vue', 'Angular', 'Node.js', 'Django', 'Flask',
        'DevOps', 'Docker', 'Kubernetes', 'AWS',
        'Data Science', 'Machine Learning',
        'Frontend', 'Backend', 'Full Stack',
        'iOS', 'Android', 'Mobile',
        'QA', 'Automation', 'Selenium',
        'Project Manager', 'Product Manager', 'Scrum',
        'UI/UX', 'Web Design',
        'HR', 'Recruiter',
        'Аналитик', 'Бухгалтер', 'Юрист',
        'Менеджер по продажам', 'Маркетолог',
        'Инженер', 'Механик', 'Электрик',
        'Водитель', 'Логистика',
    ]

    total_results = {
        'total_queries': len(search_queries),
        'total_vacancies': 0,
        'total_saved': 0,
        'total_updated': 0,
        'total_errors': 0,
        'queries_processed': 0,
        'queries_failed': 0,
    }

    logger.info(f"Начинаем универсальный парсинг: {len(search_queries)} запросов")

    for i, query in enumerate(search_queries, 1):
        try:
            logger.info(f"Запрос {i}/{len(search_queries)}: '{query}'")

            result = parse_vacancies_by_text(
                text=query,
                max_pages=max_pages_per_query,
                delay=delay,
                api_key=api_key,
            )

            total_results['total_vacancies'] += result['total_vacancies']
            total_results['total_saved'] += result['saved_vacancies']
            total_results['total_updated'] += result['updated_vacancies']
            total_results['total_errors'] += result['errors']
            total_results['queries_processed'] += 1

        except Exception as e:
            logger.error(f"Ошибка при обработке запроса '{query}': {e}")
            total_results['queries_failed'] += 1
            total_results['total_errors'] += 1

        if i < len(search_queries):
            time.sleep(delay * 2)

    logger.info(f"Универсальный парсинг завершен: {total_results}")
    return total_results


def parse_vacancies_by_catalogue(catalogue_id: int, catalogue_title: str = '', max_pages: int = 10, 
    delay: float = 1.0, api_key: str = None) -> Dict[str, Any]:
    """Парсинг вакансий по конкретному каталогу (отрасли)."""
    client = SuperJobAPIClient(api_key)
    total_vacancies = 0
    saved_vacancies = 0
    updated_vacancies = 0
    errors = 0

    logger.info(f"Парсинг каталога '{catalogue_title}' (id={catalogue_id})")

    for page in range(max_pages):
        try:
            search_result = client.search_vacancies(
                catalogues=str(catalogue_id),
                page=page,
                count=100,
            )

            vacancies = search_result.get('objects', [])
            if not vacancies:
                break

            total_vacancies += len(vacancies)

            for vac_data in vacancies:
                try:
                    parsed = parse_vacancy_data(vac_data)
                    vacancy = save_vacancy_to_db(parsed)
                    if vacancy:
                        if vacancy.current_version == 1:
                            saved_vacancies += 1
                        else:
                            updated_vacancies += 1
                    else:
                        errors += 1
                except Exception as e:
                    logger.error(f"Ошибка при обработке вакансии: {e}")
                    errors += 1

            if not search_result.get('more', False):
                break

            if page < max_pages - 1:
                time.sleep(delay)

        except Exception as e:
            logger.error(f"Ошибка на странице {page + 1} каталога '{catalogue_title}': {e}")
            errors += 1

    logger.info(
        f"Каталог '{catalogue_title}': найдено вакансий={total_vacancies}, "
        f"сохранено={saved_vacancies}, обновлено={updated_vacancies}"
    )

    return {
        'catalogue_id': catalogue_id,
        'catalogue_title': catalogue_title,
        'total_vacancies': total_vacancies,
        'saved_vacancies': saved_vacancies,
        'updated_vacancies': updated_vacancies,
        'errors': errors,
    }


def parse_vacancies_by_catalogues(catalogue_ids: List[int] = None,max_pages_per_catalogue: int = 10,
    delay: float = 1.0, api_key: str = None) -> Dict[str, Any]:
    """
    Парсинг вакансий по каталогам (отраслям) SuperJob.

    Если catalogue_ids не указаны, загружаются все каталоги с API
    и парсятся последовательно. Это самый эффективный способ
    покрыть все вакансии без дубликатов.
    """
    client = SuperJobAPIClient(api_key)

    if catalogue_ids:
        catalogues = [{'key': cid, 'title': f'Каталог {cid}'} for cid in catalogue_ids]
    else:
        raw_catalogues = client.get_catalogues()
        if not raw_catalogues:
            logger.error("Не удалось получить список каталогов SuperJob")
            return {
                'total_catalogues': 0, 'catalogues_processed': 0,
                'total_vacancies': 0, 'total_saved': 0,
                'total_updated': 0, 'total_errors': 1,
                'catalogues_failed': 1,
            }
        catalogues = [{'key': c['key'], 'title': c.get('title', '')} for c in raw_catalogues]

    total_results = {
        'total_catalogues': len(catalogues),
        'catalogues_processed': 0,
        'catalogues_failed': 0,
        'total_vacancies': 0,
        'total_saved': 0,
        'total_updated': 0,
        'total_errors': 0,
    }

    logger.info(f"Парсинг по каталогам: {len(catalogues)} каталогов")

    for i, cat in enumerate(catalogues, 1):
        try:
            logger.info(f"Каталог {i}/{len(catalogues)}: '{cat['title']}' (id={cat['key']})")

            result = parse_vacancies_by_catalogue(
                catalogue_id=cat['key'],
                catalogue_title=cat['title'],
                max_pages=max_pages_per_catalogue,
                delay=delay,
                api_key=api_key,
            )

            total_results['total_vacancies'] += result['total_vacancies']
            total_results['total_saved'] += result['saved_vacancies']
            total_results['total_updated'] += result['updated_vacancies']
            total_results['total_errors'] += result['errors']
            total_results['catalogues_processed'] += 1

        except Exception as e:
            logger.error(f"Ошибка при обработке каталога '{cat['title']}': {e}")
            total_results['catalogues_failed'] += 1
            total_results['total_errors'] += 1

        if i < len(catalogues):
            time.sleep(delay * 2)

    logger.info(f"Парсинг по каталогам завершен: {total_results}")
    return total_results


def get_catalogues_list(api_key: str = None) -> List[Dict[str, Any]]:
    """Получение списка каталогов SuperJob (для UI и выбора)."""
    client = SuperJobAPIClient(api_key)
    raw = client.get_catalogues()

    result = []
    for cat in raw:
        positions = [
            {'key': p['key'], 'title': p.get('title', '')}
            for p in cat.get('positions', [])
        ]
        result.append({
            'key': cat['key'],
            'title': cat.get('title', ''),
            'positions': positions,
        })
    return result


def get_vacancy_details(vacancy_id: str, api_key: str = None) -> Optional[Dict[str, Any]]:
    """Получение детальной информации о конкретной вакансии."""
    client = SuperJobAPIClient(api_key)
    return client.get_vacancy_details(vacancy_id)
