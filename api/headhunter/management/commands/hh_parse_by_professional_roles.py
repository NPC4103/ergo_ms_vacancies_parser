"""
Команда для парсинга вакансий HeadHunter по профессиональным ролям IT.

Автоматически получает список IT ролей из категории 11 и парсит вакансии
по каждой роли с использованием параметра professional_role API HeadHunter.
"""

import json
import logging
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from django.core.management.base import BaseCommand

from ...tasks import parse_vacancies_by_professional_roles

logger = logging.getLogger('modules.vacancies_parser.headhunter')
CONFIG_PATH = Path(__file__).parent.parent.parent / 'config' / 'professional_roles_config.json'

# Профили быстрого выбора параметров
PROFILES: Dict[str, Dict[str, Any]] = {
    'safe': {
        'delay': 1.5,
        'parallel_workers': 1,
        'no_delays': False,
    },
    'full': {
        'delay': 0.8,             # минимально безопасная задержка для деталей
        'parallel_workers': 1,    # без параллельности, чтобы не ловить капчу на деталях
        'no_delays': False,
        'get_details': True,
        'pages': 200,
        'max_concurrent_roles': 3,
        'batch_size': 15,
    },
    'fast': {
        'delay': 0.5,
        'parallel_workers': 2,
        'no_delays': False,
    },
    'night': {
        'delay': 0.7,
        'parallel_workers': 3,
        'no_delays': False,
    },
    'test': {
        'delay': 0.5,
        'parallel_workers': 1,
        'no_delays': True,
        'pages': 1,
        'get_details': False,
        'max_concurrent_roles': 2,
        'batch_size': 5,
    },
}

TEXT: Dict[str, str] = {
    'line_sep': '-' * 64,
    'header': 'Парсинг вакансий по профессиональным ролям IT',
    'dry_run': 'Dry-run: задача не запускается.',
    'task_start': 'Запуск парсинга по профессиональным ролям IT',
    'task_sent': 'Задача Celery отправлена. Task ID: {task_id}',
    'parallel_note': 'Параллельные задачи отправлены в очередь.',
    'results_note': 'Результаты будут доступны после завершения всех подзадач.',
    'wait_not_supported': 'Примечание: --wait не поддерживается для параллельного режима.',
    'check_status': '   Используйте Flower или проверьте статус задач вручную.',
    'wait_start': 'Ожидание завершения задачи...',
    'wait_progress': 'Прогресс отображается в логах выше.',
    'wait_done': 'Задача завершена успешно.',
    'error_exec': 'Ошибка при выполнении: {error}',
}


@dataclass
class ParsingConfig:
    """Конфигурация параметров парсинга вакансий."""
    # Основные параметры
    area: int = 113
    pages: int = 20
    delay: float = 0.5
    get_details: bool = True
    max_concurrent_roles: int = 5
    batch_size: int = 25
    parallel_workers: int = 1
    sync: bool = False

    # Флаги поведения
    force_refresh_roles: bool = False
    incremental: bool = False
    skip_existing_roles: bool = False
    no_delays: bool = False
    wait: bool = False
    dry_run: bool = False
    profile: Optional[str] = None
    json_output: bool = False
    quiet: bool = False

    # Фильтры API HH
    experience: Optional[str] = None
    employment: Optional[str] = None
    schedule: Optional[str] = None
    only_with_salary: bool = False
    period: Optional[int] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    salary_from: Optional[int] = None
    salary_to: Optional[int] = None

    def to_task_params(self) -> Dict[str, Any]:
        """Преобразует конфигурацию в параметры для Celery задачи."""
        params = {
            'area': self.area,
            'pages': self.pages,
            'delay': 0.0 if self.no_delays else self.delay,
            'get_details': self.get_details,
            'max_concurrent_roles': self.max_concurrent_roles,
            'batch_size': self.batch_size,
            'force_refresh_roles': self.force_refresh_roles,
            'parallel_workers': self.parallel_workers,
            'incremental': self.incremental,
            'skip_existing_roles': self.skip_existing_roles,
            'only_with_salary': self.only_with_salary,
            'no_delays': self.no_delays
        }

        # Добавляем только не-None значения
        optional_params = {
            'experience': self.experience,
            'employment': self.employment,
            'schedule': self.schedule,
            'period': self.period,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'salary_from': self.salary_from,
            'salary_to': self.salary_to
        }

        for key, value in optional_params.items():
            if value is not None:
                params[key] = value

        return params


class Command(BaseCommand):
    """Команда для парсинга вакансий HeadHunter по профессиональным ролям IT."""

    help = 'Парсинг вакансий HeadHunter по профессиональным ролям IT'

    def add_arguments(self, parser):
        """Добавляет аргументы командной строки."""
        # Основные параметры парсинга
        parser.add_argument(
            '--area',
            type=int,
            default=None,
            help='ID региона для поиска (по умолчанию: из config или 113 - Россия)'
        )

        parser.add_argument(
            '--pages',
            type=int,
            default=None,
            help='Количество страниц для каждой роли (по умолчанию: 20, по 10 вакансий на страницу, максимум 200)'
        )

        parser.add_argument(
            '--delay',
            type=float,
            default=None,
            help='Задержка между запросами в секундах (по умолчанию: из config или 0.5)'
        )

        parser.add_argument(
            '--no-details',
            action='store_true',
            help='Не получать детальную информацию о вакансиях (только базовую)'
        )

        parser.add_argument(
            '--max-concurrent-roles',
            type=int,
            default=None,
            help='Максимум параллельных ролей для обработки (по умолчанию: из config или 5)'
        )

        parser.add_argument(
            '--batch-size',
            type=int,
            default=None,
            help='Размер батча ролей для обработки (по умолчанию: из config или 25, 0 = все роли сразу для макс. скорости)'
        )

        # Режимы работы
        parser.add_argument(
            '--force-refresh-roles',
            action='store_true',
            help='Принудительно обновить список ролей из API'
        )

        parser.add_argument(
            '--no-delays',
            action='store_true',
            help='Отключить основные задержки для максимальной скорости (риск блокировки, авто-задержки сохраняются)'
        )

        parser.add_argument(
            '--wait',
            action='store_true',
            help='Дождаться завершения задачи Celery и вывести результат'
        )

        parser.add_argument(
            '--parallel-workers',
            type=int,
            default=None,
            help='Количество параллельных Celery задач (по умолчанию: 1, макс: 10, рекомендуется: 1-2). При 403 ошибках автоматически уменьшается'
        )

        parser.add_argument(
            '--incremental',
            action='store_true',
            help='Инкрементальный парсинг - парсить только вакансии новее последней в БД'
        )

        parser.add_argument(
            '--skip-existing-roles',
            action='store_true',
            help='Пропускать роли, которые уже парсились сегодня'
        )

        parser.add_argument(
            '--profile',
            choices=list(PROFILES.keys()),
            help='Профиль настроек (safe, fast, night) для быстрого выбора параметров'
        )

        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать конфигурацию и не запускать задачу'
        )
        parser.add_argument(
            '--sync',
            action='store_true',
            help='Синхронный запуск без Celery (apply)'
        )

        # Дополнительные параметры фильтрации из API HH
        parser.add_argument(
            '--experience',
            type=str,
            help='Опыт работы (noExperience, between1And3, between3And6, moreThan6)'
        )

        parser.add_argument(
            '--employment',
            type=str,
            help='Тип занятости (full, part, project, volunteer, probation)'
        )

        parser.add_argument(
            '--schedule',
            type=str,
            help='График работы (fullDay, shift, flexible, remote, flyInFlyOut)'
        )

        parser.add_argument(
            '--only-with-salary',
            action='store_true',
            help='Показывать только вакансии с указанием зарплаты'
        )

        parser.add_argument(
            '--period',
            type=int,
            help='Количество дней для поиска (от настоящего момента назад)'
        )

        parser.add_argument(
            '--date-from',
            type=str,
            help='Дата начала поиска в формате YYYY-MM-DD'
        )

        parser.add_argument(
            '--date-to',
            type=str,
            help='Дата окончания поиска в формате YYYY-MM-DD'
        )

        parser.add_argument(
            '--salary-from',
            type=int,
            help='Минимальная зарплата (в рублях)'
        )

        parser.add_argument(
            '--salary-to',
            type=int,
            help='Максимальная зарплата (в рублях)'
        )

        parser.add_argument(
            '--json-output',
            action='store_true',
            help='Вывести результат в JSON (stdout)'
        )

        parser.add_argument(
            '--quiet',
            action='store_true',
            help='Минимальный вывод (только ключевые строки или JSON)'
        )

    def handle(self, *args, **options):
        """Основной обработчик команды."""
        self._print_header(bool(options.get('quiet')))

        try:
            # Парсим и валидируем параметры
            config = self._parse_arguments(options)
            self._validate_parameters(config)

            # Выводим конфигурацию и проверяем риски
            self._print_configuration(config)
            risk_level, risk_message = self._check_risk_level(config)
            self._print_risk_warning(risk_level, risk_message, config.quiet)

            if config.dry_run:
                if not config.quiet:
                    self.stdout.write(TEXT['dry_run'])
                return

            # Запускаем парсинг
            self._run_parsing_task(config)

        except KeyboardInterrupt:
            self.stdout.write('\nПарсинг прерван пользователем')
        except Exception as e:
            self.stdout.write(f'Ошибка: {e}')
            logger.exception('Ошибка при запуске парсинга по ролям')

    def _parse_arguments(self, options) -> ParsingConfig:
        """Парсит аргументы командной строки в конфигурацию."""
        defaults = self._load_defaults()
        profile_overrides = PROFILES.get(options.get('profile') or '', {})

        # Применяем приоритет: CLI > profile > defaults > hardcoded
        def pick(name, hardcoded):
            cli_val = options.get(name)
            if cli_val is not None:
                return cli_val
            if name in profile_overrides:
                return profile_overrides[name]
            return defaults.get(name, hardcoded)

        ctx_profile = options.get('profile') or ''
        min_pages = 1 if ctx_profile == 'test' else 20
        pages_value = max(pick('pages', 20), min_pages)

        if options.get('no_details') is not None:
            get_details_val = not options['no_details']
        elif 'get_details' in profile_overrides:
            get_details_val = profile_overrides['get_details']
        else:
            get_details_val = defaults.get('get_details', True)

        return ParsingConfig(
            # Основные параметры
            area=pick('area', 113),
            pages=pages_value,
            delay=pick('delay', 0.5),
            get_details=get_details_val,
            max_concurrent_roles=pick('max_concurrent_roles', 5),
            batch_size=pick('batch_size', 25),
            parallel_workers=min(pick('parallel_workers', 1), 10),  # Макс 10 параллельных задач

            # Флаги поведения
            force_refresh_roles=options['force_refresh_roles'],
            incremental=options['incremental'],
            skip_existing_roles=options['skip_existing_roles'],
            no_delays=pick('no_delays', False),
            wait=options['wait'],
            dry_run=options['dry_run'],
            sync=options['sync'],
            profile=options.get('profile'),
            json_output=options['json_output'],
            quiet=options['quiet'],

            # Фильтры API HH
            experience=options.get('experience'),
            employment=options.get('employment'),
            schedule=options.get('schedule'),
            only_with_salary=options['only_with_salary'],
            period=options.get('period'),
            date_from=options.get('date_from'),
            date_to=options.get('date_to'),
            salary_from=options.get('salary_from'),
            salary_to=options.get('salary_to')
        )

    def _load_defaults(self) -> Dict[str, Any]:
        """Загружает дефолтные значения из config файла модуля."""
        if not CONFIG_PATH.exists():
            return {}

        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)

            parsing_settings = data.get('parsing_settings', {})

            return {
                'area': parsing_settings.get('area'),
                'pages': parsing_settings.get('pages'),
                'delay': parsing_settings.get('delay'),
                'get_details': parsing_settings.get('get_details'),
                'max_concurrent_roles': parsing_settings.get('max_concurrent_roles'),
                'batch_size': parsing_settings.get('batch_size'),
            }
        except Exception as exc:
            logger.warning('Не удалось загрузить professional_roles_config.json: %s', exc)
            return {}

    def _validate_parameters(self, config: ParsingConfig):
        """Валидирует параметры конфигурации."""
        if config.pages < 1:
            raise ValueError('Количество страниц должно быть больше 0')
        if config.delay < 0:
            raise ValueError('Задержка не может быть отрицательной')
        if config.max_concurrent_roles < 1:
            raise ValueError('Количество одновременных ролей должно быть больше 0')
        if config.batch_size < 0:
            raise ValueError('Размер батча не может быть отрицательным')
        if config.parallel_workers < 1:
            raise ValueError('Количество воркеров должно быть больше 0')

    def _print_configuration(self, config: ParsingConfig):
        """Выводит текущую конфигурацию парсинга."""
        if config.quiet:
            return
        self.stdout.write('Параметры парсинга:')
        self.stdout.write(f'   Регион: {config.area}')
        self.stdout.write(f'   Страниц на роль: {config.pages}')
        self.stdout.write(f'   Задержка: {config.delay} сек')
        self.stdout.write(f'   Детальная информация: {"Да" if config.get_details else "Нет"}')
        self.stdout.write(f'   Размер батча: {config.batch_size}')
        self.stdout.write(f'   Макс. одновременных ролей: {config.max_concurrent_roles}')
        self.stdout.write(f'   Параллельных задач: {config.parallel_workers}')

        # Выводим дополнительные параметры
        self._print_optional_params(config)
        self.stdout.write('\n' + '=' * 70 + '\n')

    def _print_optional_params(self, config: ParsingConfig):
        """Выводит опциональные параметры."""
        if config.quiet:
            return
        self.stdout.write(f'   Инкрементальный режим: {"Да" if config.incremental else "Нет"}')
        self.stdout.write(f'   Пропускать существующие роли: {"Да" if config.skip_existing_roles else "Нет"}')
        self.stdout.write(f'   Без задержек: {"Да" if config.no_delays else "Нет"}')

        if config.experience:
            self.stdout.write(f'   Опыт работы: {config.experience}')
        if config.employment:
            self.stdout.write(f'   Тип занятости: {config.employment}')
        if config.schedule:
            self.stdout.write(f'   График работы: {config.schedule}')
        if config.only_with_salary:
            self.stdout.write('   Только с зарплатой: Да')
        if config.period:
            self.stdout.write(f'   Период (дни): {config.period}')
        if config.date_from or config.date_to:
            self.stdout.write(f'   Диапазон дат: {config.date_from or "N/A"} - {config.date_to or "N/A"}')
        if config.salary_from or config.salary_to:
            self.stdout.write(f'   Диапазон зарплат: {config.salary_from or "N/A"} - {config.salary_to or "N/A"} руб.')

    def _check_risk_level(self, config: ParsingConfig) -> tuple[str, str]:
        """Проверяет уровень риска блокировки и возвращает рекомендации."""
        if config.no_delays:
            if config.parallel_workers > 1:
                return "high", "ВЫСОКИЙ РИСК: --no-delays + параллельность = гарантированная блокировка!"
            else:
                return "medium", "СРЕДНИЙ РИСК: --no-delays может привести к блокировке"
        elif config.parallel_workers > 2:
            return "medium", "РИСК: >2 параллельных воркеров может вызвать блокировку даже с задержками"
        elif config.parallel_workers > 1 and config.delay < 1.0:
            return "low", "СОВЕТ: Для 2 воркеров рекомендуется delay >= 1.0 сек"

        return "low", ""

    def _print_risk_warning(self, risk_level: str, risk_message: str, quiet: bool):
        """Выводит предупреждение о рисках."""
        if quiet:
            return
        if risk_message:
            self.stdout.write(f'   [WARNING] {risk_message}')

            if risk_level == "high":
                self.stdout.write('   [RECOMMEND] --parallel-workers 1 --delay 1.5 (максимальная безопасность)')
            elif risk_level == "medium":
                self.stdout.write('   [RECOMMEND] --parallel-workers 1 --delay 1.0 (высокая безопасность)')
            else:
                self.stdout.write('   [RECOMMEND] --parallel-workers 1-2 --delay 1.0+ (оптимальная безопасность)')

    def _run_parsing_task(self, config: ParsingConfig):
        """Запускает задачу парсинга."""
        if not config.quiet:
            self.stdout.write(TEXT['task_start'])

        # Получаем параметры для задачи
        task_params = config.to_task_params()

        if config.sync:
            # В синхронном режиме отключаем распараллеливание (chord не работает с apply)
            if task_params.get('parallel_workers', 1) > 1:
                task_params['parallel_workers'] = 1
                if not config.quiet:
                    self.stdout.write('Синхронный режим: parallel_workers принудительно установлен в 1')

            # Синхронный запуск без Celery worker
            if not config.quiet:
                self.stdout.write('Синхронный запуск (без Celery worker)...')
            task = parse_vacancies_by_professional_roles.apply(kwargs=task_params)  # type: ignore[call-arg]
            if task.successful():
                result = task.get()
                self._print_result(result, config)
            else:
                if config.json_output:
                    self.stdout.write(json.dumps({'status': 'error', 'error': str(task.result)}, ensure_ascii=False))
                else:
                    self.stdout.write(TEXT['error_exec'].format(error=task.result))
            return

        task = parse_vacancies_by_professional_roles.delay(**task_params)  # type: ignore[call-arg]

        if config.json_output and not config.wait:
            self.stdout.write(json.dumps({'task_id': str(task.id), 'status': 'queued'}, ensure_ascii=False))
        elif config.quiet:
            self.stdout.write(f'Task ID: {task.id}')
        else:
            self.stdout.write(TEXT['task_sent'].format(task_id=task.id))

        if config.parallel_workers > 1:
            self._handle_parallel_mode(task, config)
        else:
            self._handle_single_worker_mode(task, config)

    def _handle_parallel_mode(self, task, config: ParsingConfig):
        """Обрабатывает параллельный режим выполнения."""
        if config.json_output:
            self.stdout.write(json.dumps({'task_id': str(task.id), 'status': 'queued_parallel'}, ensure_ascii=False))
            return

        if config.quiet:
            self.stdout.write(f'Task ID: {task.id}')
            return

        self.stdout.write(TEXT['parallel_note'])
        self.stdout.write(TEXT['results_note'])
        self.stdout.write(f'Main Task ID: {task.id}')
        self.stdout.write('')
        self.stdout.write(TEXT['monitor_flower'])

        if config.wait:
            self.stdout.write('')
            self.stdout.write(TEXT['wait_not_supported'])
            self.stdout.write(TEXT['check_status'])

    def _handle_single_worker_mode(self, task, config: ParsingConfig):
        """Обрабатывает режим с одним воркером."""
        if config.wait:
            self._handle_wait_mode(task, config)
        else:
            if config.json_output:
                self.stdout.write(json.dumps({'task_id': str(task.id), 'status': 'queued'}, ensure_ascii=False))
            elif config.quiet:
                self.stdout.write(f'Task ID: {task.id}')
            else:
                self.stdout.write('Задача отправлена в очередь.')
                self.stdout.write('Прогресс отображается в логах выше.')
                self.stdout.write(f'Task ID: {task.id}')

    def _handle_wait_mode(self, task, config: ParsingConfig):
        """Обрабатывает режим ожидания завершения задачи."""
        if not config.quiet:
            self.stdout.write(TEXT['wait_start'])
            self.stdout.write(TEXT['wait_progress'])
            self.stdout.write(TEXT['wait_monitor'])
            self.stdout.write('')

        spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        i = 0
        start_time = time.time()

        while not task.ready():
            if config.quiet or config.json_output:
                time.sleep(1)
                continue

            elapsed = time.time() - start_time
            elapsed_str = f'{int(elapsed // 60):02d}:{int(elapsed % 60):02d}'

            sys.stdout.write(f'\r{spinner[i % 10]} Выполняется... {elapsed_str} прошло')
            sys.stdout.flush()
            time.sleep(1)
            i += 1

        # Очистка строки
        if not config.quiet and not config.json_output:
            sys.stdout.write('\r' + ' ' * 50 + '\r')
            sys.stdout.flush()

        if task.successful():
            result = task.get()
            if config.json_output:
                self._print_result(result, config)
            else:
                self.stdout.write(TEXT['wait_done'])
                self._print_result(result, config)
        else:
            if config.json_output:
                self.stdout.write(json.dumps({'task_id': str(task.id), 'status': 'error', 'error': str(task.result)}, ensure_ascii=False))
            else:
                self.stdout.write(TEXT['error_exec'].format(error=task.result))

    def _print_header(self, quiet: bool):
        """Выводит заголовок команды."""
        if quiet:
            return
        self.stdout.write(TEXT['line_sep'])
        self.stdout.write(TEXT['header'])
        self.stdout.write(TEXT['line_sep'])

    def _print_result(self, result, config: ParsingConfig):
        """Вывод результатов парсинга."""
        if config.json_output:
            self.stdout.write(json.dumps(result, ensure_ascii=False, indent=None if config.quiet else 2))
            return

        if config.quiet:
            if result.get('error'):
                self.stdout.write(result.get('error', 'error'))
            else:
                self.stdout.write(f"status={result.get('status', 'completed')}, total_vacancies={result.get('total_vacancies', 0)}")
            return

        if result.get('error'):
            self.stdout.write(f'Ошибка: {result["error"]}')
            return

        self.stdout.write('\n=== РЕЗУЛЬТАТЫ ПАРСИНГА ===')

        mode = result.get('mode', 'unknown')

        if mode in ['by_professional_roles', 'by_professional_roles_parallel']:
            if mode == 'by_professional_roles_parallel':
                status = result.get('status', 'unknown')
                if status == 'parallel_tasks_dispatched':
                    self.stdout.write('Параллельные задачи запущены!')
                    self.stdout.write(f"Всего ролей для обработки: {result.get('total_roles', 0)}")
                    self.stdout.write(f"Количество воркеров: {result.get('parallel_workers', 0)}")
                    self.stdout.write(f"ID группы задач: {result.get('group_task_id', 'N/A')}")
                    self.stdout.write('')
                    self.stdout.write('Для получения результатов проверьте статус задач через Flower')
                    self.stdout.write('или дождитесь завершения всех подзадач.')
                    return
                else:
                    self.stdout.write(f"Всего IT ролей: {result.get('total_roles', 0)}")
            else:
                self.stdout.write(f"Всего IT ролей: {result.get('total_roles', 0)}")
                self.stdout.write(f"Обработано ролей: {result.get('parsed_roles', 0)}")

        self.stdout.write('')
        self.stdout.write(f"Всего обработано вакансий: {result.get('total_vacancies', 0)}")
        self.stdout.write(f"Новых вакансий: {result.get('new_vacancies', 0)}")
        self.stdout.write(f"Обновлено вакансий: {result.get('updated_vacancies', 0)}")
        self.stdout.write(f"Всего в базе данных: {result.get('total_in_db', 0)}")

        if result.get('metrics'):
            metrics = result['metrics']
            self.stdout.write('')
            self.stdout.write('Метрики выполнения:')
            self.stdout.write(f"  Запросов: {metrics.get('requests_total', 0)}")
            self.stdout.write(f"  Успешных: {metrics.get('requests_success', 0)}")
            self.stdout.write(f"  Ошибок: {metrics.get('requests_error', 0)}")
            self.stdout.write(f"  Rate limit: {metrics.get('rate_limits', 0)}")
