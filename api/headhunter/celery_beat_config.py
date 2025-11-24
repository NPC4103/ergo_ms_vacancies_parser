"""
Конфигурация Celery Beat для модуля HeadHunter.
Настройка периодических задач парсинга вакансий.
"""

from typing import Dict, Any
from celery.schedules import crontab

from src.core.utils.celery_beat.base import CeleryBeatModuleConfig


class HeadhunterCeleryBeatConfig(CeleryBeatModuleConfig):
    """
    Конфигурация периодических задач для парсинга HeadHunter.
    """
    
    def get_beat_schedule(self) -> Dict[str, Dict[str, Any]]:
        """
        Расписание периодических задач для парсинга вакансий.
        
        Returns:
            Dict[str, Dict[str, Any]]: Расписание задач
        """
        return {
            # ============================================================
            # ПАРСИНГ ПО ЯЗЫКАМ ПРОГРАММИРОВАНИЯ (каждые 4 часа)
            # ============================================================
            'hh-parse-languages-every-4h': {
                'task': 'modules.vacancies_parser.api.headhunter.tasks.parse_vacancies_by_category',
                'schedule': crontab(minute=0, hour='*/4'),  # Каждые 4 часа
                'kwargs': {
                    'category': 'LANG',
                    'use_aliases': False,
                    'area': 113,  # Россия
                    'pages': 2,
                    'delay': 1.5,
                    'get_details': True,
                    'max_queries': 20
                },
                'options': {
                    'queue': 'headhunter',
                    'priority': 7,
                    'expires': 3 * 60 * 60,  # Не запускать следующую задачу, если текущая висит
                }
            },
            
            # ============================================================
            # ПАРСИНГ ПО ФРЕЙМВОРКАМ (каждые 6 часов)
            # ============================================================
            'hh-parse-frameworks-every-6h': {
                'task': 'modules.vacancies_parser.api.headhunter.tasks.parse_vacancies_by_category',
                'schedule': crontab(minute=30, hour='*/6'),  # Каждые 6 часов
                'kwargs': {
                    'category': 'FRAMEWORK',
                    'use_aliases': False,
                    'area': 113,
                    'pages': 2,
                    'delay': 1.5,
                    'get_details': True,
                    'max_queries': 25
                },
                'options': {
                    'queue': 'headhunter',
                    'priority': 6,
                    'expires': 4 * 60 * 60,
                }
            },
            
            # ============================================================
            # ПАРСИНГ ПО БАЗАМ ДАННЫХ (каждые 8 часов)
            # ============================================================
            'hh-parse-databases-every-8h': {
                'task': 'modules.vacancies_parser.api.headhunter.tasks.parse_vacancies_by_category',
                'schedule': crontab(minute=0, hour='*/8'),  # Каждые 8 часов
                'kwargs': {
                    'category': 'DB',
                    'use_aliases': False,
                    'area': 113,
                    'pages': 2,
                    'delay': 1.5,
                    'get_details': True,
                    'max_queries': 15
                },
                'options': {
                    'queue': 'headhunter',
                    'priority': 5,
                    'expires': 5 * 60 * 60,
                }
            },
            
            # ============================================================
            # ПАРСИНГ ПО ИНСТРУМЕНТАМ (каждые 12 часов)
            # ============================================================
            'hh-parse-tools-every-12h': {
                'task': 'modules.vacancies_parser.api.headhunter.tasks.parse_vacancies_by_category',
                'schedule': crontab(minute=0, hour='*/12'),  # Каждые 12 часов
                'kwargs': {
                    'category': 'TOOL',
                    'use_aliases': False,
                    'area': 113,
                    'pages': 2,
                    'delay': 1.5,
                    'get_details': True,
                    'max_queries': 15
                },
                'options': {
                    'queue': 'headhunter',
                    'priority': 4,
                    'expires': 6 * 60 * 60,
                }
            },
            
            # ============================================================
            # ЕЖЕНЕДЕЛЬНЫЙ ПАРСИНГ С АЛИАСАМИ (более широкий поиск)
            # ============================================================
            'hh-parse-top-technologies-weekly': {
                'task': 'modules.vacancies_parser.api.headhunter.tasks.parse_vacancies_by_technologies',
                'schedule': crontab(day_of_week='sunday', hour=10, minute=0),  # Каждое воскресенье в 10:00
                'kwargs': {
                    'categories': ['LANG', 'FRAMEWORK'],
                    'top_n': 50,
                    'use_aliases': True,  # С алиасами для более широкого поиска
                    'area': 113,
                    'pages': 2,
                    'delay': 2.5,
                    'get_details': True,
                    'max_queries': 100
                },
                'options': {
                    'queue': 'headhunter',
                    'priority': 6,
                    'expires': 2 * 60 * 60,
                }
            },
            
            # ============================================================
            # НОЧНОЙ ПАРСИНГ ПО ОБЛАЧНЫМ ПЛАТФОРМАМ
            # ============================================================
            'hh-parse-platforms-nightly': {
                'task': 'modules.vacancies_parser.api.headhunter.tasks.parse_vacancies_by_category',
                'schedule': crontab(hour=23, minute=30),  # Каждую ночь в 23:30
                'kwargs': {
                    'category': 'PLATFORM',
                    'use_aliases': True,
                    'area': 113,
                    'pages': 2,
                    'delay': 2.0,
                    'get_details': True,
                    'max_queries': 15
                },
                'options': {
                    'queue': 'headhunter',
                    'priority': 3,
                    'expires': 20 * 60 * 60,
                }
            },
            
            # ============================================================
            # БЫСТРЫЙ ПАРСИНГ КАЖДЫЕ 2 ЧАСА (топ-15 технологий)
            # ============================================================
            'hh-parse-top15-every-2h': {
                'task': 'modules.vacancies_parser.api.headhunter.tasks.parse_vacancies_by_technologies',
                'schedule': crontab(minute=15, hour='*/2'),  # Каждые 2 часа
                'kwargs': {
                    'categories': None,
                    'top_n': 15,
                    'use_aliases': False,
                    'area': 113,
                    'pages': 1,
                    'delay': 1.0,
                    'get_details': False,  # Без деталей - быстрее
                    'max_queries': 15
                },
                'options': {
                    'queue': 'headhunter',
                    'priority': 8,
                    'expires': 90 * 60,  # 1.5 часа
                }
            },
            
            # ============================================================
            # СРЕДНИЙ ПАРСИНГ КАЖДЫЕ 6 ЧАСОВ (топ-30 технологий)
            # ============================================================
            'hh-parse-top30-every-6h': {
                'task': 'modules.vacancies_parser.api.headhunter.tasks.parse_vacancies_by_technologies',
                'schedule': crontab(minute=0, hour='2,8,14,20'),  # 4 раза в день
                'kwargs': {
                    'categories': ['LANG', 'FRAMEWORK'],
                    'top_n': 30,
                    'use_aliases': False,
                    'area': 113,
                    'pages': 2,
                    'delay': 1.5,
                    'get_details': True,
                    'max_queries': 30
                },
                'options': {
                    'queue': 'headhunter',
                    'priority': 6,
                    'expires': 5 * 60 * 60,
                }
            },
            
            # ============================================================
            # ПРОВЕРКА СТАТУСА ВАКАНСИЙ (ежедневно в 04:00)
            # ============================================================
            'hh-check-vacancies-status-daily': {
                'task': 'modules.vacancies_parser.api.headhunter.tasks.check_vacancies_status_task',
                'schedule': crontab(hour=4, minute=0),  # Каждый день в 4:00
                'kwargs': {
                    'batch_size': 100,
                    'delay': 0.2,
                    'max_vacancies': 500  # Проверяем до 500 вакансий за раз
                },
                'options': {
                    'queue': 'headhunter',
                    'priority': 2,  # Низкий приоритет
                    'expires': 6 * 60 * 60,  # 6 часов
                }
            },
        }
    
    def get_additional_beat_config(self) -> Dict[str, Any]:
        """
        Дополнительные настройки для Beat планировщика.
        
        Returns:
            Dict[str, Any]: Дополнительные настройки
        """
        return {
            'headhunter_beat_enabled': True,
            'headhunter_beat_max_interval': 300,  # Максимальный интервал проверки в секундах
            'headhunter_beat_sync_every': 60,  # Синхронизация каждые 60 секунд
        }

