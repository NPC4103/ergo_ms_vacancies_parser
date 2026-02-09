import logging
import re
import time

import requests
from datetime import datetime
from django.utils import timezone

from .models import Vacancy

logger = logging.getLogger('modules.vacancies_parser.habr_career')


class HabrCareerParser:
    """Парсер для работы с API Хабр Карьеры"""
    
    def __init__(self, access_token=None):
        self.base_url = "https://career.habr.com/api"
        self.access_token = access_token
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        if access_token:
            self.headers['Authorization'] = f'Bearer {access_token}'
    
    def get_vacancies(self, page=1, per_page=100):
        """
        Получение вакансий пользователя
        
        Args:
            page (int): Номер страницы
            per_page (int): Количество вакансий на странице
        """
        if not self.access_token:
            logger.error("Не указан access_token для API Хабр Карьеры")
            return None
        
        params = {
            'page': page,
            'per_page': per_page
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/v1/integrations/vacancies",
                params=params,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Ошибка при получении вакансий: {e}")
            return None
    
    def get_archived_vacancies(self, page=1, per_page=100):
        """
        Получение архивных вакансий пользователя
        
        Args:
            page (int): Номер страницы
            per_page (int): Количество вакансий на странице
        """
        if not self.access_token:
            logger.error("Не указан access_token для API Хабр Карьеры")
            return None
        
        params = {
            'page': page,
            'per_page': per_page
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/v1/integrations/vacancies/archived",
                params=params,
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Ошибка при получении архивных вакансий: {e}")
            return None
    
    def get_vacancy_details(self, vacancy_id):
        """
        Получение детальной информации о вакансии
        
        Args:
            vacancy_id (str): ID вакансии
        """
        if not self.access_token:
            logger.error("Не указан access_token для API Хабр Карьеры")
            return None
        
        try:
            response = requests.get(
                f"{self.base_url}/v1/integrations/vacancies/{vacancy_id}",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Ошибка при получении деталей вакансии {vacancy_id}: {e}")
            return None
    
    def get_user_info(self):
        """Получение информации о текущем пользователе"""
        if not self.access_token:
            logger.error("Не указан access_token для API Хабр Карьеры")
            return None
        
        try:
            response = requests.get(
                f"{self.base_url}/v1/integrations/users/me",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Ошибка при получении информации о пользователе: {e}")
            return None
    
    def parse_vacancy(self, vacancy_data):
        """Парсинг данных вакансии в модель"""
        if not vacancy_data:
            logger.warning("vacancy_data is None")
            return None
            
        try:
            salary_from = None
            salary_to = None
            salary_currency = None
            
            salary_info = vacancy_data.get('salary', '')
            if salary_info:
                salary_pattern = r'от\s+(\d+)\s+до\s+(\d+)\s+(\w+)'
                match = re.search(salary_pattern, salary_info)
                if match:
                    salary_from = int(match.group(1))
                    salary_to = int(match.group(2))
                    salary_currency = match.group(3)
                else:
                    from_pattern = r'от\s+(\d+)\s+(\w+)'
                    match = re.search(from_pattern, salary_info)
                    if match:
                        salary_from = int(match.group(1))
                        salary_currency = match.group(2)
                    else:
                        to_pattern = r'до\s+(\d+)\s+(\w+)'
                        match = re.search(to_pattern, salary_info)
                        if match:
                            salary_to = int(match.group(1))
                            salary_currency = match.group(2)
            
            city = vacancy_data.get('city', '')
            
            company = vacancy_data.get('company', {})
            company_name = company.get('name', 'Не указано')
            company_url = company.get('url')
            company_alias = company.get('alias_name')
            company_logo_url = company.get('logo_url')
            
            specializations = []
            for spec in vacancy_data.get('specializations', []):
                spec_data = {
                    'id': spec.get('id'),
                    'title': spec.get('title', {})
                }
                specializations.append(spec_data)
            
            divisions = vacancy_data.get('divisions', [])
            
            published_at_str = vacancy_data.get('published_at')
            if published_at_str:
                try:
                    published_at = datetime.fromisoformat(published_at_str.replace('Z', '+00:00'))
                    if published_at.tzinfo is None:
                        published_at = timezone.make_aware(published_at)
                except ValueError:
                    published_at = timezone.now()
            else:
                published_at = timezone.now()
            
            vacancy_data_parsed = {
                'title': vacancy_data.get('title', ''),
                'company_name': company_name,
                'salary_from': salary_from,
                'salary_to': salary_to,
                'salary_currency': salary_currency,
                'salary_gross': True,
                'city': city,
                'description': vacancy_data.get('description', ''),
                'employment_type': vacancy_data.get('employment_type', ''),
                'qualification': vacancy_data.get('qualification'),
                'specializations': specializations,
                'divisions': divisions,
                'habr_id': str(vacancy_data.get('id', '')),
                'url': vacancy_data.get('url', ''),
                'company_url': company_url,
                'company_alias': company_alias,
                'company_logo_url': company_logo_url,
                'marked': vacancy_data.get('marked', False),
                'published_at': published_at,
            }
            
            return vacancy_data_parsed
            
        except Exception as e:
            logger.error(f"Ошибка при парсинге вакансии: {e}", exc_info=True)
            return None
    
    def save_vacancy(self, vacancy_data):
        """Сохранение вакансии в базу данных"""
        if not vacancy_data:
            return None
        
        try:
            habr_id = vacancy_data.get('habr_id')
            if not habr_id:
                logger.error("Отсутствует habr_id")
                return None
            
            existing_vacancy = Vacancy.objects.filter(habr_id=habr_id).first()
            
            if existing_vacancy:
                changes = existing_vacancy.has_changes(vacancy_data)
                if changes:
                    logger.info(f"Обновление вакансии {habr_id} с изменениями: {list(changes.keys())}")
                    existing_vacancy.create_version(vacancy_data)
                    
                    for field, value in vacancy_data.items():
                        if hasattr(existing_vacancy, field):
                            setattr(existing_vacancy, field, value)
                    
                    existing_vacancy.save()
                    return existing_vacancy
                else:
                    logger.debug(f"Вакансия {habr_id} не изменилась")
                    return existing_vacancy
            else:
                logger.info(f"Создание новой вакансии {habr_id}")
                vacancy = Vacancy.objects.create(**vacancy_data)
                return vacancy
                
        except Exception as e:
            logger.error(f"Ошибка при сохранении вакансии: {e}", exc_info=True)
            return None


def parse_habr_vacancies(access_token, pages=5, delay=1.0, get_details=True):
    """
    Парсинг вакансий с Хабр Карьеры
    
    Args:
        access_token (str): Токен доступа к API
        pages (int): Количество страниц для парсинга
        delay (float): Задержка между запросами в секундах
        get_details (bool): Получать ли детальную информацию о вакансиях
    """
    parser = HabrCareerParser(access_token)
    
    total_vacancies = 0
    new_vacancies = 0
    updated_vacancies = 0
    errors = 0
    
    logger.info(f"Начинаем парсинг вакансий с Хабр Карьеры. "
                f"Параметры: страниц={pages}, задержка={delay}с, детали={get_details}")
    
    user_info = parser.get_user_info()
    if user_info:
        logger.info(f"Пользователь: {user_info.get('first_name', '')} {user_info.get('last_name', '')}")
    
    for page in range(1, pages + 1):
        logger.info(f"Обрабатываем страницу {page}/{pages}")
        
        vacancies_data = parser.get_vacancies(page=page)
        if not vacancies_data:
            logger.error(f"Ошибка при получении вакансий со страницы {page}")
            errors += 1
            continue
        
        vacancies = vacancies_data.get('vacancies', [])
        if not vacancies:
            logger.info(f"На странице {page} нет вакансий")
            break
        
        logger.info(f"Найдено {len(vacancies)} вакансий на странице {page}")
        
        for i, vacancy_data in enumerate(vacancies, 1):
            try:
                logger.debug(f"Обрабатываем вакансию {i}/{len(vacancies)}: "
                             f"{vacancy_data.get('title', 'Без названия')}")
                
                if get_details:
                    vacancy_id = vacancy_data.get('id')
                    if vacancy_id:
                        detailed_data = parser.get_vacancy_details(vacancy_id)
                        if detailed_data:
                            vacancy_data = detailed_data
                
                parsed_data = parser.parse_vacancy(vacancy_data)
                if parsed_data:
                    saved_vacancy = parser.save_vacancy(parsed_data)
                    if saved_vacancy:
                        total_vacancies += 1
                        if saved_vacancy.created_at == saved_vacancy.updated_at:
                            new_vacancies += 1
                        else:
                            updated_vacancies += 1
                    else:
                        errors += 1
                else:
                    errors += 1
                
                if delay > 0 and i < len(vacancies):
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Ошибка при обработке вакансии: {e}", exc_info=True)
                errors += 1
        
        if delay > 0 and page < pages:
            time.sleep(delay)
    
    logger.info(f"Парсинг завершен. Всего: {total_vacancies}, "
                f"Новых: {new_vacancies}, Обновлено: {updated_vacancies}, Ошибок: {errors}")
    
    return {
        'total': total_vacancies,
        'new': new_vacancies,
        'updated': updated_vacancies,
        'errors': errors
    }


def parse_habr_archived_vacancies(access_token, pages=5, delay=1.0):
    """
    Парсинг архивных вакансий с Хабр Карьеры
    
    Args:
        access_token (str): Токен доступа к API
        pages (int): Количество страниц для парсинга
        delay (float): Задержка между запросами в секундах
    """
    parser = HabrCareerParser(access_token)
    
    total_vacancies = 0
    new_vacancies = 0
    updated_vacancies = 0
    errors = 0
    
    logger.info(f"Начинаем парсинг архивных вакансий с Хабр Карьеры. "
                f"Параметры: страниц={pages}, задержка={delay}с")
    
    for page in range(1, pages + 1):
        logger.info(f"Обрабатываем страницу {page}/{pages}")
        
        vacancies_data = parser.get_archived_vacancies(page=page)
        if not vacancies_data:
            logger.error(f"Ошибка при получении архивных вакансий со страницы {page}")
            errors += 1
            continue
        
        vacancies = vacancies_data.get('vacancies', [])
        if not vacancies:
            logger.info(f"На странице {page} нет архивных вакансий")
            break
        
        logger.info(f"Найдено {len(vacancies)} архивных вакансий на странице {page}")
        
        for i, vacancy_data in enumerate(vacancies, 1):
            try:
                logger.debug(f"Обрабатываем архивную вакансию {i}/{len(vacancies)}: "
                             f"{vacancy_data.get('title', 'Без названия')}")
                
                parsed_data = parser.parse_vacancy(vacancy_data)
                if parsed_data:
                    saved_vacancy = parser.save_vacancy(parsed_data)
                    if saved_vacancy:
                        total_vacancies += 1
                        if saved_vacancy.created_at == saved_vacancy.updated_at:
                            new_vacancies += 1
                        else:
                            updated_vacancies += 1
                    else:
                        errors += 1
                else:
                    errors += 1
                
                if delay > 0 and i < len(vacancies):
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Ошибка при обработке архивной вакансии: {e}", exc_info=True)
                errors += 1
        
        if delay > 0 and page < pages:
            time.sleep(delay)
    
    logger.info(f"Парсинг архивных вакансий завершен. Всего: {total_vacancies}, "
                f"Новых: {new_vacancies}, Обновлено: {updated_vacancies}, Ошибок: {errors}")
    
    return {
        'total': total_vacancies,
        'new': new_vacancies,
        'updated': updated_vacancies,
        'errors': errors
    }


def parse_habr_all_vacancies(access_token, pages=5, delay=1.0, get_details=True):
    """
    Парсинг всех вакансий (активных и архивных) с Хабр Карьеры
    Args:
        access_token (str): Токен доступа к API
        pages (int): Количество страниц для парсинга
        delay (float): Задержка между запросами в секундах
        get_details (bool): Получать ли детальную информацию о вакансиях
    """
    logger.info(f"Начинаем парсинг всех вакансий с Хабр Карьеры. "
                f"Параметры: страниц={pages}, задержка={delay}с, детали={get_details}")

    active_result = parse_habr_vacancies(
        access_token=access_token,
        pages=pages,
        delay=delay,
        get_details=get_details
    )
    logger.info("Активные вакансии обработаны, парсим архивные...")

    archived_result = parse_habr_archived_vacancies(
        access_token=access_token,
        pages=pages,
        delay=delay
    )

    total_result = {
        'active': active_result,
        'archived': archived_result,
        'total': {
            'total': active_result['total'] + archived_result['total'],
            'new': active_result['new'] + archived_result['new'],
            'updated': active_result['updated'] + archived_result['updated'],
            'errors': active_result['errors'] + archived_result['errors']
        }
    }
    logger.info(f"Парсинг всех вакансий завершен. "
                f"Всего: {total_result['total']['total']}, "
                f"Новых: {total_result['total']['new']}, "
                f"Обновлено: {total_result['total']['updated']}, "
                f"Ошибок: {total_result['total']['errors']}")
    return total_result
