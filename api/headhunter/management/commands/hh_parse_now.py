"""
Команда для немедленного запуска парсинга вне очереди.

Позволяет быстро запустить парсинг не дожидаясь расписания.
"""

import logging
from django.core.management.base import BaseCommand

from modules.vacancies_parser.api.headhunter.tasks import (
    parse_vacancies_by_technologies,
    parse_vacancies_by_category
)

logger = logging.getLogger('modules.vacancies_parser.headhunter')


class Command(BaseCommand):
    help = 'Немедленный запуск парсинга вне очереди'

    def add_arguments(self, parser):
        parser.add_argument(
            '--preset',
            type=str,
            choices=['quick', 'normal', 'full', 'test'],
            default='quick',
            help='Пресет парсинга: quick (быстро), normal (обычный), full (полный), test (тест)'
        )
        parser.add_argument(
            '--category',
            type=str,
            help='Конкретная категория (LANG, FRAMEWORK, DB, TOOL, PLATFORM)'
        )
        parser.add_argument(
            '--async',
            action='store_true',
            help='Запустить асинхронно (в фоне), иначе с ожиданием'
        )

    def handle(self, *args, **options):
        preset = options.get('preset')
        category = options.get('category')
        is_async = options.get('async')

        self.stdout.write('=== НЕМЕДЛЕННЫЙ ЗАПУСК ПАРСИНГА ===')
        
        # Определяем параметры в зависимости от пресета
        if category:
            params = self._get_category_params(category)
            task_func = parse_vacancies_by_category
        else:
            params = self._get_preset_params(preset)
            task_func = parse_vacancies_by_technologies
        
        # Вывод информации
        self.stdout.write(f'Режим: {preset.upper() if not category else f"CATEGORY: {category}"}')
        self.stdout.write('Параметры:')
        for key, value in params.items():
            self.stdout.write(f'   - {key}: {value}')

        self.stdout.write(f'Режим выполнения: {"Асинхронный (фон)" if is_async else "Синхронный (с ожиданием)"}')
        self.stdout.write()
        
        # Запуск
        try:
            if is_async:
                # Асинхронный запуск
                task = task_func.delay(**params)
                self.stdout.write('Задача запущена в фоне!')
                self.stdout.write(f'Task ID: {task.id}')
                self.stdout.write('Проверьте статус через логи или Django shell')
            else:
                # Синхронный запуск
                self.stdout.write('Запуск парсинга (ожидайте)...')
                result = task_func(**params)

                self.stdout.write('\n=== ПАРСИНГ ЗАВЕРШЕН! ===')

                if result.get('error'):
                    self.stdout.write(f'Ошибка: {result["error"]}')
                else:
                    self._print_results(result)
                
        except Exception as e:
            self.stdout.write(f'Ошибка при запуске: {e}')
            logger.exception('Ошибка при немедленном запуске парсинга')
    
    def _get_preset_params(self, preset):
        """Получение параметров для пресета."""
        presets = {
            'test': {
                'categories': None,
                'top_n': 5,
                'use_aliases': False,
                'area': 113,
                'pages': 1,
                'delay': 1.0,
                'get_details': False,
                'max_queries': 5
            },
            'quick': {
                'categories': None,
                'top_n': 10,
                'use_aliases': False,
                'area': 113,
                'pages': 1,
                'delay': 1.0,
                'get_details': False,
                'max_queries': 10
            },
            'normal': {
                'categories': ['LANG', 'FRAMEWORK'],
                'top_n': 20,
                'use_aliases': False,
                'area': 113,
                'pages': 2,
                'delay': 1.5,
                'get_details': True,
                'max_queries': 25
            },
            'full': {
                'categories': ['LANG', 'FRAMEWORK', 'DB'],
                'top_n': 40,
                'use_aliases': True,
                'area': 113,
                'pages': 3,
                'delay': 2.0,
                'get_details': True,
                'max_queries': 50
            }
        }
        return presets.get(preset, presets['quick'])
    
    def _get_category_params(self, category):
        """Получение параметров для конкретной категории."""
        return {
            'category': category,
            'use_aliases': False,
            'area': 113,
            'pages': 2,
            'delay': 1.5,
            'get_details': True,
            'max_queries': 20
        }
    
    def _print_results(self, result):
        """Вывод результатов парсинга."""
        mode = result.get('mode', 'unknown')

        if mode == 'by_technologies':
            self.stdout.write(f"Технологий использовано: {result.get('technologies_count', 0)}")
            self.stdout.write(f"Поисковых запросов: {result.get('search_queries_count', 0)}")
        elif mode == 'by_category':
            self.stdout.write(f"Категория: {result.get('category', 'N/A')}")
            self.stdout.write(f"Поисковых запросов: {result.get('search_queries_count', 0)}")

        self.stdout.write('')
        self.stdout.write(f"Всего обработано: {result.get('total_vacancies', 0)}")
        self.stdout.write(f"Новых вакансий: {result.get('new_vacancies', 0)}")
        self.stdout.write(f"Обновлено: {result.get('updated_vacancies', 0)}")
        self.stdout.write(f"Всего в базе: {result.get('total_in_db', 0)}")



