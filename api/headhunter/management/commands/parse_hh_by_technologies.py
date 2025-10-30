"""
Команда для парсинга вакансий HeadHunter по технологиям из базы данных.

Автоматически генерирует поисковые запросы на основе технологий
и запускает парсинг через Celery.
"""

import logging
import time
import sys
from django.core.management.base import BaseCommand

from modules.vacancies_parser.api.headhunter.tasks import (
    parse_vacancies_by_technologies,
    parse_vacancies_by_category
)

logger = logging.getLogger('modules.vacancies_parser.headhunter')


class Command(BaseCommand):
    help = 'Парсинг вакансий HeadHunter по технологиям из базы данных'

    def add_arguments(self, parser):
        parser.add_argument(
            '--category',
            type=str,
            help='Категория технологий (LANG, FRAMEWORK, DB, TOOL, PLATFORM, PROTOCOL, LIBRARY, SERVICE)'
        )
        parser.add_argument(
            '--categories',
            type=str,
            nargs='+',
            help='Список категорий технологий'
        )
        parser.add_argument(
            '--top',
            type=int,
            default=50,
            help='Количество топовых технологий (по умолчанию 50)'
        )
        parser.add_argument(
            '--use-aliases',
            action='store_true',
            help='Использовать алиасы технологий как отдельные запросы'
        )
        parser.add_argument(
            '--area',
            type=int,
            default=113,
            help='ID региона (по умолчанию 113 = Россия)'
        )
        parser.add_argument(
            '--pages',
            type=int,
            default=2,
            help='Количество страниц для парсинга на запрос (по умолчанию 2)'
        )
        parser.add_argument(
            '--delay',
            type=float,
            default=1.5,
            help='Задержка между запросами в секундах (по умолчанию 1.5)'
        )
        parser.add_argument(
            '--no-details',
            action='store_true',
            help='Не получать детальную информацию (быстрее)'
        )
        parser.add_argument(
            '--max-queries',
            type=int,
            help='Максимальное количество поисковых запросов'
        )
        parser.add_argument(
            '--wait',
            action='store_true',
            help='Дождаться завершения задачи Celery и вывести результат'
        )

    def handle(self, *args, **options):
        self.stdout.write('=' * 70)
        self.stdout.write('=== Парсинг вакансий по технологиям ===')
        self.stdout.write('=' * 70)
        
        category = options.get('category')
        categories = options.get('categories')
        top_n = options.get('top')
        use_aliases = options.get('use_aliases')
        area = options.get('area')
        pages = options.get('pages')
        delay = options.get('delay')
        get_details = not options.get('no_details')
        max_queries = options.get('max_queries')
        wait = options.get('wait')
        
        # Вывод параметров
        self.stdout.write('Параметры парсинга:')
        if category:
            self.stdout.write(f'   Категория: {category}')
        elif categories:
            self.stdout.write(f'   Категории: {", ".join(categories)}')
        else:
            self.stdout.write(f'   Топ технологий: {top_n}')
        
        self.stdout.write(f'   Использовать алиасы: {"Да" if use_aliases else "Нет"}')
        self.stdout.write(f'   Регион: {area}')
        self.stdout.write(f'   Страниц на запрос: {pages}')
        self.stdout.write(f'   Задержка: {delay} сек')
        self.stdout.write(f'   Детальная информация: {"Да" if get_details else "Нет"}')
        if max_queries:
            self.stdout.write(f'   Макс. запросов: {max_queries}')
        
        self.stdout.write('\n' + '=' * 70 + '\n')
        
        try:
            # Запуск задачи
            if category:
                # Парсинг по конкретной категории
                self.stdout.write(f'Запуск парсинга по категории: {category}')
                task = parse_vacancies_by_category.delay(
                    category=category,
                    use_aliases=use_aliases,
                    area=area,
                    pages=pages,
                    delay=delay,
                    get_details=get_details,
                    max_queries=max_queries or 50
                )
            else:
                # Парсинг по топовым технологиям или списку категорий
                self.stdout.write('Запуск парсинга по технологиям')
                task = parse_vacancies_by_technologies.delay(
                    categories=categories,
                    top_n=top_n,
                    use_aliases=use_aliases,
                    area=area,
                    pages=pages,
                    delay=delay,
                    get_details=get_details,
                    max_queries=max_queries
                )
            
            self.stdout.write(f'Задача Celery отправлена! Task ID: {task.id}')

            if wait:
                self.stdout.write('Ожидание завершения задачи...')
                spinner = ['|', '/', '-', '\\']
                i = 0

                while not task.ready():
                    sys.stdout.write(f'\rВыполняется... {spinner[i % 4]}')
                    sys.stdout.flush()
                    time.sleep(2)
                    i += 1

                sys.stdout.write('\r')

                if task.successful():
                    result = task.get()
                    self.stdout.write('Задача завершена!')
                    self._print_result(result)
                else:
                    self.stdout.write(f'Ошибка при выполнении: {task.result}')
            else:
                self.stdout.write('Проверьте статус задачи через Celery Flower или Django shell.')
        
        except Exception as e:
            self.stdout.write(f'Ошибка: {e}')
            logger.exception('Ошибка при запуске парсинга по технологиям')
    
    def _print_result(self, result):
        """Вывод результатов парсинга."""
        if result.get('error'):
            self.stdout.write(f'Ошибка: {result["error"]}')
            return

        self.stdout.write('\n=== РЕЗУЛЬТАТЫ ПАРСИНГА ===')

        mode = result.get('mode', 'unknown')

        if mode == 'by_technologies':
            self.stdout.write(f"Использовано технологий: {result.get('technologies_count', 0)}")
            self.stdout.write(f"Поисковых запросов: {result.get('search_queries_count', 0)}")

            if result.get('search_queries'):
                self.stdout.write('   Примеры запросов:')
                for query in result['search_queries'][:10]:
                    self.stdout.write(f'     - {query}')

        elif mode == 'by_category':
            self.stdout.write(f"Категория: {result.get('category', 'N/A')}")
            self.stdout.write(f"Поисковых запросов: {result.get('search_queries_count', 0)}")

            if result.get('search_queries'):
                self.stdout.write('   Запросы:')
                for query in result['search_queries'][:10]:
                    self.stdout.write(f'     - {query}')

        self.stdout.write('')
        self.stdout.write(f"Всего обработано вакансий: {result.get('total_vacancies', 0)}")
        self.stdout.write(f"Новых вакансий: {result.get('new_vacancies', 0)}")
        self.stdout.write(f"Обновлено вакансий: {result.get('updated_vacancies', 0)}")
        self.stdout.write(f"Всего в базе данных: {result.get('total_in_db', 0)}")

