"""
Конфигурация Celery Beat для модуля SuperJob.
Настройка периодических задач парсинга вакансий.

Принципы расписания:
- Разнесение задач по времени для избежания конфликтов
- Интенсивный парсинг ночью, когда нагрузка на API минимальна
- Разные расписания для рабочих и выходных дней
- Приоритизация по типу задачи
- Учёт лимита SuperJob API: 120 запросов/минуту
"""

from typing import Dict, Any
from celery.schedules import crontab

from src.core.utils.celery_beat.base import CeleryBeatModuleConfig


IT_CATALOGUE_ID = 33


class SuperjobCeleryBeatConfig(CeleryBeatModuleConfig):
    """
    Конфигурация периодических задач для парсинга SuperJob.

    Доступные каталоги SuperJob (IT-сфера):
    - 33: Информационные технологии, интернет, телеком (основной)

    Ключевые задачи:
    - parse_superjob_by_catalogues_task: парсинг по каталогам (IT)
    - parse_superjob_vacancies_task: парсинг по текстовым запросам
    - parse_all_superjob_vacancies_task: универсальный парсинг по config.json
    """

    def __init__(self, module_name: str):
        super().__init__(module_name)

    def get_beat_schedule(self) -> Dict[str, Dict[str, Any]]:
        return {
            # ============================================================
            # ЕЖЕДНЕВНЫЙ ПАРСИНГ IT-КАТАЛОГА (высший приоритет)
            # Полный обход каталога 33 (IT) — основной источник вакансий
            # ============================================================
            'sj-daily-it-catalogue': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_superjob_by_catalogues_task',
                'schedule': crontab(minute=0, hour=2),
                'kwargs': {
                    'catalogue_ids': [IT_CATALOGUE_ID],
                    'max_pages_per_catalogue': 500,
                    'delay': 1.0,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 10,
                    'expires': 6 * 60 * 60,
                }
            },

            # ============================================================
            # ТЕКСТОВЫЙ ПУЛЬС — РАБОЧИЕ ДНИ (популярные технологии)
            # Быстрый обход по ключевым запросам для отлова свежих вакансий
            # ============================================================
            'sj-pulse-python-workdays': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_superjob_vacancies_task',
                'schedule': crontab(minute=15, hour=9, day_of_week='1-5'),
                'kwargs': {
                    'text': 'Python',
                    'max_pages': 10,
                    'delay': 1.0,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 8,
                    'expires': 3 * 60 * 60,
                }
            },
            'sj-pulse-javascript-workdays': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_superjob_vacancies_task',
                'schedule': crontab(minute=30, hour=9, day_of_week='1-5'),
                'kwargs': {
                    'text': 'JavaScript',
                    'max_pages': 10,
                    'delay': 1.0,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 8,
                    'expires': 3 * 60 * 60,
                }
            },
            'sj-pulse-java-workdays': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_superjob_vacancies_task',
                'schedule': crontab(minute=45, hour=9, day_of_week='1-5'),
                'kwargs': {
                    'text': 'Java',
                    'max_pages': 10,
                    'delay': 1.0,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 8,
                    'expires': 3 * 60 * 60,
                }
            },

            # ============================================================
            # ТЕКСТОВЫЙ ПУЛЬС — ДНЕВНОЙ (фреймворки и DevOps)
            # ============================================================
            'sj-pulse-react-noon': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_superjob_vacancies_task',
                'schedule': crontab(minute=15, hour=13, day_of_week='1-5'),
                'kwargs': {
                    'text': 'React',
                    'max_pages': 10,
                    'delay': 1.0,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 7,
                    'expires': 3 * 60 * 60,
                }
            },
            'sj-pulse-django-noon': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_superjob_vacancies_task',
                'schedule': crontab(minute=30, hour=13, day_of_week='1-5'),
                'kwargs': {
                    'text': 'Django',
                    'max_pages': 10,
                    'delay': 1.0,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 7,
                    'expires': 3 * 60 * 60,
                }
            },
            'sj-pulse-devops-noon': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_superjob_vacancies_task',
                'schedule': crontab(minute=45, hour=13, day_of_week='1-5'),
                'kwargs': {
                    'text': 'DevOps',
                    'max_pages': 10,
                    'delay': 1.0,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 7,
                    'expires': 3 * 60 * 60,
                }
            },

            # ============================================================
            # ТЕКСТОВЫЙ ПУЛЬС — ВЕЧЕРНИЙ (дополнительные технологии)
            # ============================================================
            'sj-pulse-vue-evening': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_superjob_vacancies_task',
                'schedule': crontab(minute=15, hour=18, day_of_week='1-5'),
                'kwargs': {
                    'text': 'Vue',
                    'max_pages': 10,
                    'delay': 1.0,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 6,
                    'expires': 3 * 60 * 60,
                }
            },

            # ============================================================
            # ВЫХОДНЫЕ — СОКРАЩЁННЫЙ ПУЛЬС (2 раза в день)
            # ============================================================
            'sj-pulse-weekend-morning': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_superjob_vacancies_task',
                'schedule': crontab(minute=15, hour=10, day_of_week='0,6'),
                'kwargs': {
                    'text': 'Python',
                    'max_pages': 10,
                    'delay': 1.5,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 5,
                    'expires': 6 * 60 * 60,
                }
            },
            'sj-pulse-weekend-evening': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_superjob_vacancies_task',
                'schedule': crontab(minute=15, hour=18, day_of_week='0,6'),
                'kwargs': {
                    'text': 'JavaScript',
                    'max_pages': 10,
                    'delay': 1.5,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 5,
                    'expires': 6 * 60 * 60,
                }
            },

            # ============================================================
            # ГЛУБОКОЕ НОЧНОЕ СКАНИРОВАНИЕ IT-КАТАЛОГА (с увеличенным delay)
            # Дополнительный проход по IT-каталогу для подбора пропущенных
            # ============================================================
            'sj-deep-it-scan-nightly': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_superjob_by_catalogues_task',
                'schedule': crontab(minute=30, hour=23),
                'kwargs': {
                    'catalogue_ids': [IT_CATALOGUE_ID],
                    'max_pages_per_catalogue': 500,
                    'delay': 1.5,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 6,
                    'expires': 6 * 60 * 60,
                }
            },

            # ============================================================
            # УНИВЕРСАЛЬНЫЙ ПАРСИНГ (ночью, по config.json search_queries)
            # Проходит по всем запросам из конфигурации
            # ============================================================
            'sj-universal-nightly': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_all_superjob_vacancies_task',
                'schedule': crontab(minute=0, hour=4),
                'kwargs': {
                    'max_pages_per_query': 5,
                    'delay': 1.5,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 5,
                    'expires': 6 * 60 * 60,
                }
            },

            # ============================================================
            # ЕЖЕНЕДЕЛЬНЫЙ ПОЛНЫЙ ПАРСИНГ (воскресенье, ночь)
            # Максимальная глубина по IT-каталогу + все текстовые запросы
            # ============================================================
            'sj-weekly-comprehensive-catalogues': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_superjob_by_catalogues_task',
                'schedule': crontab(minute=0, hour=1, day_of_week='sunday'),
                'kwargs': {
                    'catalogue_ids': [IT_CATALOGUE_ID],
                    'max_pages_per_catalogue': 500,
                    'delay': 1.0,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 9,
                    'expires': 8 * 60 * 60,
                }
            },
            'sj-weekly-comprehensive-universal': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_all_superjob_vacancies_task',
                'schedule': crontab(minute=0, hour=5, day_of_week='sunday'),
                'kwargs': {
                    'max_pages_per_query': 10,
                    'delay': 1.5,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 7,
                    'expires': 8 * 60 * 60,
                }
            },

            # ============================================================
            # МЕСЯЧНЫЙ ГЛУБОКИЙ ПАРСИНГ (1-е число, ночь)
            # Полный проход по IT-каталогу с максимальным покрытием
            # ============================================================
            'sj-monthly-deep-scan': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_superjob_by_catalogues_task',
                'schedule': crontab(minute=0, hour=0, day_of_month='1'),
                'kwargs': {
                    'catalogue_ids': [IT_CATALOGUE_ID],
                    'max_pages_per_catalogue': 500,
                    'delay': 0.8,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 9,
                    'expires': 12 * 60 * 60,
                }
            },

            # ============================================================
            # ПРОВЕРКА СТАТУСА ВАКАНСИЙ (рано утром)
            # Деактивация закрытых/архивных вакансий в БД
            # ============================================================
            'sj-check-vacancies-status': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.check_superjob_vacancies_status_task',
                'schedule': crontab(minute=0, hour=5),
                'kwargs': {
                    'batch_size': 50,
                    'max_vacancies': 800,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 2,
                    'expires': 6 * 60 * 60,
                }
            },
        }

    def get_additional_beat_config(self) -> Dict[str, Any]:
        return {
            'superjob_beat_enabled': True,
            'superjob_beat_max_interval': 300,
            'superjob_beat_sync_every': 60,
        }
