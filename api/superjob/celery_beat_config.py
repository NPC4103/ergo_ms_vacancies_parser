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
            # Первый ночной запуск дня: 02:00 (разведён с Habr 02:30)
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
            # МЕСЯЧНЫЙ ГЛУБОКИЙ ПАРСИНГ (monthly, 1-е число 01:00)
            # ============================================================
            'sj-monthly-deep-scan': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_superjob_by_catalogues_task',
                'schedule': crontab(minute=0, hour=1, day_of_month='1'),
                'kwargs': {
                    'catalogue_ids': [IT_CATALOGUE_ID],
                    'max_pages_per_catalogue': 500,
                    'delay': 1.2,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 9,
                    'expires': 12 * 60 * 60,
                }
            },

            # ============================================================
            # ЯЗЫКИ ПРОГРАММИРОВАНИЯ - РАБОЧИЕ ДНИ (3 раза/день)
            # ============================================================
            'sj-languages-workdays-morning': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_superjob_vacancies_task',
                'schedule': crontab(minute=30, hour=6, day_of_week='1-5'),
                'kwargs': {
                    'text': 'Python',
                    'max_pages': 20,
                    'delay': 1.5,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 8,
                    'expires': 4 * 60 * 60,
                }
            },
            'sj-languages-workdays-noon': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_superjob_vacancies_task',
                'schedule': crontab(minute=30, hour=12, day_of_week='1-5'),
                'kwargs': {
                    'text': 'JavaScript',
                    'max_pages': 20,
                    'delay': 1.5,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 8,
                    'expires': 4 * 60 * 60,
                }
            },
            'sj-languages-workdays-evening': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_superjob_vacancies_task',
                'schedule': crontab(minute=30, hour=18, day_of_week='1-5'),
                'kwargs': {
                    'text': 'Java',
                    'max_pages': 20,
                    'delay': 1.5,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 8,
                    'expires': 4 * 60 * 60,
                }
            },

            # ============================================================
            # ЯЗЫКИ ПРОГРАММИРОВАНИЯ - ВЫХОДНЫЕ (2 раза/день)
            # ============================================================
            'sj-languages-weekend-morning': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_superjob_vacancies_task',
                'schedule': crontab(minute=30, hour=10, day_of_week='0,6'),
                'kwargs': {
                    'text': 'Python',
                    'max_pages': 20,
                    'delay': 1.5,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 6,
                    'expires': 6 * 60 * 60,
                }
            },
            'sj-languages-weekend-evening': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_superjob_vacancies_task',
                'schedule': crontab(minute=30, hour=18, day_of_week='0,6'),
                'kwargs': {
                    'text': 'JavaScript',
                    'max_pages': 20,
                    'delay': 1.5,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 6,
                    'expires': 6 * 60 * 60,
                }
            },

            # ============================================================
            # ФРЕЙМВОРКИ - РАБОЧИЕ ДНИ (3 раза/день)
            # ============================================================
            'sj-frameworks-workdays-morning': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_superjob_vacancies_task',
                'schedule': crontab(minute=45, hour=7, day_of_week='1-5'),
                'kwargs': {
                    'text': 'React',
                    'max_pages': 25,
                    'delay': 1.5,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 7,
                    'expires': 4 * 60 * 60,
                }
            },
            'sj-frameworks-workdays-noon': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_superjob_vacancies_task',
                'schedule': crontab(minute=45, hour=13, day_of_week='1-5'),
                'kwargs': {
                    'text': 'Django',
                    'max_pages': 25,
                    'delay': 1.5,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 7,
                    'expires': 4 * 60 * 60,
                }
            },
            'sj-frameworks-workdays-evening': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_superjob_vacancies_task',
                'schedule': crontab(minute=45, hour=19, day_of_week='1-5'),
                'kwargs': {
                    'text': 'Spring',
                    'max_pages': 25,
                    'delay': 1.5,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 7,
                    'expires': 4 * 60 * 60,
                }
            },

            # ============================================================
            # ФРЕЙМВОРКИ - ВЫХОДНЫЕ (2 раза/день)
            # ============================================================
            'sj-frameworks-weekend-morning': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_superjob_vacancies_task',
                'schedule': crontab(minute=45, hour=11, day_of_week='0,6'),
                'kwargs': {
                    'text': 'React',
                    'max_pages': 25,
                    'delay': 1.5,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 5,
                    'expires': 6 * 60 * 60,
                }
            },
            'sj-frameworks-weekend-evening': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_superjob_vacancies_task',
                'schedule': crontab(minute=45, hour=19, day_of_week='0,6'),
                'kwargs': {
                    'text': 'Django',
                    'max_pages': 25,
                    'delay': 1.5,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 5,
                    'expires': 6 * 60 * 60,
                }
            },

            # ============================================================
            # РАННИЙ УТРЕННИЙ ЗАПУСК (чтобы данные были в течение дня после старта воркера)
            # ============================================================
            'sj-early-morning-pulse': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_superjob_vacancies_task',
                'schedule': crontab(minute=0, hour=8),
                'kwargs': {
                    'text': 'Python',
                    'max_pages': 10,
                    'delay': 1.2,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 8,
                    'expires': 2 * 60 * 60,
                }
            },

            # ============================================================
            # БАЗЫ ДАННЫХ (2 раза/день)
            # ============================================================
            'sj-databases-morning': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_superjob_vacancies_task',
                'schedule': crontab(minute=0, hour=9),
                'kwargs': {
                    'text': 'PostgreSQL',
                    'max_pages': 15,
                    'delay': 1.5,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 5,
                    'expires': 8 * 60 * 60,
                }
            },
            'sj-databases-evening': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_superjob_vacancies_task',
                'schedule': crontab(minute=0, hour=21),
                'kwargs': {
                    'text': 'SQL',
                    'max_pages': 15,
                    'delay': 1.5,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 5,
                    'expires': 8 * 60 * 60,
                }
            },

            # ============================================================
            # ИНСТРУМЕНТЫ (1 раз/день)
            # ============================================================
            'sj-tools-daily': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_superjob_vacancies_task',
                'schedule': crontab(minute=15, hour=14),
                'kwargs': {
                    'text': 'Git',
                    'max_pages': 15,
                    'delay': 1.5,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 4,
                    'expires': 12 * 60 * 60,
                }
            },

            # ============================================================
            # ПЛАТФОРМЫ (ночью)
            # ============================================================
            'sj-platforms-nightly': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_superjob_vacancies_task',
                'schedule': crontab(minute=45, hour=23),
                'kwargs': {
                    'text': 'Kubernetes',
                    'max_pages': 15,
                    'delay': 2.0,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 3,
                    'expires': 20 * 60 * 60,
                }
            },

            # ============================================================
            # ПУЛЬС ТОП-20 (рабочие дни каждые 3 часа)
            # ============================================================
            'sj-top20-pulse-09': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_all_superjob_vacancies_task',
                'schedule': crontab(minute=15, hour=9, day_of_week='1-5'),
                'kwargs': {
                    'max_pages_per_query': 1,
                    'delay': 1.0,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 9,
                    'expires': 2 * 60 * 60,
                }
            },
            'sj-top20-pulse-12': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_all_superjob_vacancies_task',
                'schedule': crontab(minute=15, hour=12, day_of_week='1-5'),
                'kwargs': {
                    'max_pages_per_query': 1,
                    'delay': 1.0,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 9,
                    'expires': 2 * 60 * 60,
                }
            },
            'sj-top20-pulse-15': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_all_superjob_vacancies_task',
                'schedule': crontab(minute=15, hour=15, day_of_week='1-5'),
                'kwargs': {
                    'max_pages_per_query': 1,
                    'delay': 1.0,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 9,
                    'expires': 2 * 60 * 60,
                }
            },
            'sj-top20-pulse-18': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_all_superjob_vacancies_task',
                'schedule': crontab(minute=15, hour=18, day_of_week='1-5'),
                'kwargs': {
                    'max_pages_per_query': 1,
                    'delay': 1.0,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 9,
                    'expires': 2 * 60 * 60,
                }
            },
            'sj-top20-pulse-21': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_all_superjob_vacancies_task',
                'schedule': crontab(minute=15, hour=21, day_of_week='1-5'),
                'kwargs': {
                    'max_pages_per_query': 1,
                    'delay': 1.0,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 9,
                    'expires': 2 * 60 * 60,
                }
            },

            # ============================================================
            # ГЛУБОКОЕ СКАНИРОВАНИЕ ТОП-40 (nightly deep)
            # ============================================================
            'sj-top40-deep-scan': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_all_superjob_vacancies_task',
                'schedule': crontab(minute=15, hour=3),
                'kwargs': {
                    'max_pages_per_query': 3,
                    'delay': 2.0,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 6,
                    'expires': 4 * 60 * 60,
                }
            },

            # ============================================================
            # ЕЖЕНЕДЕЛЬНЫЙ ПОЛНЫЙ ПАРСИНГ (weekly comprehensive)
            # ============================================================
            'sj-weekly-comprehensive': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.parse_all_superjob_vacancies_task',
                'schedule': crontab(minute=15, hour=4, day_of_week='sunday'),
                'kwargs': {
                    'max_pages_per_query': 8,
                    'delay': 2.5,
                },
                'options': {
                    'queue': 'superjob',
                    'priority': 7,
                    'expires': 6 * 60 * 60,
                }
            },

            # ============================================================
            # ПРОВЕРКА СТАТУСА ВАКАНСИЙ (рано утром)
            # Деактивация закрытых/архивных вакансий в БД
            # ============================================================
            'sj-check-vacancies-status': {
                'task': 'modules.vacancies_parser.api.superjob.tasks.check_superjob_vacancies_status_task',
                'schedule': crontab(minute=15, hour=5),
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
