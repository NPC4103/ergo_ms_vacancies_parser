import re
import time
import logging
import requests
import random
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from django.utils import timezone
from .models import Vacancy


logger = logging.getLogger('modules.vacancies_parser.headhunter')


class ProxyRotator:
    """Ротатор прокси-серверов для обхода блокировок"""

    # Базовый набор бесплатных прокси (резервный)
    DEFAULT_PROXIES = [
        {'http': 'http://185.82.99.181:9091', 'https': 'https://185.82.99.181:9091'},
        {'http': 'http://109.167.134.253:5678', 'https': 'https://109.167.134.253:5678'},
        {'http': 'http://195.201.108.163:1080', 'https': 'https://195.201.108.163:1080'},
    ]

    def __init__(self, custom_proxies: Optional[List[Dict[str, str]]] = None):
        self.proxies = custom_proxies or self.DEFAULT_PROXIES.copy()
        self.current_index = 0
        self.last_rotation = time.time()
        self.failed_proxies = set()  # Прокси с ошибками

    @classmethod
    def from_json_file(cls, json_file_path: str) -> 'ProxyRotator':
        """Создать ProxyRotator из JSON файла с прокси"""
        import json
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                proxy_data = json.load(f)

            proxies = []
            for item in proxy_data:
                proxy_url = item.get('proxy', '')
                protocol = item.get('protocol', 'http')
                https = item.get('https', False)

                if not proxy_url:
                    continue

                proxy_dict: Dict[str, str] = {}
                if protocol in ['http', 'https']:
                    if protocol == 'http' or https:
                        proxy_dict['http'] = proxy_url
                    if https or protocol == 'https':
                        # Преобразуем http в https если нужно
                        if proxy_url.startswith('http://'):
                            proxy_dict['https'] = proxy_url.replace('http://', 'https://', 1)
                        else:
                            proxy_dict['https'] = proxy_url
                elif protocol in ['socks4', 'socks5']:
                    # Для SOCKS прокси используем тот же URL для http и https
                    proxy_dict = {
                        'http': proxy_url,
                        'https': proxy_url
                    }

                if proxy_dict:
                    proxies.append(proxy_dict)

            logger.info(f'Загружено {len(proxies)} прокси из файла {json_file_path}')
            return cls(custom_proxies=proxies)

        except Exception as e:
            logger.error(f'Ошибка загрузки прокси из файла {json_file_path}: {e}')
            return cls()  # Возвращаем с дефолтными прокси

    def get_random_proxy(self) -> Optional[Dict[str, str]]:
        """Получить случайный рабочий прокси"""
        available_proxies = [p for i, p in enumerate(self.proxies) if i not in self.failed_proxies]
        if not available_proxies:
            return None
        return random.choice(available_proxies)

    def get_next_proxy(self) -> Optional[Dict[str, str]]:
        """Получить следующий прокси по кругу"""
        if not self.proxies:
            return None

        # Пропускаем нерабочие прокси
        attempts = 0
        while attempts < len(self.proxies):
            proxy = self.proxies[self.current_index]
            if self.current_index not in self.failed_proxies:
                self.current_index = (self.current_index + 1) % len(self.proxies)
                return proxy

            self.current_index = (self.current_index + 1) % len(self.proxies)
            attempts += 1

        return None

    def mark_proxy_failed(self, proxy: Dict[str, str]):
        """Отметить прокси как нерабочий"""
        try:
            proxy_url = proxy.get('http', proxy.get('https', ''))
            for i, p in enumerate(self.proxies):
                if p.get('http') == proxy_url or p.get('https') == proxy_url:
                    self.failed_proxies.add(i)
                    logger.warning(f"Прокси {proxy_url} отмечен как нерабочий")
                    break
        except Exception as e:
            logger.debug(f"Ошибка при отметке прокси как нерабочего: {e}")

    def should_rotate(self, requests_since_rotation: int, time_since_rotation: float) -> bool:
        """Определить, нужно ли ротировать прокси"""
        # Ротировать каждые 20-50 запросов или каждые 2-8 минут
        return (requests_since_rotation >= random.randint(20, 50) or
                time_since_rotation >= random.randint(120, 480))

    def test_proxy(self, proxy: Dict[str, str], timeout: float = 5.0) -> bool:
        """Протестировать работоспособность прокси"""
        try:
            test_url = "http://httpbin.org/ip"
            response = requests.get(test_url, proxies=proxy, timeout=timeout)
            return response.status_code == 200
        except Exception:
            return False

    def get_working_proxies(self) -> List[Dict[str, str]]:
        """Получить список рабочих прокси"""
        working_proxies = []
        for proxy in self.proxies:
            if self.test_proxy(proxy, timeout=2.0):
                working_proxies.append(proxy)
        return working_proxies

    def add_proxy(self, proxy: Dict[str, str]):
        """Добавить новый прокси"""
        self.proxies.append(proxy)

    def clear_failed_proxies(self):
        """Очистить список нерабочих прокси"""
        self.failed_proxies.clear()


class UserAgentRotator:
    """Ротатор User-Agent для обхода блокировок"""

    # Различные браузеры и устройства для имитации реальных пользователей
    USER_AGENTS = [
        # Chrome Desktop (разные версии)
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',

        # Firefox Desktop
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0',

        # Safari Desktop
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',

        # Edge
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',

        # Chrome Mobile
        'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/120.0.0.0 Mobile/15E148 Safari/604.1',

        # Opera
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0',

        # Yandex Browser
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 YaBrowser/24.1.0.0 Safari/537.36',
    ]

    def __init__(self):
        self.current_index = 0
        self.last_rotation = time.time()

    def get_random_user_agent(self) -> str:
        """Получить случайный User-Agent"""
        return random.choice(self.USER_AGENTS)

    def get_next_user_agent(self) -> str:
        """Получить следующий User-Agent по кругу"""
        ua = self.USER_AGENTS[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.USER_AGENTS)
        return ua

    def should_rotate(self, requests_since_rotation: int, time_since_rotation: float) -> bool:
        """Определить, нужно ли ротировать User-Agent"""
        # Ротировать каждые 50-100 запросов или каждые 5-15 минут
        return (requests_since_rotation >= random.randint(50, 100) or
                time_since_rotation >= random.randint(300, 900))


class RequestJitter:
    """Генератор jitter для имитации человеческого поведения"""

    def __init__(self, base_delay: float = 1.0, jitter_factor: float = 0.3):
        self.base_delay = base_delay
        self.jitter_factor = jitter_factor

    def get_delay(self) -> float:
        """Получить задержку с jitter"""
        # Добавляем случайное отклонение ±30% от базовой задержки
        jitter = random.uniform(-self.jitter_factor, self.jitter_factor)
        delay = self.base_delay * (1 + jitter)
        # Минимум 0.1 секунды, максимум не больше base_delay * 2
        return max(0.1, min(delay, self.base_delay * 2))

    def get_human_like_delay(self, min_delay: float = 0.5, max_delay: float = 3.0) -> float:
        """Получить задержку, имитирующую человеческое поведение"""
        # Используем нормальное распределение для более реалистичных задержек
        mean = (min_delay + max_delay) / 2
        std_dev = (max_delay - min_delay) / 6  # 99.7% значений в пределах min-max

        delay = random.gauss(mean, std_dev)
        return max(min_delay, min(delay, max_delay))

    def get_page_turn_delay(self) -> float:
        """Задержка при перелистывании страниц (дольше, как будто читают)"""
        return random.uniform(2.0, 5.0)

    def get_detail_request_delay(self) -> float:
        """Задержка при запросе деталей вакансии"""
        return random.uniform(0.5, 2.0)


@dataclass
class ParsingMetrics:
    """Метрики парсинга для мониторинга"""
    start_time: datetime = field(default_factory=timezone.now)
    requests_count: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limits_hit: int = 0
    new_vacancies: int = 0
    updated_vacancies: int = 0
    skipped_vacancies: int = 0
    errors: List[str] = field(default_factory=list)
    
    def record_request(self, success: bool = True):
        """Записать результат запроса"""
        self.requests_count += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
    
    def record_rate_limit(self):
        """Записать срабатывание rate limit"""
        self.rate_limits_hit += 1
    
    def record_error(self, error_msg: str):
        """Записать ошибку"""
        self.errors.append(f"{timezone.now().isoformat()}: {error_msg}")
        if len(self.errors) > 100:  # Ограничиваем количество ошибок
            self.errors = self.errors[-100:]
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразовать в словарь для логирования"""
        duration = (timezone.now() - self.start_time).total_seconds()
        return {
            'duration_seconds': round(duration, 2),
            'requests_total': self.requests_count,
            'requests_successful': self.successful_requests,
            'requests_failed': self.failed_requests,
            'rate_limits_hit': self.rate_limits_hit,
            'new_vacancies': self.new_vacancies,
            'updated_vacancies': self.updated_vacancies,
            'skipped_vacancies': self.skipped_vacancies,
            'avg_request_time': round(duration / self.requests_count, 3) if self.requests_count else 0,
            'success_rate': round(self.successful_requests / self.requests_count * 100, 1) if self.requests_count else 0,
            'errors_count': len(self.errors)
        }
    
    def log_summary(self):
        """Вывести сводку в лог"""
        stats = self.to_dict()
        logger.info(
            "Метрики парсинга: %d запросов за %.1f сек, "
            "новых: %d, обновлено: %d, пропущено: %d, "
            "rate limits: %d, ошибок: %d",
            stats['requests_total'],
            stats['duration_seconds'],
            stats['new_vacancies'],
            stats['updated_vacancies'],
            stats['skipped_vacancies'],
            stats['rate_limits_hit'],
            stats['errors_count']
        )


class HeadHunterParser:
    """Парсер для работы с API HeadHunter с ротацией User-Agent и jitter"""

    # Константы для rate limiting
    MAX_RETRIES = 3
    BASE_DELAY = 1.0
    MAX_DELAY = 60.0

    def __init__(self, metrics: Optional[ParsingMetrics] = None, use_jitter: bool = True,
                 rotate_user_agent: bool = True, use_proxy: bool = False,
                 custom_proxies: Optional[List[Dict[str, str]]] = None):
        self.base_url = "https://api.hh.ru"
        self.metrics = metrics or ParsingMetrics()
        self.use_jitter = use_jitter
        self.rotate_user_agent = rotate_user_agent
        self.use_proxy = use_proxy

        # Инициализация компонентов
        self.ua_rotator = UserAgentRotator() if rotate_user_agent else None
        self.jitter = RequestJitter(base_delay=self.BASE_DELAY) if use_jitter else None
        self.proxy_rotator = ProxyRotator(custom_proxies) if use_proxy else None

        # Счетчики для ротации
        self.requests_since_ua_rotation = 0
        self.requests_since_proxy_rotation = 0
        self.session_start_time = time.time()

        # Начальный User-Agent
        self._update_headers()

    def _update_headers(self):
        """Обновить заголовки с новым User-Agent"""
        user_agent = (self.ua_rotator.get_random_user_agent() if self.ua_rotator
                     else 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        self.headers = {
            'User-Agent': user_agent,
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    def _should_rotate_user_agent(self) -> bool:
        """Определить, нужно ли ротировать User-Agent"""
        if not self.ua_rotator:
            return False

        time_since_rotation = time.time() - self.ua_rotator.last_rotation
        return self.ua_rotator.should_rotate(self.requests_since_ua_rotation, time_since_rotation)

    def _should_rotate_proxy(self) -> bool:
        """Определить, нужно ли ротировать прокси"""
        if not self.proxy_rotator:
            return False

        time_since_rotation = time.time() - self.proxy_rotator.last_rotation
        return self.proxy_rotator.should_rotate(self.requests_since_proxy_rotation, time_since_rotation)

    def _rotate_user_agent(self):
        """Ротировать User-Agent"""
        if self.ua_rotator:
            old_ua = self.headers.get('User-Agent', '').split(' ')[0]
            self._update_headers()
            new_ua = self.headers.get('User-Agent', '').split(' ')[0]
            logger.debug(f'Ротирован User-Agent: {old_ua} -> {new_ua}')
            self.ua_rotator.last_rotation = time.time()
            self.requests_since_ua_rotation = 0

    def _rotate_proxy(self):
        """Ротировать прокси"""
        if self.proxy_rotator:
            old_proxy = getattr(self, '_current_proxy', None)
            self._current_proxy = self.proxy_rotator.get_random_proxy()
            logger.debug(f'Ротирован прокси: {old_proxy} -> {self._current_proxy}')
            self.proxy_rotator.last_rotation = time.time()
            self.requests_since_proxy_rotation = 0

    def _get_current_proxy(self) -> Optional[Dict[str, str]]:
        """Получить текущий прокси"""
        if not self.use_proxy or not self.proxy_rotator:
            return None

        if not hasattr(self, '_current_proxy') or self._current_proxy is None:
            self._current_proxy = self.proxy_rotator.get_random_proxy()

        return self._current_proxy

    def _get_delay(self, is_page_turn: bool = False, is_detail_request: bool = False) -> float:
        """Получить задержку с учетом jitter"""
        if not self.jitter:
            return self.BASE_DELAY

        if is_page_turn:
            return self.jitter.get_page_turn_delay()
        elif is_detail_request:
            return self.jitter.get_detail_request_delay()
        else:
            return self.jitter.get_delay()
    
    def _make_request(
        self,
        url: str,
        params: Optional[Dict] = None,
        max_retries: Optional[int] = None,
        is_page_turn: bool = False,
        is_detail_request: bool = False
    ) -> Optional[Dict]:
        """
        Выполнить HTTP-запрос с обработкой rate limiting, ротацией User-Agent и jitter.

        Args:
            url: URL для запроса
            params: Параметры запроса
            max_retries: Максимальное количество попыток
            is_page_turn: Запрос на следующую страницу
            is_detail_request: Запрос деталей вакансии

        Returns:
            JSON-ответ или None при ошибке
        """
        max_retries = max_retries or self.MAX_RETRIES
        last_error = None

        # Ротируем User-Agent и прокси если нужно
        if self._should_rotate_user_agent():
            self._rotate_user_agent()

        if self._should_rotate_proxy():
            self._rotate_proxy()

        for attempt in range(max_retries):
            try:
                # Добавляем jitter задержку перед запросом (кроме первого)
                if attempt > 0 or self.requests_since_ua_rotation > 0:
                    delay = self._get_delay(is_page_turn, is_detail_request)
                    time.sleep(delay)
                    logger.debug(f"Jitter delay: {delay:.2f}s")

                # Получаем текущий прокси
                current_proxy = self._get_current_proxy()
                self.requests_since_ua_rotation += 1
                self.requests_since_proxy_rotation += 1

                response = requests.get(url, params=params, headers=self.headers,
                                      proxies=current_proxy, timeout=30)

                # Обработка rate limiting (429 Too Many Requests)
                if response.status_code == 429:
                    self.metrics.record_rate_limit()
                    retry_after = int(response.headers.get('Retry-After', 60))
                    retry_after = min(retry_after, self.MAX_DELAY)
                    logger.warning(
                        "Rate limit достигнут (попытка %d/%d), ожидание %d сек...",
                        attempt + 1, max_retries, retry_after
                    )
                    time.sleep(retry_after)
                    # При rate limit ротируем User-Agent и прокси
                    self._rotate_user_agent()
                    if self.use_proxy:
                        self._rotate_proxy()
                    continue
                
                # Обработка 403 Forbidden (возможно бан)
                if response.status_code == 403:
                    self.metrics.record_request(success=False)
                    self.metrics.record_error(f"403 Forbidden для {url}")
                    logger.error("Доступ запрещён (403). Возможно, временная блокировка IP.")
                    # Увеличенная пауза при 403
                    delay = min(self.BASE_DELAY * (2 ** attempt) * 5, self.MAX_DELAY)
                    time.sleep(delay)

                    # Ротируем User-Agent и прокси при 403
                    self._rotate_user_agent()
                    if self.use_proxy:
                        self._rotate_proxy()
                    continue
                
                # Успешный запрос
                response.raise_for_status()
                self.metrics.record_request(success=True)
                return response.json()
                
            except requests.Timeout as e:
                last_error = e
                self.metrics.record_request(success=False)
                self.metrics.record_error(f"Timeout для {url}")
                logger.warning("Timeout при запросе %s (попытка %d/%d)", url, attempt + 1, max_retries)
                
            except requests.ConnectionError as e:
                last_error = e
                self.metrics.record_request(success=False)
                self.metrics.record_error(f"Connection error для {url}")
                logger.warning("Ошибка соединения %s (попытка %d/%d)", url, attempt + 1, max_retries)

                # Ротируем прокси при ошибке соединения
                if self.use_proxy and self.proxy_rotator and current_proxy:
                    self.proxy_rotator.mark_proxy_failed(current_proxy)
                    self._rotate_proxy()

            except requests.HTTPError as e:
                last_error = e
                self.metrics.record_request(success=False)
                self.metrics.record_error(f"HTTP error {e.response.status_code} для {url}")
                logger.warning("HTTP ошибка %s: %s", url, e)
                
            except requests.RequestException as e:
                last_error = e
                self.metrics.record_request(success=False)
                self.metrics.record_error(str(e))
                logger.warning("Ошибка запроса %s: %s", url, e)
            
            # Exponential backoff перед следующей попыткой
            if attempt < max_retries - 1:
                delay = min(self.BASE_DELAY * (2 ** attempt), self.MAX_DELAY)
                logger.debug("Ожидание %.1f сек перед повторной попыткой...", delay)
                time.sleep(delay)
        
        # Все попытки исчерпаны
        logger.error("Не удалось выполнить запрос %s после %d попыток: %s", url, max_retries, last_error)
        return None
    
    def search_vacancies(self, text=None, area=None, experience=None, employment=None,
                        schedule=None, professional_role=None, per_page=100, page=0,
                        only_with_salary=False, date_from=None, date_to=None):
        """
        Поиск вакансий по параметрам

        Args:
            text (str): Текст для поиска (может содержать несколько слов)
            area (int): ID региона (1 - Москва, 2 - СПб, 113 - Россия)
            experience (str): Опыт работы (noExperience, between1And3, between3And6, moreThan6)
            employment (str): Тип занятости (full, part, project, volunteer, probation)
            schedule (str): График работы (fullDay, shift, flexible, remote, flyInFlyOut)
            professional_role (int): ID профессиональной роли
            per_page (int): Количество вакансий на странице (максимум 100)
            page (int): Номер страницы
            only_with_salary (bool): Только вакансии с указанной зарплатой
            date_from (str): Дата публикации от (формат YYYY-MM-DD)
            date_to (str): Дата публикации до (формат YYYY-MM-DD)
        """
        params = {
            'per_page': per_page,
            'page': page,
            'order_by': 'publication_time'
        }
        
        # Фильтр по зарплате (опционально)
        if only_with_salary:
            params['only_with_salary'] = True
        
        if text:
            params['text'] = text
        if area:
            params['area'] = area
        if experience:
            params['experience'] = experience
        if employment:
            params['employment'] = employment
        if schedule:
            params['schedule'] = schedule
        if professional_role:
            params['professional_role'] = professional_role
        if date_from:
            params['date_from'] = date_from
        if date_to:
            params['date_to'] = date_to

        # Добавляем jitter для страниц после первой (имитация чтения)
        is_page_turn = page > 0
        return self._make_request(f"{self.base_url}/vacancies", params=params, is_page_turn=is_page_turn)
    
    def get_vacancy_details(self, vacancy_id):
        """Получение детальной информации о вакансии"""
        return self._make_request(f"{self.base_url}/vacancies/{vacancy_id}", is_detail_request=True)
    
    def check_vacancy_exists(self, vacancy_id) -> Optional[Dict]:
        """
        Проверить, существует ли вакансия и не архивирована ли она.
        
        Args:
            vacancy_id: ID вакансии на hh.ru
            
        Returns:
            Dict с информацией или None если вакансия не найдена/архивирована
        """
        result = self._make_request(f"{self.base_url}/vacancies/{vacancy_id}")
        if result and result.get('archived'):
            return None
        return result
    
    def parse_vacancy(self, vacancy_data):
        """Парсинг данных вакансии в модель"""
        if not vacancy_data:
            print("Ошибка: vacancy_data is None")
            return None
            
        try:
            # Парсим зарплату (безопасно обрабатываем null)
            salary = vacancy_data.get('salary') or {}
            salary_from = salary.get('from')
            salary_to = salary.get('to')
            salary_currency = salary.get('currency')
            salary_gross = salary.get('gross', True)
            
            # Парсим локацию (безопасно обрабатываем null)
            area = vacancy_data.get('area') or {}
            city = area.get('name')
            
            # Парсим компанию (безопасно обрабатываем null)
            employer = vacancy_data.get('employer') or {}
            company_name = employer.get('name', 'Не указано')
            company_url = employer.get('alternate_url')
            employer_id = employer.get('id')
            employer_trusted = employer.get('trusted', False)
            employer_blacklisted = employer.get('blacklisted', False)
            
            # Парсим навыки
            key_skills = [skill.get('name', '') for skill in vacancy_data.get('key_skills', [])]
            
            # Парсим дату публикации
            published_at_str = vacancy_data.get('published_at')
            if published_at_str:
                # Убираем 'Z' и парсим дату
                if published_at_str.endswith('Z'):
                    published_at_str = published_at_str[:-1] + '+00:00'
                
                try:
                    published_at = datetime.fromisoformat(published_at_str)
                    # Если дата уже содержит часовой пояс, не делаем её aware
                    if published_at.tzinfo is None:
                        published_at = timezone.make_aware(published_at)
                except ValueError:
                    published_at = timezone.now()
            else:
                published_at = timezone.now()
            
            # Получаем описание и извлекаем секции
            description = vacancy_data.get('description', '')
            
            # Сначала пробуем получить из snippet (обрезанные данные)
            requirements = self._get_snippet_field(vacancy_data.get('snippet'), 'requirement')
            responsibilities = self._get_snippet_field(vacancy_data.get('snippet'), 'responsibility')
            
            # Если есть полное описание, пробуем извлечь полные данные
            if description:
                extracted = self._extract_sections_from_description(description)
                # Используем извлечённые данные если они длиннее чем из snippet
                if extracted['requirements'] and len(extracted['requirements']) > len(requirements or ''):
                    requirements = extracted['requirements']
                if extracted['responsibilities'] and len(extracted['responsibilities']) > len(responsibilities or ''):
                    responsibilities = extracted['responsibilities']
            
            # Создаем объект вакансии с полными данными
            vacancy = Vacancy(
                title=vacancy_data.get('name', 'Без названия'),
                company_name=company_name,
                salary_from=salary_from,
                salary_to=salary_to,
                salary_currency=salary_currency,
                salary_gross=salary_gross,
                city=city,
                address=self._get_address_raw(vacancy_data.get('address')),
                description=description,
                requirements=requirements,
                responsibilities=responsibilities,
                employment_type=(vacancy_data.get('employment') or {}).get('name'),
                experience_level=(vacancy_data.get('experience') or {}).get('name'),
                skills=[],
                key_skills=key_skills,
                hh_id=vacancy_data['id'],
                url=vacancy_data.get('alternate_url', ''),
                company_url=company_url,
                # Дополнительные поля
                schedule_type=(vacancy_data.get('schedule') or {}).get('name'),
                professional_role=self._get_professional_role_name(vacancy_data.get('professional_roles', [])),
                alternate_url=vacancy_data.get('alternate_url', ''),
                apply_alternate_url=vacancy_data.get('apply_alternate_url', ''),
                # Информация о работодателе
                employer_id=employer_id,
                employer_name=company_name,
                employer_trusted=employer_trusted,
                employer_blacklisted=employer_blacklisted,
                # Дополнительная информация
                premium=vacancy_data.get('premium', False),
                has_test=vacancy_data.get('has_test', False),
                response_letter_required=vacancy_data.get('response_letter_required', False),
                published_at=published_at
            )
            
            return vacancy
            
        except Exception as e:
            print(f"Ошибка при парсинге вакансии {vacancy_data.get('id', 'unknown')}: {e}")
            return None
    
    def _get_professional_role_name(self, professional_roles):
        """Безопасное извлечение названия профессиональной роли"""
        try:
            if professional_roles and len(professional_roles) > 0:
                first_role = professional_roles[0]
                if isinstance(first_role, dict):
                    return first_role.get('name')
            return None
        except Exception:
            return None
    
    def _get_address_raw(self, address_data):
        """Безопасное извлечение адреса"""
        try:
            if address_data and isinstance(address_data, dict):
                return address_data.get('raw')
            return None
        except Exception:
            return None
    
    def _get_snippet_field(self, snippet_data, field_name):
        """Безопасное извлечение поля из snippet"""
        try:
            if snippet_data and isinstance(snippet_data, dict):
                return snippet_data.get(field_name, '')
            return ''
        except Exception:
            return ''
    
    def _extract_sections_from_description(self, description_html):
        """
        Извлечение требований и обязанностей из полного HTML-описания вакансии.
        
        Args:
            description_html (str): HTML-описание вакансии
            
        Returns:
            dict: Словарь с ключами 'requirements' и 'responsibilities'
        """
        result = {
            'requirements': '',
            'responsibilities': ''
        }
        
        if not description_html:
            return result
        
        try:
            # Паттерны для поиска секций (различные варианты написания)
            requirements_patterns = [
                r'(?:требования|требуется|ожидания|что мы ждём|ждём от вас|вы нам подходите|наши требования|мы ожидаем|что нужно знать|необходимые навыки|обязательно)[:\s]*</(?:strong|b|p|h\d)>(.+?)(?=<(?:strong|b|p|h\d)[^>]*>(?:обязанности|условия|мы предлагаем|что предлагаем|будет плюсом|преимущества)|$)',
                r'<(?:strong|b)[^>]*>(?:требования|требуется|ожидания)[^<]*</(?:strong|b)>(.+?)(?=<(?:strong|b)[^>]*>|$)',
            ]
            
            responsibilities_patterns = [
                r'(?:обязанности|задачи|вам предстоит|чем предстоит заниматься|что нужно делать|будете заниматься|ваши задачи|основные задачи)[:\s]*</(?:strong|b|p|h\d)>(.+?)(?=<(?:strong|b|p|h\d)[^>]*>(?:требования|условия|мы предлагаем|что предлагаем)|$)',
                r'<(?:strong|b)[^>]*>(?:обязанности|задачи|вам предстоит)[^<]*</(?:strong|b)>(.+?)(?=<(?:strong|b)[^>]*>|$)',
            ]
            
            # Пробуем найти требования
            for pattern in requirements_patterns:
                match = re.search(pattern, description_html, re.IGNORECASE | re.DOTALL)
                if match:
                    requirements_html = match.group(1)
                    result['requirements'] = self._html_to_text(requirements_html)
                    break
            
            # Пробуем найти обязанности
            for pattern in responsibilities_patterns:
                match = re.search(pattern, description_html, re.IGNORECASE | re.DOTALL)
                if match:
                    responsibilities_html = match.group(1)
                    result['responsibilities'] = self._html_to_text(responsibilities_html)
                    break
            
        except Exception as e:
            print(f"Ошибка при извлечении секций из описания: {e}")
        
        return result
    
    def _html_to_text(self, html_content):
        """
        Конвертирует HTML в чистый текст.
        
        Args:
            html_content (str): HTML-контент
            
        Returns:
            str: Чистый текст
        """
        if not html_content:
            return ''
        
        try:
            # Заменяем теги списков на переносы строк
            text = re.sub(r'<li[^>]*>', '• ', html_content)
            text = re.sub(r'</li>', '\n', text)
            text = re.sub(r'<br\s*/?>', '\n', text)
            text = re.sub(r'</p>', '\n', text)
            text = re.sub(r'</div>', '\n', text)
            
            # Убираем все оставшиеся HTML-теги
            text = re.sub(r'<[^>]+>', '', text)
            
            # Декодируем HTML-сущности
            text = text.replace('&nbsp;', ' ')
            text = text.replace('&amp;', '&')
            text = text.replace('&lt;', '<')
            text = text.replace('&gt;', '>')
            text = text.replace('&quot;', '"')
            text = text.replace('&#39;', "'")
            
            # Убираем множественные пробелы и переносы
            text = re.sub(r'[ \t]+', ' ', text)
            text = re.sub(r'\n\s*\n', '\n', text)
            text = text.strip()
            
            return text
        except Exception:
            return ''
    
    def get_areas(self):
        """Получение списка всех регионов"""
        areas = self._make_request(f"{self.base_url}/areas")
        
        if not areas:
            # Возвращаем основные регионы по умолчанию
            return [
                {'id': 113, 'name': 'Россия', 'type': 'country'},
                {'id': 1, 'name': 'Москва', 'type': 'city'},
                {'id': 2, 'name': 'Санкт-Петербург', 'type': 'city'},
            ]
        
        # Извлекаем основные регионы (страны и крупные города)
        main_areas = []
        
        for country in areas:
            if country['name'] in ['Россия', 'Российская Федерация']:
                main_areas.append({
                    'id': country['id'],
                    'name': country['name'],
                    'type': 'country'
                })
                
                # Добавляем крупные города России
                for region in country.get('areas', []):
                    if region['name'] in ['Москва', 'Санкт-Петербург', 'Новосибирск', 'Екатеринбург', 'Казань', 'Нижний Новгород']:
                        main_areas.append({
                            'id': region['id'],
                            'name': region['name'],
                            'type': 'city'
                        })
        
        return main_areas
    
    def get_professional_roles(self, category_id: Optional[str] = None):
        """
        Получение списка профессиональных ролей.

        Args:
            category_id: ID категории для фильтрации (например, '11' для IT).
                        Если не задан, возвращаются все роли всех категорий.
        """
        roles = self._make_request(f"{self.base_url}/professional_roles")
        
        if not roles:
            return []
        
        categories = roles.get('categories', [])

        if category_id:
            target_category = next(
                (category for category in categories if str(category.get('id')) == str(category_id)),
                None
            )
            if not target_category:
                logger.warning('Категория профессиональных ролей %s не найдена', category_id)
                return []

            return [
                {
                    'id': role['id'],
                    'name': role['name']
                }
                for role in target_category.get('roles', [])
            ]

        # Получаем все роли
        all_roles = []
        for category in categories:
            for role in category.get('roles', []):
                all_roles.append({
                    'id': role['id'],
                    'name': role['name']
                })

        return all_roles
    
    def search_all_vacancies(self, area_id, page=0, per_page=100):
        """Поиск всех вакансий в регионе"""
        params = {
            'per_page': per_page,
            'page': page,
            'area': area_id,
            'order_by': 'publication_time'
        }
        return self._make_request(f"{self.base_url}/vacancies", params=params)


def parse_vacancies_by_text(text_list, area=113, pages=2, delay=1.0, get_details=True,
                           date_from=None, date_to=None):
    """
    Парсинг вакансий по списку текстовых запросов

    Args:
        text_list (list): Список текстов для поиска (например: ["Python разработчик", "Java программист"])
        area (int): ID региона (1 - Москва, 2 - СПб, 113 - Россия)
        pages (int): Количество страниц для каждого запроса
        delay (float): Задержка между запросами в секундах
        get_details (bool): Получать ли детальную информацию о вакансиях
        date_from (str): Дата публикации от (формат YYYY-MM-DD)
        date_to (str): Дата публикации до (формат YYYY-MM-DD)

    Returns:
        dict: Статистика парсинга
    """
    # Создаём метрики и парсер
    metrics = ParsingMetrics()
    parser = HeadHunterParser(metrics=metrics)
    
    # Загружаем существующие ID для проверки дубликатов
    existing_hh_ids = set(Vacancy.objects.values_list('hh_id', flat=True))
    logger.info('Загружено %d существующих вакансий для проверки дубликатов', len(existing_hh_ids))
    
    total_vacancies = 0
    total_new_vacancies = 0
    total_updated_vacancies = 0
    
    for i, text in enumerate(text_list, 1):
        print(f'\n[{i}/{len(text_list)}] Парсинг запроса: "{text}"')
        
        vacancies_to_save = []
        query_vacancies = 0
        query_new_vacancies = 0
        query_updated_vacancies = 0
        total_available_pages = pages  # Будет обновлено после первого запроса
        
        for page in range(pages):
            # Пропускаем страницы, которых не существует
            if page >= total_available_pages:
                logger.debug('Страница %d не существует (всего %d)', page + 1, total_available_pages)
                break
            
            print(f'  Страница {page + 1} из {min(pages, total_available_pages)}...')
            
            # Поиск вакансий
            search_result = parser.search_vacancies(
                text=text,
                area=area,
                per_page=100,
                page=page,
                date_from=date_from,
                date_to=date_to
            )
            
            if not search_result:
                print(f'  Не удалось получить данные для страницы {page + 1}')
                continue
            
            # Обновляем информацию о доступных страницах (только на первой странице)
            if page == 0:
                total_found = search_result.get('found', 0)
                total_available_pages = min(search_result.get('pages', 1), pages, 20)  # API лимит 20 страниц
                logger.info('Запрос "%s": найдено %d вакансий, доступно %d страниц', 
                           text, total_found, total_available_pages)

            vacancies = search_result.get('items', [])
            query_vacancies += len(vacancies)

            if not vacancies:
                logger.debug('Вакансии не найдены на странице %d', page + 1)
                break
            
            # Парсинг каждой вакансии
            for j, vacancy_data in enumerate(vacancies, 1):
                vacancy_id = vacancy_data.get('id')
                vacancy_title = vacancy_data.get('name', 'Без названия')
                company_name = (vacancy_data.get('employer') or {}).get('name', 'Не указано')
                city = (vacancy_data.get('area') or {}).get('name', 'не указан')
                
                print(f'    [{j}/{len(vacancies)}] {city} | {vacancy_title} | {company_name}', end=' ')
                
                # Пропускаем уже существующие вакансии
                if vacancy_id in existing_hh_ids:
                    print('Уже существует. ')
                    continue
                
                # Получаем детальную информацию о вакансии для навыков
                if get_details and vacancy_id:
                    detailed_vacancy = parser.get_vacancy_details(vacancy_id)
                    if detailed_vacancy:
                        # Сохраняем snippet из поисковых данных, т.к. в детальных данных его нет
                        search_snippet = vacancy_data.get('snippet')
                        vacancy_data = detailed_vacancy
                        # Восстанавливаем snippet если его нет в детальных данных
                        if search_snippet and not vacancy_data.get('snippet'):
                            vacancy_data['snippet'] = search_snippet
                
                vacancy = parser.parse_vacancy(vacancy_data)
                if vacancy:
                    # Проверяем, существует ли вакансия
                    existing_vacancy = Vacancy.objects.filter(hh_id=vacancy_id).first()
                    
                    if existing_vacancy:
                        # Проверяем, есть ли изменения
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
                            # Создаем новую версию с историей изменений
                            existing_vacancy.create_version(new_data)
                            # Обновляем данные вакансии
                            for field, value in new_data.items():
                                setattr(existing_vacancy, field, value)
                            existing_vacancy.save()
                            print('обновлена (новая версия)')
                            query_updated_vacancies += 1
                        else:
                            print('без изменений')
                    else:
                        # Новая вакансия
                        vacancies_to_save.append(vacancy)
                        existing_hh_ids.add(vacancy_id)
                        print('новая вакансия')
                        query_new_vacancies += 1
                else:
                    print('ошибка парсинга')
                
                # Небольшая задержка между запросами детальной информации
                if get_details:
                    time.sleep(0.1)
            
            # Задержка между страницами
            if page < pages - 1:
                time.sleep(0.5)
        
        # Массовое сохранение вакансий для этого запроса
        if vacancies_to_save:
            Vacancy.objects.bulk_create(vacancies_to_save, ignore_conflicts=True)
            new_vacancies = len(vacancies_to_save)
            print(f'  Сохранено {new_vacancies} новых вакансий')
            total_new_vacancies += new_vacancies
        else:
            print(f'  Новых вакансий не найдено')

        # Выводим статистику по обновлениям
        if query_updated_vacancies > 0:
            logger.info('Создано %d новых версий вакансий', query_updated_vacancies)
            total_updated_vacancies += query_updated_vacancies
        
        total_vacancies += query_vacancies
        
        # Задержка между запросами
        if i < len(text_list):
            time.sleep(delay)
    
    # Обновляем метрики
    metrics.new_vacancies = total_new_vacancies
    metrics.updated_vacancies = total_updated_vacancies
    
    # Логируем сводку
    metrics.log_summary()
    
    return {
        'total_vacancies': total_vacancies,
        'new_vacancies': total_new_vacancies,
        'updated_vacancies': total_updated_vacancies,
        'total_in_db': Vacancy.objects.count(),
        'metrics': metrics.to_dict()
    }


def parse_all_vacancies(pages_per_area=5, delay=1.0, max_total_pages=100, areas_only=False):
    """
    Универсальный парсинг всех вакансий по регионам и ролям
    
    Args:
        pages_per_area (int): Количество страниц для каждого региона
        delay (float): Задержка между запросами в секундах
        max_total_pages (int): Максимальное общее количество страниц
        areas_only (bool): Парсить только по регионам (без ролей)
    
    Returns:
        dict: Статистика парсинга
    """
    # Создаём метрики и парсер
    metrics = ParsingMetrics()
    parser = HeadHunterParser(metrics=metrics)
    
    # Получаем регионы
    areas = parser.get_areas()
    print(f'Найдено {len(areas)} регионов для парсинга')
    
    # Получаем профессиональные роли (если нужно)
    roles = []
    if not areas_only:
        roles = parser.get_professional_roles()
        print(f'Найдено {len(roles)} профессиональных ролей для парсинга')
    
    # Загружаем существующие ID для проверки дубликатов
    existing_hh_ids = set(Vacancy.objects.values_list('hh_id', flat=True))
    print(f'Загружено {len(existing_hh_ids)} существующих вакансий для проверки дубликатов')
    
    total_vacancies = 0
    total_new_vacancies = 0
    total_updated_vacancies = 0
    total_pages_processed = 0
    
    # Парсинг по регионам
    for i, area in enumerate(areas, 1):
        if total_pages_processed >= max_total_pages:
            print(f'Достигнут лимит страниц ({max_total_pages}). Останавливаем парсинг.')
            break
        
        print(f'\n[{i}/{len(areas)}] Парсинг региона: {area["name"]} (ID: {area["id"]})')
        
        area_vacancies, area_new_vacancies, area_updated_vacancies, pages_processed = _parse_area(
            parser, area, existing_hh_ids, pages_per_area
        )
        
        total_vacancies += area_vacancies
        total_new_vacancies += area_new_vacancies
        total_updated_vacancies += area_updated_vacancies
        total_pages_processed += pages_processed
        
        print(f'Результат: {area_vacancies} обработано, {area_new_vacancies} новых, {area_updated_vacancies} обновлено, {pages_processed} страниц')
        
        # Задержка между регионами
        if i < len(areas):
            print(f'Ожидание {delay} сек перед следующим регионом...')
            time.sleep(delay)
    
    # Парсинг по профессиональным ролям (если включено)
    if roles and not areas_only:
        print(f'\nНачинаем парсинг по {len(roles)} профессиональным ролям...')
        
        for i, role in enumerate(roles, 1):
            if total_pages_processed >= max_total_pages:
                break
            
            print(f'\n[{i}/{len(roles)}] Парсинг роли: {role["name"]} (ID: {role["id"]})')
            
            role_vacancies, role_new_vacancies, role_updated_vacancies, pages_processed = _parse_role(
                parser, role, existing_hh_ids, pages_per_area
            )
            
            total_vacancies += role_vacancies
            total_new_vacancies += role_new_vacancies
            total_updated_vacancies += role_updated_vacancies
            total_pages_processed += pages_processed
            
            print(f'Результат: {role_vacancies} обработано, {role_new_vacancies} новых, {role_updated_vacancies} обновлено, {pages_processed} страниц')
            
            # Задержка между ролями
            if i < len(roles):
                time.sleep(delay)
    
    # Обновляем метрики
    metrics.new_vacancies = total_new_vacancies
    metrics.updated_vacancies = total_updated_vacancies
    
    # Логируем сводку
    metrics.log_summary()
    
    return {
        'areas_processed': len(areas),
        'roles_processed': len(roles) if not areas_only else 0,
        'pages_processed': total_pages_processed,
        'total_vacancies': total_vacancies,
        'new_vacancies': total_new_vacancies,
        'updated_vacancies': total_updated_vacancies,
        'total_in_db': Vacancy.objects.count(),
        'metrics': metrics.to_dict()
    }


def _parse_area(parser, area, existing_hh_ids, pages):
    """Парсинг вакансий по региону"""
    vacancies_to_save = []
    total_vacancies = 0
    total_updated_vacancies = 0
    pages_processed = 0
    total_available_pages = pages
    
    for page in range(pages):
        # Пропускаем страницы, которых не существует
        if page >= total_available_pages:
            break
        
        search_result = parser.search_all_vacancies(
            area_id=area['id'],
            page=page,
            per_page=100
        )
        
        if not search_result:
            print(f'  Не удалось получить данные для страницы {page + 1}')
            continue
        
        # Обновляем информацию о доступных страницах
        if page == 0:
            total_available_pages = min(search_result.get('pages', 1), pages, 20)
        
        vacancies = search_result.get('items', [])
        total_vacancies += len(vacancies)
        pages_processed += 1
        
        if not vacancies:
            break
        
        # Парсинг каждой вакансии
        for j, vacancy_data in enumerate(vacancies, 1):
            vacancy_id = vacancy_data.get('id')
            vacancy_title = vacancy_data.get('name', 'Без названия')
            company_name = (vacancy_data.get('employer') or {}).get('name', 'Не указано')
            city = (vacancy_data.get('area') or {}).get('name', 'не указан')
            
            print(f'    [{j}/{len(vacancies)}] {city} | {vacancy_title} | {company_name}', end=' ')
            
            # Пропускаем уже существующие вакансии
            if vacancy_id in existing_hh_ids:
                print('Уже существует.')
                continue
            
            # Получаем детальную информацию о вакансии
            if vacancy_id:
                detailed_vacancy = parser.get_vacancy_details(vacancy_id)
                if detailed_vacancy:
                    # Сохраняем snippet из поисковых данных
                    search_snippet = vacancy_data.get('snippet')
                    vacancy_data = detailed_vacancy
                    # Восстанавливаем snippet если его нет в детальных данных
                    if search_snippet and not vacancy_data.get('snippet'):
                        vacancy_data['snippet'] = search_snippet
            
            # Проверяем, что у нас есть данные для парсинга
            if not vacancy_data:
                print('нет данных для парсинга')
                continue
                
            vacancy = parser.parse_vacancy(vacancy_data)
            if vacancy:
                # Проверяем, существует ли вакансия
                existing_vacancy = Vacancy.objects.filter(hh_id=vacancy_id).first()
                
                if existing_vacancy:
                    # Проверяем, есть ли изменения
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
                        # Создаем новую версию с историей изменений
                        existing_vacancy.create_version(new_data)
                        # Обновляем данные вакансии
                        for field, value in new_data.items():
                            setattr(existing_vacancy, field, value)
                        existing_vacancy.save()
                        print('обновлена (новая версия)')
                        total_updated_vacancies += 1
                    else:
                        print('без изменений')
                else:
                    # Новая вакансия
                    vacancies_to_save.append(vacancy)
                    existing_hh_ids.add(vacancy_id)
                    print('новая вакансия')
            else:
                print('ошибка парсинга')
            
            # Задержка между запросами детальной информации
            time.sleep(0.1)
        
        # Задержка между страницами
        if page < pages - 1:
            time.sleep(0.5)
    
    # Массовое сохранение вакансий
    if vacancies_to_save:
        print(f'  Сохранение {len(vacancies_to_save)} вакансий в базу данных...')
        Vacancy.objects.bulk_create(vacancies_to_save, ignore_conflicts=True)
        print(f'  Сохранено {len(vacancies_to_save)} вакансий')
        return total_vacancies, len(vacancies_to_save), total_updated_vacancies, pages_processed
    else:
        print(f'  Новых вакансий не найдено')
        return total_vacancies, 0, total_updated_vacancies, pages_processed


def _parse_role(parser, role, existing_hh_ids, pages):
    """Парсинг вакансий по профессиональной роли"""
    vacancies_to_save = []
    total_vacancies = 0
    total_updated_vacancies = 0
    pages_processed = 0
    total_available_pages = pages
    
    for page in range(pages):
        # Пропускаем страницы, которых не существует
        if page >= total_available_pages:
            break
        
        # Поиск вакансий по роли
        search_result = parser.search_vacancies(
            professional_role=role['id'],
            per_page=100,
            page=page
        )
        
        if not search_result:
            print(f'  Не удалось получить данные для страницы {page + 1}')
            continue
        
        # Обновляем информацию о доступных страницах
        if page == 0:
            total_available_pages = min(search_result.get('pages', 1), pages, 20)
        
        vacancies = search_result.get('items', [])
        total_vacancies += len(vacancies)
        pages_processed += 1
        
        if not vacancies:
            break
        
        # Парсинг каждой вакансии
        for j, vacancy_data in enumerate(vacancies, 1):
            vacancy_id = vacancy_data.get('id')
            vacancy_title = vacancy_data.get('name', 'Без названия')
            company_name = (vacancy_data.get('employer') or {}).get('name', 'Не указано')
            city = (vacancy_data.get('area') or {}).get('name', 'не указан')
            
            print(f'    [{j}/{len(vacancies)}] {city} | {vacancy_title} | {company_name}', end=' ')
            
            # Пропускаем уже существующие вакансии
            if vacancy_id in existing_hh_ids:
                print('Уже существует.')
                continue
            
            # Получаем детальную информацию о вакансии
            if vacancy_id:
                detailed_vacancy = parser.get_vacancy_details(vacancy_id)
                if detailed_vacancy:
                    # Сохраняем snippet из поисковых данных
                    search_snippet = vacancy_data.get('snippet')
                    vacancy_data = detailed_vacancy
                    # Восстанавливаем snippet если его нет в детальных данных
                    if search_snippet and not vacancy_data.get('snippet'):
                        vacancy_data['snippet'] = search_snippet
            
            # Проверяем, что у нас есть данные для парсинга
            if not vacancy_data:
                print('нет данных для парсинга')
                continue
                
            vacancy = parser.parse_vacancy(vacancy_data)
            if vacancy:
                # Проверяем, существует ли вакансия
                existing_vacancy = Vacancy.objects.filter(hh_id=vacancy_id).first()
                
                if existing_vacancy:
                    # Проверяем, есть ли изменения
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
                        # Создаем новую версию с историей изменений
                        existing_vacancy.create_version(new_data)
                        # Обновляем данные вакансии
                        for field, value in new_data.items():
                            setattr(existing_vacancy, field, value)
                        existing_vacancy.save()
                        print('обновлена (новая версия)')
                        total_updated_vacancies += 1
                    else:
                        print('без изменений')
                else:
                    # Новая вакансия
                    vacancies_to_save.append(vacancy)
                    existing_hh_ids.add(vacancy_id)
                    print('новая вакансия')
            else:
                print('ошибка парсинга')
            
            # Задержка между запросами детальной информации
            time.sleep(0.1)
        
        # Задержка между страницами
        if page < pages - 1:
            time.sleep(0.5)
    
    # Массовое сохранение вакансий
    if vacancies_to_save:
        print(f'  Сохранение {len(vacancies_to_save)} вакансий в базу данных...')
        Vacancy.objects.bulk_create(vacancies_to_save, ignore_conflicts=True)
        print(f'  Сохранено {len(vacancies_to_save)} вакансий')
        return total_vacancies, len(vacancies_to_save), total_updated_vacancies, pages_processed
    else:
        print(f'  Новых вакансий не найдено')
        return total_vacancies, 0, total_updated_vacancies, pages_processed 