"""
Django команда для миграции вакансий из старых таблиц в NormalizedVacancy.

Мигрирует данные из:
- vacancies_parser_headhunter_vacancy
- vacancies_parser_habr_career_vacancy  
- vacancies_parser_superjob_superjobvacancy

В унифицированную таблицу:
- vacancies_parser_normalizedvacancy
"""

import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from src.modules.vacancies_parser.api.core.normalized_models import NormalizedVacancy
from src.modules.vacancies_parser.api.headhunter.models import Vacancy as HHVacancy
from src.modules.vacancies_parser.api.habr_career.models import Vacancy as HabrVacancy
from src.modules.vacancies_parser.api.superjob.models import SuperJobVacancy

logger = logging.getLogger('celery.module.vacancies_parser')


class Command(BaseCommand):
    help = 'Мигрирует вакансии из старых таблиц в NormalizedVacancy'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            choices=['headhunter', 'habr_career', 'superjob', 'all'],
            default='all',
            help='Источник для миграции (по умолчанию: all)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Размер батча для миграции (по умолчанию: 1000)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Тестовый запуск без сохранения данных'
        )

    def handle(self, *args, **options):
        source = options['source']
        batch_size = options['batch_size']
        dry_run = options['dry_run']

        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 ТЕСТОВЫЙ РЕЖИМ - данные не будут сохранены'))

        if source in ['headhunter', 'all']:
            self.migrate_headhunter(batch_size, dry_run)

        if source in ['habr_career', 'all']:
            self.migrate_habr_career(batch_size, dry_run)

        if source in ['superjob', 'all']:
            self.migrate_superjob(batch_size, dry_run)

        self.stdout.write(self.style.SUCCESS('\n✅ Миграция завершена!'))

    def migrate_headhunter(self, batch_size, dry_run):
        """Мигрирует вакансии HeadHunter"""
        self.stdout.write(self.style.HTTP_INFO('\n📦 Миграция HeadHunter вакансий...'))

        total = HHVacancy.objects.count()
        self.stdout.write(f'Всего вакансий в старой таблице: {total}')

        # Проверяем сколько уже мигрировано
        existing_ids = set(
            NormalizedVacancy.objects.filter(
                source='headhunter'
            ).values_list('external_id', flat=True)
        )
        self.stdout.write(f'Уже мигрировано: {len(existing_ids)}')

        migrated = 0
        skipped = 0
        errors = 0

        # Обрабатываем батчами
        for offset in range(0, total, batch_size):
            vacancies = HHVacancy.objects.all()[offset:offset + batch_size]

            batch_to_create = []

            for vacancy in vacancies:
                # Пропускаем уже мигрированные
                if vacancy.hh_id in existing_ids:
                    skipped += 1
                    continue

                try:
                    normalized = NormalizedVacancy(
                        # Основная информация
                        title=vacancy.title or '',
                        company_name=vacancy.company_name or '',
                        external_id=vacancy.hh_id,
                        external_url=vacancy.url or '',
                        
                        # Зарплата
                        salary_from=vacancy.salary_from,
                        salary_to=vacancy.salary_to,
                        salary_currency=vacancy.salary_currency or 'RUR',
                        salary_gross=vacancy.salary_gross or False,
                        
                        # Локация
                        area_name=vacancy.city or '',
                        address=vacancy.address or '',
                        
                        # Описание
                        description=vacancy.description or '',
                        requirements=vacancy.requirements or '',
                        responsibilities=vacancy.responsibilities or '',
                        
                        # Условия
                        employment_type=vacancy.employment_type or '',
                        experience_level=vacancy.experience_level or '',
                        
                        # Навыки
                        key_skills=vacancy.key_skills or [],
                        
                        # Метаданные
                        source='headhunter',
                        parsing_mode='api',  # Старые данные были через API
                        published_at=vacancy.published_at or timezone.now(),
                        archived=False,
                        is_active=True,
                    )

                    batch_to_create.append(normalized)
                    migrated += 1

                except Exception as e:
                    logger.error(f'Ошибка миграции HH вакансии {vacancy.id}: {e}')
                    errors += 1

            # Сохраняем батч
            if batch_to_create and not dry_run:
                try:
                    with transaction.atomic():
                        NormalizedVacancy.objects.bulk_create(batch_to_create, ignore_conflicts=True)
                except Exception as e:
                    logger.error(f'Ошибка сохранения батча: {e}')
                    errors += len(batch_to_create)

            # Прогресс
            progress = min(offset + batch_size, total)
            self.stdout.write(f'Обработано: {progress}/{total} ({progress*100//total}%)')

        self.stdout.write(self.style.SUCCESS(
            f'✅ HeadHunter: мигрировано {migrated}, пропущено {skipped}, ошибок {errors}'
        ))

    def migrate_habr_career(self, batch_size, dry_run):
        """Мигрирует вакансии Habr Career"""
        self.stdout.write(self.style.HTTP_INFO('\n📦 Миграция Habr Career вакансий...'))

        total = HabrVacancy.objects.count()
        if total == 0:
            self.stdout.write('Нет вакансий для миграции')
            return

        self.stdout.write(f'Всего вакансий в старой таблице: {total}')

        existing_ids = set(
            NormalizedVacancy.objects.filter(
                source='habr_career'
            ).values_list('external_id', flat=True)
        )
        self.stdout.write(f'Уже мигрировано: {len(existing_ids)}')

        migrated = 0
        skipped = 0
        errors = 0

        for offset in range(0, total, batch_size):
            vacancies = HabrVacancy.objects.all()[offset:offset + batch_size]
            batch_to_create = []

            for vacancy in vacancies:
                if vacancy.habr_id in existing_ids:
                    skipped += 1
                    continue

                try:
                    normalized = NormalizedVacancy(
                        title=vacancy.title or '',
                        company_name=vacancy.company_name or '',
                        external_id=vacancy.habr_id,
                        external_url=vacancy.url or '',
                        salary_from=vacancy.salary_from,
                        salary_to=vacancy.salary_to,
                        salary_currency=vacancy.salary_currency or 'RUR',
                        area_name=vacancy.location or '',
                        description=vacancy.description or '',
                        requirements=vacancy.skills_description or '',
                        employment_type=vacancy.employment_type or '',
                        experience_level=vacancy.experience_level or '',
                        key_skills=vacancy.skills or [],
                        source='habr_career',
                        parsing_mode='api',
                        published_at=vacancy.published_at or timezone.now(),
                        archived=False,
                        is_active=True,
                    )

                    batch_to_create.append(normalized)
                    migrated += 1

                except Exception as e:
                    logger.error(f'Ошибка миграции Habr вакансии {vacancy.id}: {e}')
                    errors += 1

            if batch_to_create and not dry_run:
                try:
                    with transaction.atomic():
                        NormalizedVacancy.objects.bulk_create(batch_to_create, ignore_conflicts=True)
                except Exception as e:
                    logger.error(f'Ошибка сохранения батча: {e}')
                    errors += len(batch_to_create)

            progress = min(offset + batch_size, total)
            self.stdout.write(f'Обработано: {progress}/{total} ({progress*100//total}%)')

        self.stdout.write(self.style.SUCCESS(
            f'✅ Habr Career: мигрировано {migrated}, пропущено {skipped}, ошибок {errors}'
        ))

    def migrate_superjob(self, batch_size, dry_run):
        """Мигрирует вакансии SuperJob"""
        self.stdout.write(self.style.HTTP_INFO('\n📦 Миграция SuperJob вакансий...'))

        total = SuperJobVacancy.objects.count()
        if total == 0:
            self.stdout.write('Нет вакансий для миграции')
            return

        self.stdout.write(f'Всего вакансий в старой таблице: {total}')

        existing_ids = set(
            NormalizedVacancy.objects.filter(
                source='superjob'
            ).values_list('external_id', flat=True)
        )
        self.stdout.write(f'Уже мигрировано: {len(existing_ids)}')

        migrated = 0
        skipped = 0
        errors = 0

        for offset in range(0, total, batch_size):
            vacancies = SuperJobVacancy.objects.all()[offset:offset + batch_size]
            batch_to_create = []

            for vacancy in vacancies:
                if str(vacancy.superjob_id) in existing_ids:
                    skipped += 1
                    continue

                try:
                    normalized = NormalizedVacancy(
                        title=vacancy.profession or '',
                        company_name=vacancy.firm_name or '',
                        external_id=str(vacancy.superjob_id),
                        external_url=vacancy.link or '',
                        salary_from=vacancy.payment_from,
                        salary_to=vacancy.payment_to,
                        salary_currency=vacancy.currency or 'rub',
                        area_name=vacancy.town_title or '',
                        address=vacancy.address or '',
                        description=vacancy.candidat or '',
                        employment_type=vacancy.type_of_work_title or '',
                        experience_level=vacancy.experience_title or '',
                        source='superjob',
                        parsing_mode='api',
                        published_at=vacancy.date_published or timezone.now(),
                        archived=vacancy.is_archive or False,
                        is_active=not (vacancy.is_archive or False),
                    )

                    batch_to_create.append(normalized)
                    migrated += 1

                except Exception as e:
                    logger.error(f'Ошибка миграции SuperJob вакансии {vacancy.id}: {e}')
                    errors += 1

            if batch_to_create and not dry_run:
                try:
                    with transaction.atomic():
                        NormalizedVacancy.objects.bulk_create(batch_to_create, ignore_conflicts=True)
                except Exception as e:
                    logger.error(f'Ошибка сохранения батча: {e}')
                    errors += len(batch_to_create)

            progress = min(offset + batch_size, total)
            self.stdout.write(f'Обработано: {progress}/{total} ({progress*100//total}%)')

        self.stdout.write(self.style.SUCCESS(
            f'✅ SuperJob: мигрировано {migrated}, пропущено {skipped}, ошибок {errors}'
        ))
