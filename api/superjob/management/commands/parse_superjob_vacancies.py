import json
import os
import traceback

from django.core.management.base import BaseCommand

from ...scripts import (
    parse_vacancies_by_text,
    parse_all_vacancies,
    get_vacancy_details,
)
from ...tasks import (
    parse_superjob_vacancies_task,
    parse_all_superjob_vacancies_task,
    get_superjob_vacancy_details_task,
)


class Command(BaseCommand):
    help = 'Парсинг вакансий с SuperJob'

    def add_arguments(self, parser):
        parser.add_argument(
            '--config',
            type=str,
            default='config.json',
            help='Путь к JSON конфигурационному файлу (по умолчанию config.json)',
        )
        parser.add_argument(
            '--api-key',
            type=str,
            help='API ключ SuperJob (переопределяет config и env)',
        )
        parser.add_argument(
            '--text',
            type=str,
            help='Текст для поиска вакансий (переопределяет config)',
        )
        parser.add_argument(
            '--town',
            type=str,
            help='Город для поиска (переопределяет config)',
        )
        parser.add_argument(
            '--max-pages',
            type=int,
            help='Максимальное количество страниц (переопределяет config)',
        )
        parser.add_argument(
            '--delay',
            type=float,
            help='Задержка между запросами в секундах (переопределяет config)',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Универсальный парсинг по всем популярным запросам',
        )
        parser.add_argument(
            '--vacancy-id',
            type=str,
            help='Получить детали конкретной вакансии по ID',
        )
        parser.add_argument(
            '--celery',
            action='store_true',
            help='Запустить парсинг через Celery',
        )
        parser.add_argument(
            '--wait',
            action='store_true',
            help='Дождаться завершения задачи Celery и вывести результат',
        )

    def load_config(self, config_path):
        try:
            if not os.path.isabs(config_path):
                current_dir = os.path.dirname(os.path.abspath(__file__))
                config_path = os.path.join(current_dir, config_path)

            if not os.path.exists(config_path):
                self.stdout.write(
                    self.style.WARNING(
                        f'Конфигурационный файл {config_path} не найден. '
                        'Используем значения по умолчанию.'
                    )
                )
                return {}

            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            self.stdout.write(
                self.style.SUCCESS(f'Конфигурация загружена из {config_path}')
            )
            return config

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка при загрузке конфигурации: {e}')
            )
            return {}

    def print_formatted_result(self, result):
        if not isinstance(result, dict):
            self.stdout.write(f"Результат: {result}")
            return

        result_status = result.get('status')
        if result_status == 'SUCCESS':
            self.stdout.write(
                self.style.SUCCESS(result.get('message', 'Задача выполнена успешно'))
            )
            stats = result.get('result')
            if isinstance(stats, dict):
                self.stdout.write("Статистика:")
                self.stdout.write(f"   Всего найдено: {stats.get('total_vacancies', 0)}")
                self.stdout.write(f"   Сохранено: {stats.get('saved_vacancies', stats.get('total_saved', 0))}")
                self.stdout.write(f"   Обновлено: {stats.get('updated_vacancies', stats.get('total_updated', 0))}")
                self.stdout.write(f"   Ошибок: {stats.get('errors', stats.get('total_errors', 0))}")
        elif result_status == 'FAILURE':
            self.stdout.write(
                self.style.ERROR(result.get('message', 'Произошла ошибка'))
            )
            if 'error' in result:
                self.stdout.write(f"Детали ошибки: {result['error']}")
        else:
            self.stdout.write(f"Результат: {result}")

    def handle(self, *args, **options):
        config = self.load_config(options['config'])

        api_key = (
            options.get('api_key')
            or config.get('api_key')
            or os.environ.get('SUPERJOB_API_KEY')
        )
        text = options.get('text') or config.get('search_queries', [None])[0]
        town = options.get('town') or config.get('town')
        max_pages = options.get('max_pages') or config.get('max_pages', 5)
        delay = options.get('delay') or config.get('delay', 1.0)
        parse_all_flag = options.get('all', False)
        vacancy_id = options.get('vacancy_id')
        use_celery = options.get('celery', False)
        wait_for_result = options.get('wait', False)

        if not api_key:
            self.stdout.write(
                self.style.ERROR('Ошибка: Не указан API ключ SuperJob')
            )
            self.stdout.write(
                self.style.WARNING(
                    'Укажите ключ в config.json, через --api-key '
                    'или в переменной окружения SUPERJOB_API_KEY'
                )
            )
            return

        key_display = f"{'*' * 10}{api_key[-4:]}" if len(api_key) > 4 else '****'
        self.stdout.write("Параметры парсинга:")
        self.stdout.write(f"   API Key: {key_display}")
        self.stdout.write(f"   Страниц: {max_pages}")
        self.stdout.write(f"   Задержка: {delay}с")
        self.stdout.write(f"   Город: {town or 'Не указан'}")
        self.stdout.write(f"   Celery: {'Да' if use_celery else 'Нет'}")

        if vacancy_id:
            self.stdout.write(f"   Режим: Детали вакансии {vacancy_id}")
        elif parse_all_flag:
            self.stdout.write("   Режим: Универсальный парсинг")
        else:
            self.stdout.write(f"   Режим: Поиск по тексту '{text}'")

        try:
            if use_celery:
                task = self._run_celery_task(
                    api_key, text, town, max_pages, delay,
                    parse_all_flag, vacancy_id
                )
                self.stdout.write(f"Задача Celery запущена с ID: {task.id}")

                if wait_for_result:
                    self.stdout.write("Ожидаем завершения задачи...")
                    result = task.get()
                    self.print_formatted_result(result)
                else:
                    self.stdout.write(
                        self.style.SUCCESS("Задача отправлена в очередь Celery")
                    )
            else:
                result = self._run_sync(
                    api_key, text, town, max_pages, delay,
                    parse_all_flag, vacancy_id
                )
                self.print_formatted_result(result)

        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING("\nПарсинг прерван пользователем")
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Ошибка при выполнении парсинга: {e}")
            )
            traceback.print_exc()

    def _run_celery_task(self, api_key, text, town, max_pages, delay,
                         parse_all_flag, vacancy_id):
        if vacancy_id:
            return get_superjob_vacancy_details_task.delay(
                vacancy_id=str(vacancy_id), api_key=api_key
            )
        if parse_all_flag:
            return parse_all_superjob_vacancies_task.delay(
                max_pages_per_query=max_pages, delay=delay, api_key=api_key
            )
        return parse_superjob_vacancies_task.delay(
            text=text, town=town, max_pages=max_pages,
            delay=delay, api_key=api_key
        )

    def _run_sync(self, api_key, text, town, max_pages, delay,
                  parse_all_flag, vacancy_id):
        if vacancy_id:
            self.stdout.write(f"Получаем детали вакансии {vacancy_id}...")
            details = get_vacancy_details(vacancy_id, api_key)
            if details:
                return {
                    'status': 'SUCCESS',
                    'result': details,
                    'message': f'Детали вакансии получены: {details.get("profession", vacancy_id)}',
                }
            return {
                'status': 'FAILURE',
                'error': 'Вакансия не найдена',
                'message': f'Не удалось получить детали вакансии {vacancy_id}',
            }

        if parse_all_flag:
            self.stdout.write("Начинаем универсальный парсинг...")
            result = parse_all_vacancies(
                max_pages_per_query=max_pages, delay=delay, api_key=api_key
            )
            return {'status': 'SUCCESS', 'result': result, 'message': 'Универсальный парсинг завершен'}

        if not text:
            return {
                'status': 'FAILURE',
                'error': 'Не указан текст для поиска',
                'message': 'Укажите --text или добавьте search_queries в config.json',
            }

        self.stdout.write(f"Начинаем парсинг по запросу '{text}'...")
        result = parse_vacancies_by_text(
            text=text, town=town, max_pages=max_pages,
            delay=delay, api_key=api_key
        )
        return {'status': 'SUCCESS', 'result': result, 'message': 'Парсинг завершен'}
