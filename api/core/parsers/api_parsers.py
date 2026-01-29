"""
API парсеры для HeadHunter, Habr Career, SuperJob.

Используют официальные API источников для получения данных.
"""

import logging
import requests
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base import (
    BaseParser,
    ParserFactory,
    ParserError,
    BlockedError,
    NetworkError,
    ValidationError
)

logger = logging.getLogger('celery.module.vacancies_parser')


class HeadHunterAPIParser(BaseParser):
    """
    Парсер HeadHunter через официальный API (https://api.hh.ru).
    
    Endpoints:
    - /vacancies - поиск вакансий
    - /vacancies/{id} - детальная информация
    - /professional_roles - список ролей
    """
    
    BASE_URL = "https://api.hh.ru"
    
    def __init__(self, source='headhunter', parsing_mode='api', *args, **kwargs):
        super().__init__(source=source, parsing_mode=parsing_mode, *args, **kwargs)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ErgoMS Vacancy Parser/1.0 (igoroffrus@mail.ru)'
        })
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Валидация конфигурации для HeadHunter API.
        
        Требуемые поля:
        - area: ID региона (например, 1 для Москвы)
        - per_page: количество вакансий на страницу (по умолчанию 100)
        - pages: количество страниц для парсинга
        
        Опциональные:
        - professional_role: ID профессиональной роли
        - text: текст для поиска
        - specialization: ID специализации
        """
        required_fields = ['area']
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Отсутствует обязательное поле в config: {field}")
        
        # Валидация типов
        if not isinstance(config.get('pages', 1), int):
            raise ValueError("Поле 'pages' должно быть числом")
        
        if config.get('pages', 1) < 1:
            raise ValueError("Поле 'pages' должно быть больше 0")
        
        return True
    
    def discover_items(self, config: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Обнаружение вакансий через HeadHunter API.
        
        Args:
            config: {
                'area': '1',  # ID региона
                'pages': 10,  # Количество страниц
                'per_page': 100,  # Вакансий на страницу
                'professional_role': '96',  # Опционально
                'text': 'python',  # Опционально
            }
        
        Returns:
            List[Dict]: [{'source_item_id': '12345', 'url': 'https://hh.ru/vacancy/12345'}, ...]
        """
        self.validate_config(config)
        
        items = []
        area = config['area']
        pages = config.get('pages', 1)
        per_page = config.get('per_page', 100)
        
        # Параметры поиска
        search_params = {
            'area': area,
            'per_page': per_page,
            'only_with_salary': False,
        }
        
        # Опциональные параметры
        if 'professional_role' in config:
            search_params['professional_role'] = config['professional_role']
        
        if 'text' in config:
            search_params['text'] = config['text']
        
        if 'specialization' in config:
            search_params['specialization'] = config['specialization']
        
        self.logger.info(f"Начало discovery для HeadHunter API: {search_params}")
        
        for page in range(pages):
            search_params['page'] = page
            
            try:
                response = self.session.get(
                    f"{self.BASE_URL}/vacancies",
                    params=search_params,
                    timeout=self.timeout
                )
                
                if response.status_code == 403:
                    raise BlockedError("Доступ заблокирован HeadHunter API (403)")
                
                if response.status_code == 429:
                    self.logger.warning("Rate limit превышен, ждем 1 минуту")
                    time.sleep(60)
                    continue
                
                response.raise_for_status()
                data = response.json()
                
                vacancies = data.get('items', [])
                
                for vacancy in vacancies:
                    vacancy_id = str(vacancy.get('id'))
                    url = vacancy.get('alternate_url', f"https://hh.ru/vacancy/{vacancy_id}")
                    
                    items.append({
                        'source_item_id': vacancy_id,
                        'url': url
                    })
                
                self.logger.info(
                    f"Discovery HeadHunter: страница {page+1}/{pages}, "
                    f"найдено {len(vacancies)} вакансий"
                )
                
                # Задержка между запросами
                time.sleep(config.get('delay', 0.5))
                
            except requests.RequestException as e:
                self.logger.error(f"Ошибка при discovery HeadHunter: {e}")
                raise NetworkError(f"Ошибка сети при discovery: {e}")
        
        self.logger.info(f"Discovery HeadHunter завершен: найдено {len(items)} вакансий")
        return items
    
    def parse_item(self, item_id: str, url: str) -> Dict[str, Any]:
        """
        Парсинг одной вакансии HeadHunter.
        
        Args:
            item_id: ID вакансии на HeadHunter
            url: URL вакансии (используется для fallback)
        
        Returns:
            Dict: Нормализованные данные вакансии
        """
        try:
            response = self.session.get(
                f"{self.BASE_URL}/vacancies/{item_id}",
                timeout=self.timeout
            )
            
            if response.status_code == 403:
                raise BlockedError(f"Доступ к вакансии {item_id} заблокирован (403)")
            
            if response.status_code == 404:
                raise ValidationError(f"Вакансия {item_id} не найдена (404)")
            
            if response.status_code == 429:
                raise BlockedError(f"Rate limit превышен для вакансии {item_id}")
            
            response.raise_for_status()
            raw_data = response.json()
            
            # Нормализация данных
            normalized = self._normalize_vacancy_data(raw_data)
            
            return normalized
            
        except requests.RequestException as e:
            self.logger.error(f"Ошибка при парсинге вакансии {item_id}: {e}")
            raise NetworkError(f"Ошибка сети при парсинге: {e}")
    
    def _normalize_vacancy_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Нормализация данных вакансии HeadHunter в унифицированный формат.
        
        Args:
            raw_data: Сырые данные от HeadHunter API
        
        Returns:
            Dict: Данные в формате NormalizedVacancy
        """
        # Основные поля
        normalized = {
            'source': 'headhunter',
            'source_id': str(raw_data.get('id')),
            'source_url': raw_data.get('alternate_url', ''),
            'parsing_mode': 'api',
            
            # Базовая информация
            'title': raw_data.get('name', ''),
            'description': raw_data.get('description', ''),
            
            # Компания
            'company_name': raw_data.get('employer', {}).get('name', ''),
            'company_url': raw_data.get('employer', {}).get('alternate_url'),
            
            # Зарплата
            **self._extract_salary(raw_data),
            
            # Локация
            **self._extract_location(raw_data),
            
            # Опыт и занятость
            'experience': raw_data.get('experience', {}).get('id'),
            'employment_type': self._extract_employment(raw_data),
            'schedule': self._extract_schedule(raw_data),
            
            # Навыки
            'key_skills': self._extract_skills(raw_data),
            'professional_roles': self._extract_roles(raw_data),
            
            # Контакты
            'contacts': raw_data.get('contacts'),
            
            # Статус
            'is_active': not raw_data.get('archived', False),
            'archived': raw_data.get('archived', False),
            'published_at': self._parse_datetime(raw_data.get('published_at')),
            
            # Дополнительно
            'has_test': raw_data.get('has_test', False),
            'accepts_handicapped': raw_data.get('accept_handicapped'),
            'response_letter_required': raw_data.get('response_letter_required'),
            
            # Специфичные данные
            'source_specific_data': {
                'premium': raw_data.get('premium', False),
                'billing_type': raw_data.get('billing_type', {}).get('name'),
                'apply_alternate_url': raw_data.get('apply_alternate_url'),
                'insider_interview': raw_data.get('insider_interview'),
            },
            
            # Сырые данные
            'raw_data': raw_data,
        }
        
        return normalized
    
    def _extract_salary(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Извлечение информации о зарплате"""
        salary = raw_data.get('salary')
        if not salary:
            return {
                'salary_from': None,
                'salary_to': None,
                'salary_currency': None,
                'salary_gross': None,
            }
        
        return {
            'salary_from': salary.get('from'),
            'salary_to': salary.get('to'),
            'salary_currency': salary.get('currency'),
            'salary_gross': salary.get('gross'),
        }
    
    def _extract_location(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Извлечение информации о локации"""
        area = raw_data.get('area', {})
        address = raw_data.get('address', {})
        
        return {
            'area_name': area.get('name'),
            'area_id': str(area.get('id')) if area.get('id') else None,
            'address': address.get('raw') if address else None,
        }
    
    def _extract_skills(self, raw_data: Dict[str, Any]) -> List[str]:
        """Извлечение навыков"""
        key_skills = raw_data.get('key_skills', [])
        return [skill.get('name') for skill in key_skills if skill.get('name')]
    
    def _extract_roles(self, raw_data: Dict[str, Any]) -> List[str]:
        """Извлечение профессиональных ролей"""
        roles = raw_data.get('professional_roles', [])
        return [role.get('name') for role in roles if role.get('name')]
    
    def _extract_employment(self, raw_data: Dict[str, Any]) -> List[str]:
        """Извлечение типов занятости"""
        employment = raw_data.get('employment')
        if not employment:
            return []
        return [employment.get('id')] if employment.get('id') else []
    
    def _extract_schedule(self, raw_data: Dict[str, Any]) -> List[str]:
        """Извлечение графиков работы"""
        schedule = raw_data.get('schedule')
        if not schedule:
            return []
        return [schedule.get('id')] if schedule.get('id') else []
    
    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Парсинг datetime строки"""
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            return None


class HabrCareerAPIParser(BaseParser):
    """
    Парсер Habr Career через неофициальный API.
    
    Note: Habr Career не имеет официального публичного API,
    используем endpoints из веб-версии.
    """
    
    BASE_URL = "https://career.habr.com"
    
    def __init__(self, source='habr_career', parsing_mode='api', *args, **kwargs):
        super().__init__(source=source, parsing_mode=parsing_mode, *args, **kwargs)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ErgoMS Vacancy Parser/1.0',
            'Accept': 'application/json',
        })
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Валидация конфигурации для Habr Career"""
        # Habr Career использует более простую конфигурацию
        if 'pages' in config and not isinstance(config['pages'], int):
            raise ValueError("Поле 'pages' должно быть числом")
        return True
    
    def discover_items(self, config: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Обнаружение вакансий через Habr Career.
        
        Note: На данный момент официальный стабильный API Habr Career
        не используется. Для Habr Career рекомендуется HTML режим.
        """
        message = (
            "API режим для Habr Career временно недоступен. "
            "Используйте HTML режим парсинга."
        )
        self.logger.warning(message)
        raise ValidationError(message)
    
    def parse_item(self, item_id: str, url: str) -> Dict[str, Any]:
        """Парсинг одной вакансии Habr Career"""
        message = (
            "API режим для Habr Career временно недоступен. "
            "Используйте HTML режим парсинга."
        )
        self.logger.warning(message)
        raise ValidationError(message)
    
    def _normalize_vacancy_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Нормализация данных Habr Career"""
        message = (
            "Нормализация данных для Habr Career API не реализована, "
            "так как API режим временно недоступен."
        )
        self.logger.warning(message)
        raise ValidationError(message)


class SuperJobAPIParser(BaseParser):
    """
    Парсер SuperJob через официальный API (https://api.superjob.ru).
    
    Требует API ключ: https://api.superjob.ru/info/
    """
    
    BASE_URL = "https://api.superjob.ru/2.0"
    
    def __init__(self, source='superjob', parsing_mode='api', api_key: Optional[str] = None, *args, **kwargs):
        super().__init__(source=source, parsing_mode=parsing_mode, *args, **kwargs)
        self.api_key = api_key
        self.session = requests.Session()
        
        if self.api_key:
            self.session.headers.update({
                'X-Api-App-Id': self.api_key,
            })
        
        self.session.headers.update({
            'User-Agent': 'ErgoMS Vacancy Parser/1.0',
        })
    
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Валидация конфигурации для SuperJob API"""
        if not self.api_key:
            raise ValueError("Для SuperJob API требуется API ключ")
        return True
    
    def discover_items(self, config: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Обнаружение вакансий через SuperJob API.
        
        Note: Для работы SuperJob API требуется действующий API ключ. "
        "На данный момент API режим не используется. "
        "Рекомендуется HTML режим парсинга."
        """
        message = (
            "API режим для SuperJob временно недоступен. "
            "Используйте HTML режим парсинга."
        )
        self.logger.warning(message)
        raise ValidationError(message)
    
    def parse_item(self, item_id: str, url: str) -> Dict[str, Any]:
        """Парсинг одной вакансии SuperJob"""
        message = (
            "API режим для SuperJob временно недоступен. "
            "Используйте HTML режим парсинга."
        )
        self.logger.warning(message)
        raise ValidationError(message)
    
    def _normalize_vacancy_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Нормализация данных SuperJob"""
        message = (
            "Нормализация данных для SuperJob API не реализована, "
            "так как API режим временно недоступен."
        )
        self.logger.warning(message)
        raise ValidationError(message)


# Регистрация парсеров в фабрике при импорте модуля.
# На данный момент в продакшене используется только HeadHunter API.
# Для Habr Career и SuperJob рекомендуется HTML режим, поэтому их API
# парсеры намеренно не регистрируются, чтобы режимы не помечались
# доступными в интерфейсе.
ParserFactory.register('headhunter', 'api', HeadHunterAPIParser)
