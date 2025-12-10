"""
Команда для парсинга вакансий HeadHunter по профессиональным ролям IT.

Автоматически получает список IT ролей из категории 11 и парсит вакансии
по каждой роли с использованием параметра professional_role API HeadHunter.
"""

import logging
import time
import sys
from django.core.management.base import BaseCommand

from ...tasks import parse_vacancies_by_professional_roles

logger = logging.getLogger('modules.vacancies_parser.headhunter')


class Command(BaseCommand):
    help = 'Парсинг вакансий HeadHunter по профессиональным ролям IT'

    def add_arguments(self, parser):
        """
        Добавляет аргументы командной строки.

        Args:
            parser: Парсер аргументов командной строки
        """
        parser.add_argument(
            '--area',
            type=int,
            default=113,
            help='ID региона для поиска (по умолчанию: 113 - Россия)'
        )

        parser.add_argument(
            '--pages',
            type=int,
            default=20,
            help='Количество страниц для каждой роли (по умолчанию: 20, максимум для полного покрытия)'
        )

        parser.add_argument(
            '--delay',
            type=float,
            default=0.5,
            help='Задержка между запросами в секундах (по умолчанию: 0.5)'
        )

        parser.add_argument(
            '--no-details',
            action='store_true',
            help='Не получать детальную информацию о вакансиях (только базовую)'
        )

        parser.add_argument(
            '--max-concurrent-roles',
            type=int,
            default=5,
            help='Максимум параллельных ролей для обработки (по умолчанию: 5)'
        )

        parser.add_argument(
            '--batch-size',
            type=int,
            default=25,
            help='Размер батча ролей для обработки (по умолчанию: 25, 0 = все роли сразу для макс. скорости)'
        )

        parser.add_argument(
            '--force-refresh-roles',
            action='store_true',
            help='Принудительно обновить список ролей из API'
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
            default=1,
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

    def handle(self, *args, **options):
        self.stdout.write('=' * 70)
        self.stdout.write('=== Парсинг вакансий по профессиональным ролям IT ===')
        self.stdout.write('=' * 70)

        # Извлекаем параметры
        area = options['area']
        pages = options['pages']
        delay = 0.0 if options['no_delays'] else options['delay']
        get_details = not options['no_details']
        max_concurrent_roles = options['max_concurrent_roles']
        batch_size = options['batch_size']
        force_refresh_roles = options['force_refresh_roles']
        wait = options['wait']
        parallel_workers = min(options['parallel_workers'], 10)  # Макс 10 параллельных задач

        # Дополнительные параметры фильтрации
        experience = options.get('experience')
        employment = options.get('employment')
        schedule = options.get('schedule')
        only_with_salary = options['only_with_salary']
        period = options.get('period')
        date_from = options.get('date_from')
        date_to = options.get('date_to')
        salary_from = options.get('salary_from')
        salary_to = options.get('salary_to')
        no_delays = options['no_delays']

        # Вывод параметров
        self.stdout.write('Параметры парсинга:')
        self.stdout.write(f'   Регион: {area}')
        self.stdout.write(f'   Страниц на роль: {pages}')
        self.stdout.write(f'   Задержка: {delay} сек')
        self.stdout.write(f'   Детальная информация: {"Да" if get_details else "Нет"}')
        self.stdout.write(f'   Размер батча: {batch_size}')
        self.stdout.write(f'   Макс. одновременных ролей: {max_concurrent_roles}')
        self.stdout.write(f'   Параллельных задач: {parallel_workers}')

        # Проверяем риски блокировки IP с учетом delay и новых задержек старта
        risk_level = "low"
        risk_message = ""

        if no_delays:
            if parallel_workers > 1:
                risk_level = "high"
                risk_message = "ВЫСОКИЙ РИСК: --no-delays + параллельность = гарантированная блокировка!"
            else:
                risk_level = "medium"
                risk_message = "СРЕДНИЙ РИСК: --no-delays может привести к блокировке"
        elif parallel_workers > 2:
            risk_level = "medium"
            risk_message = "РИСК: >2 параллельных воркеров может вызвать блокировку даже с задержками"
        elif parallel_workers > 1 and delay < 1.0:
            risk_level = "low"
            risk_message = "СОВЕТ: Для 2 воркеров рекомендуется delay >= 1.0 сек"

        if risk_message:
            self.stdout.write(f'   [WARNING] {risk_message}')

            if risk_level == "high":
                self.stdout.write('   [RECOMMEND] --parallel-workers 1 --delay 1.5 (максимальная безопасность)')
            elif risk_level == "medium":
                self.stdout.write('   [RECOMMEND] --parallel-workers 1 --delay 1.0 (высокая безопасность)')
            else:
                self.stdout.write('   [RECOMMEND] --parallel-workers 1-2 --delay 1.0+ (оптимальная безопасность)')
        self.stdout.write(f'   Инкрементальный режим: {"Да" if options["incremental"] else "Нет"}')
        self.stdout.write(f'   Пропускать существующие роли: {"Да" if options["skip_existing_roles"] else "Нет"}')
        self.stdout.write(f'   Без задержек: {"Да" if no_delays else "Нет"}')

        if experience:
            self.stdout.write(f'   Опыт работы: {experience}')
        if employment:
            self.stdout.write(f'   Тип занятости: {employment}')
        if schedule:
            self.stdout.write(f'   График работы: {schedule}')
        if only_with_salary:
            self.stdout.write('   Только с зарплатой: Да')
        if period:
            self.stdout.write(f'   Период (дни): {period}')
        if date_from or date_to:
            self.stdout.write(f'   Диапазон дат: {date_from or "N/A"} - {date_to or "N/A"}')
        if salary_from or salary_to:
            self.stdout.write(f'   Диапазон зарплат: {salary_from or "N/A"} - {salary_to or "N/A"} руб.')

        self.stdout.write('\n' + '=' * 70 + '\n')

        try:
            # Параметры для задачи (фильтруем None значения)
            task_params = {
                'area': area,
                'pages': pages,
                'delay': delay,
                'get_details': get_details,
                'max_concurrent_roles': max_concurrent_roles,
                'batch_size': batch_size,
                'force_refresh_roles': force_refresh_roles,
                'parallel_workers': parallel_workers,
                'incremental': options['incremental'],
                'skip_existing_roles': options['skip_existing_roles'],
                'only_with_salary': only_with_salary,
                'no_delays': no_delays
            }

            # Добавляем только не-None значения
            if experience is not None:
                task_params['experience'] = experience
            if employment is not None:
                task_params['employment'] = employment
            if schedule is not None:
                task_params['schedule'] = schedule
            if period is not None:
                task_params['period'] = period
            if date_from is not None:
                task_params['date_from'] = date_from
            if date_to is not None:
                task_params['date_to'] = date_to
            if salary_from is not None:
                task_params['salary_from'] = salary_from
            if salary_to is not None:
                task_params['salary_to'] = salary_to

            # Запуск задачи
            self.stdout.write('Запуск парсинга по профессиональным ролям IT')
            task = parse_vacancies_by_professional_roles.delay(**task_params)

            self.stdout.write(f'Задача Celery отправлена! Task ID: {task.id}')

            if parallel_workers > 1:
                # Для параллельного режима всегда асинхронный запуск
                self.stdout.write('Параллельные задачи отправлены в очередь.')
                self.stdout.write('Результаты будут доступны после завершения всех подзадач.')
                self.stdout.write(f'Main Task ID: {task.id}')
                self.stdout.write('')
                self.stdout.write('Для мониторинга используйте Celery Flower: http://localhost:5555')
                if wait:
                    self.stdout.write('')
                    self.stdout.write('⚠️  ПРИМЕЧАНИЕ: --wait не поддерживается для параллельного режима.')
                    self.stdout.write('   Используйте Flower или проверьте статус задач вручную.')
            else:
                # Для последовательного режима можно использовать --wait
                if wait:
                    self.stdout.write('Ожидание завершения задачи...')
                    self.stdout.write('Прогресс будет отображаться в логах выше.')
                    self.stdout.write('Для детального мониторинга используйте Celery Flower: http://localhost:5555')
                    self.stdout.write('')

                    spinner = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
                    i = 0
                    start_time = time.time()

                    while not task.ready():
                        elapsed = time.time() - start_time
                        elapsed_str = f'{int(elapsed // 60):02d}:{int(elapsed % 60):02d}'

                        sys.stdout.write(f'\r{spinner[i % 10]} Выполняется... {elapsed_str} прошло')
                        sys.stdout.flush()
                        time.sleep(1)
                        i += 1

                    # Очистка строки
                    sys.stdout.write('\r' + ' ' * 50 + '\r')
                    sys.stdout.flush()

                    if task.successful():
                        result = task.get()
                        self.stdout.write('Задача завершена успешно!')
                        self._print_result(result)
                    else:
                        self.stdout.write(f'Ошибка при выполнении: {task.result}')
                else:
                    self.stdout.write('Задача отправлена в очередь.')
                    self.stdout.write('Прогресс отображается в логах выше.')
                    self.stdout.write(f'Task ID: {task.id}')

        except KeyboardInterrupt:
            self.stdout.write('\nПарсинг прерван пользователем')

        except Exception as e:
            self.stdout.write(f'Ошибка: {e}')
            logger.exception('Ошибка при запуске парсинга по ролям')

    def _print_result(self, result):
        """Вывод результатов парсинга."""
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
