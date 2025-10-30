"""
Команда для просмотра статуса фонового парсинга HeadHunter.

Показывает информацию о настроенных периодических задачах
и статусе Celery Beat планировщика.
"""

import json
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.vacancies_parser.api.headhunter.celery_beat_config import HeadhunterCeleryBeatConfig


class Command(BaseCommand):
    help = 'Просмотр статуса фонового парсинга HeadHunter'

    def add_arguments(self, parser):
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Показать детальную информацию о каждой задаче'
        )
        parser.add_argument(
            '--config',
            action='store_true',
            help='Показать конфигурацию из JSON файла'
        )

    def handle(self, *args, **options):
        self.stdout.write('=== СТАТУС ФОНОВОГО ПАРСИНГА HEADHUNTER ===')

        # Получаем конфигурацию
        beat_config = HeadhunterCeleryBeatConfig('headhunter')
        schedule = beat_config.get_beat_schedule()

        # Общая информация
        self.stdout.write(f'\nВсего настроено задач: {len(schedule)}')
        self.stdout.write(f'Текущее время: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}')
        
        # Показываем конфигурацию из JSON если запрошено
        if options.get('config'):
            self._show_json_config()
        
        # Список задач
        self.stdout.write('\n--- ПЕРИОДИЧЕСКИЕ ЗАДАЧИ ---')
        
        for task_name, task_config in schedule.items():
            self._print_task_info(task_name, task_config, options.get('detailed'))
        
        # Дополнительные настройки
        additional_config = beat_config.get_additional_beat_config()
        if additional_config:
            self.stdout.write('\n--- ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ ---')
            for key, value in additional_config.items():
                self.stdout.write(f'  {key}: {value}')
        
        # Инструкции
        self.stdout.write('\n=== ПОЛЕЗНЫЕ КОМАНДЫ ===')
        self.stdout.write('Для запуска Celery Beat:')
        self.stdout.write('   api start_celery_beat')
        self.stdout.write('\nДля ручного запуска парсинга:')
        self.stdout.write('   python src/manage.py parse_hh_by_technologies --category LANG --wait')
        self.stdout.write('\nДля просмотра логов Beat:')
        self.stdout.write('   Get-Content logs/celery_beat.log -Tail 50')
        self.stdout.write()
    
    def _print_task_info(self, task_name, task_config, detailed=False):
        """Вывод информации о задаче."""
        # Заголовок задачи
        self.stdout.write(f'- {task_name}')

        # Основная информация
        schedule = task_config.get('schedule')
        task = task_config.get('task', 'N/A')

        # Преобразование расписания в читаемый формат
        schedule_str = self._format_schedule(schedule)

        self.stdout.write(f'  Расписание: {schedule_str}')

        if detailed:
            self.stdout.write(f'  Задача: {task}')

            # Параметры задачи
            kwargs = task_config.get('kwargs', {})
            if kwargs:
                self.stdout.write('  Параметры:')
                for key, value in kwargs.items():
                    self.stdout.write(f'     - {key}: {value}')

            # Опции
            options = task_config.get('options', {})
            if options:
                self.stdout.write('  Опции:')
                for key, value in options.items():
                    self.stdout.write(f'     - {key}: {value}')
        else:
            # Краткая информация о параметрах
            kwargs = task_config.get('kwargs', {})
            if 'category' in kwargs:
                self.stdout.write(f'  Категория: {kwargs["category"]}')
            if 'top_n' in kwargs:
                self.stdout.write(f'  Топ технологий: {kwargs["top_n"]}')
            if 'pages' in kwargs:
                self.stdout.write(f'  Страниц: {kwargs["pages"]}')
        
        self.stdout.write('')  # Пустая строка
    
    def _format_schedule(self, schedule):
        """Форматирование расписания в читаемый формат."""
        if hasattr(schedule, 'run_every'):
            return f'Каждые {schedule.run_every}'
        
        # Обработка crontab
        if hasattr(schedule, 'hour') and hasattr(schedule, 'minute'):
            hour = schedule.hour
            minute = schedule.minute
            day_of_week = getattr(schedule, 'day_of_week', '*')
            
            # Форматирование времени
            if isinstance(hour, set):
                hour_str = ','.join(map(str, sorted(hour)))
            elif hour == '*':
                hour_str = 'каждый час'
            elif isinstance(hour, str) and '/' in hour:
                hour_str = f'каждые {hour.split("/")[1]} ч'
            else:
                hour_str = f'{hour:02d}' if isinstance(hour, int) else str(hour)
            
            if isinstance(minute, set):
                minute_str = ','.join(map(str, sorted(minute)))
            elif minute == '*':
                minute_str = 'каждую минуту'
            else:
                minute_str = f'{minute:02d}' if isinstance(minute, int) else str(minute)
            
            # Обработка дня недели
            if day_of_week and day_of_week != '*' and not isinstance(day_of_week, set):
                day_name = self._get_day_name(day_of_week)
                return f'{day_name} в {hour_str}:{minute_str}'
            elif isinstance(day_of_week, set):
                days = ', '.join([self._get_day_name(d) for d in sorted(day_of_week)])
                return f'{days} в {hour_str}:{minute_str}'
            else:
                if '/' in str(hour):
                    return f'{hour_str}'
                return f'Каждый день в {hour_str}:{minute_str}'
        
        return str(schedule)
    
    def _get_day_name(self, day):
        """Получение названия дня недели."""
        days = {
            0: 'Пн', 1: 'Вт', 2: 'Ср', 3: 'Чт', 4: 'Пт', 5: 'Сб', 6: 'Вс',
            'monday': 'Понедельник', 'tuesday': 'Вторник',
            'wednesday': 'Среда', 'thursday': 'Четверг',
            'friday': 'Пятница', 'saturday': 'Суббота',
            'sunday': 'Воскресенье',
        }
        return days.get(day, str(day))
    
    def _show_json_config(self):
        """Показать конфигурацию из JSON файла."""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'config',
            'background_parsing.json'
        )
        
        if not os.path.exists(config_path):
            self.stdout.write('\nФайл конфигурации не найден')
            return

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            self.stdout.write('\n--- КОНФИГУРАЦИЯ ИЗ ФАЙЛА ---')
            self.stdout.write(f'Описание: {config.get("description", "N/A")}')
            self.stdout.write(f'Включено: {"Да" if config.get("enabled") else "Нет"}')

            if 'common_settings' in config:
                self.stdout.write('\nОбщие настройки:')
                for key, value in config['common_settings'].items():
                    self.stdout.write(f'   - {key}: {value}')

        except Exception as e:
            self.stdout.write(f'Ошибка чтения конфигурации: {e}')

