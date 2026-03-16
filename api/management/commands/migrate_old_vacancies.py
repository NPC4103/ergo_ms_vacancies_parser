"""
Миграция вакансий из таблиц площадок (vpm_hh_vacancy, vpm_hc_vacancy, vpm_sj_vacancy)
в нормализованную таблицу vpm_vacancy.

Использование:
    ergoms api migrate_old_vacancies --source=headhunter
    ergoms api migrate_old_vacancies --source=all --batch-size=500
    ergoms api migrate_old_vacancies --dry-run
"""

import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from modules.vacancies_parser.api.core.normalized_models import NormalizedVacancy
from modules.vacancies_parser.api.headhunter.models import Vacancy as HHVacancy
from modules.vacancies_parser.api.habr_career.models import Vacancy as HabrVacancy
from modules.vacancies_parser.api.superjob.models import SuperJobVacancy

logger = logging.getLogger('celery.module.vacancies_parser')


def _to_list(value):
    if value is None:
        return None
    if isinstance(value, list):
        return [str(x) for x in value if x] or None
    return [str(value)] if value else None


def _normalize_currency(raw):
    if not raw:
        return 'RUR'
    s = (raw or '').strip().upper()[:3]
    if s in ('RUR', 'RUB', 'USD', 'EUR', 'KZT', 'UAH', 'BYR'):
        return 'RUR' if s == 'RUB' else s
    return 'RUR'


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
            self.stdout.write(self.style.WARNING('ТЕСТОВЫЙ РЕЖИМ - данные не будут сохранены'))

        if source in ['headhunter', 'all']:
            self.migrate_headhunter(batch_size, dry_run)

        if source in ['habr_career', 'all']:
            self.migrate_habr_career(batch_size, dry_run)

        if source in ['superjob', 'all']:
            self.migrate_superjob(batch_size, dry_run)

        self.stdout.write(self.style.SUCCESS('\nМиграция завершена.'))

    def migrate_headhunter(self, batch_size, dry_run):
        """Мигрирует вакансии HeadHunter из vpm_hh_vacancy в vpm_vacancy."""
        self.stdout.write(self.style.HTTP_INFO('\nМиграция HeadHunter (vpm_hh_vacancy -> vpm_vacancy)...'))

        total = HHVacancy.objects.count()
        self.stdout.write(f'Всего в vpm_hh_vacancy: {total}')

        existing_ids = set(
            NormalizedVacancy.objects.filter(source='headhunter').values_list('source_id', flat=True)
        )
        self.stdout.write(f'Уже в vpm_vacancy (headhunter): {len(existing_ids)}')

        migrated = 0
        skipped = 0
        errors = 0

        for offset in range(0, total, batch_size):
            vacancies = HHVacancy.objects.all()[offset:offset + batch_size]
            batch_to_create = []

            for vacancy in vacancies:
                if str(vacancy.hh_id) in existing_ids:
                    skipped += 1
                    continue

                try:
                    desc_parts = [vacancy.description or '']
                    if vacancy.requirements:
                        desc_parts.append(f"\nТребования: {vacancy.requirements}")
                    if vacancy.responsibilities:
                        desc_parts.append(f"\nОбязанности: {vacancy.responsibilities}")

                    normalized = NormalizedVacancy(
                        source='headhunter',
                        source_id=str(vacancy.hh_id),
                        source_url=vacancy.url or '',
                        parsing_mode='api',
                        task_item=None,
                        title=vacancy.title or '',
                        company_name=vacancy.company_name or '',
                        company_url=vacancy.company_url or None,
                        description=''.join(desc_parts) or '',
                        salary_from=vacancy.salary_from,
                        salary_to=vacancy.salary_to,
                        salary_currency=_normalize_currency(vacancy.salary_currency),
                        salary_gross=vacancy.salary_gross if vacancy.salary_gross is not None else False,
                        area_name=vacancy.city or '',
                        address=vacancy.address or '',
                        experience=vacancy.experience_level or None,
                        employment_type=_to_list(vacancy.employment_type),
                        schedule=_to_list(vacancy.schedule_type),
                        key_skills=vacancy.key_skills if isinstance(vacancy.key_skills, list) else _to_list(vacancy.key_skills),
                        contacts=None,
                        is_active=vacancy.is_active,
                        archived=False,
                        published_at=vacancy.published_at or timezone.now(),
                        has_test=vacancy.has_test,
                        response_letter_required=vacancy.response_letter_required,
                        source_specific_data={
                            'requirements': vacancy.requirements,
                            'responsibilities': vacancy.responsibilities,
                            'employer_id': vacancy.employer_id,
                            'premium': vacancy.premium,
                        },
                    )
                    batch_to_create.append(normalized)
                    migrated += 1
                except Exception as e:
                    logger.error(f'Ошибка миграции HH вакансии {vacancy.id}: {e}')
                    errors += 1

            if batch_to_create and not dry_run:
                try:
                    with transaction.atomic():
                        NormalizedVacancy.objects.bulk_create(batch_to_create, batch_size=batch_size)
                    for n in batch_to_create:
                        existing_ids.add(n.source_id)
                except Exception as e:
                    logger.error(f'Ошибка сохранения батча: {e}')
                    errors += len(batch_to_create)

            progress = min(offset + batch_size, total)
            if total:
                self.stdout.write(f'Обработано: {progress}/{total} ({100 * progress // total}%)')

        self.stdout.write(self.style.SUCCESS(
            f'HeadHunter: мигрировано {migrated}, пропущено {skipped}, ошибок {errors}'
        ))

    def migrate_habr_career(self, batch_size, dry_run):
        """Мигрирует вакансии Habr Career из vpm_hc_vacancy в vpm_vacancy."""
        self.stdout.write(self.style.HTTP_INFO('\nМиграция Habr Career (vpm_hc_vacancy -> vpm_vacancy)...'))

        total = HabrVacancy.objects.count()
        if total == 0:
            self.stdout.write('Нет записей в vpm_hc_vacancy')
            return

        self.stdout.write(f'Всего в vpm_hc_vacancy: {total}')
        existing_ids = set(
            NormalizedVacancy.objects.filter(source='habr_career').values_list('source_id', flat=True)
        )
        self.stdout.write(f'Уже в vpm_vacancy (habr_career): {len(existing_ids)}')

        migrated = 0
        skipped = 0
        errors = 0

        for offset in range(0, total, batch_size):
            vacancies = HabrVacancy.objects.all()[offset:offset + batch_size]
            batch_to_create = []

            for vacancy in vacancies:
                sid = str(vacancy.habr_id)
                if sid in existing_ids:
                    skipped += 1
                    continue

                try:
                    normalized = NormalizedVacancy(
                        source='habr_career',
                        source_id=sid,
                        source_url=vacancy.url or '',
                        parsing_mode='api',
                        task_item=None,
                        title=vacancy.title or '',
                        company_name=vacancy.company_name or '',
                        company_url=vacancy.company_url or None,
                        description=vacancy.description or '',
                        salary_from=vacancy.salary_from,
                        salary_to=vacancy.salary_to,
                        salary_currency=_normalize_currency(vacancy.salary_currency),
                        salary_gross=vacancy.salary_gross,
                        area_name=vacancy.city or '',
                        address=vacancy.address or '',
                        employment_type=_to_list(vacancy.employment_type),
                        experience=vacancy.experience_level or None,
                        schedule=_to_list(vacancy.schedule_type),
                        key_skills=vacancy.skills if isinstance(vacancy.skills, list) else _to_list(vacancy.skills),
                        is_active=vacancy.is_active,
                        archived=False,
                        published_at=vacancy.published_at or timezone.now(),
                        has_test=vacancy.has_test,
                        response_letter_required=vacancy.response_letter_required,
                        source_specific_data={'requirements': vacancy.requirements, 'responsibilities': vacancy.responsibilities},
                    )
                    batch_to_create.append(normalized)
                    migrated += 1
                except Exception as e:
                    logger.error(f'Ошибка миграции Habr вакансии {vacancy.id}: {e}')
                    errors += 1

            if batch_to_create and not dry_run:
                try:
                    with transaction.atomic():
                        NormalizedVacancy.objects.bulk_create(batch_to_create, batch_size=batch_size)
                    for n in batch_to_create:
                        existing_ids.add(n.source_id)
                except Exception as e:
                    logger.error(f'Ошибка сохранения батча: {e}')
                    errors += len(batch_to_create)

            progress = min(offset + batch_size, total)
            if total:
                self.stdout.write(f'Обработано: {progress}/{total} ({100 * progress // total}%)')

        self.stdout.write(self.style.SUCCESS(
            f'Habr Career: мигрировано {migrated}, пропущено {skipped}, ошибок {errors}'
        ))

    def migrate_superjob(self, batch_size, dry_run):
        """Мигрирует вакансии SuperJob из vpm_sj_vacancy в vpm_vacancy."""
        self.stdout.write(self.style.HTTP_INFO('\nМиграция SuperJob (vpm_sj_vacancy -> vpm_vacancy)...'))

        total = SuperJobVacancy.objects.count()
        if total == 0:
            self.stdout.write('Нет записей в vpm_sj_vacancy')
            return

        self.stdout.write(f'Всего в vpm_sj_vacancy: {total}')
        existing_ids = set(
            NormalizedVacancy.objects.filter(source='superjob').values_list('source_id', flat=True)
        )
        self.stdout.write(f'Уже в vpm_vacancy (superjob): {len(existing_ids)}')

        migrated = 0
        skipped = 0
        errors = 0

        for offset in range(0, total, batch_size):
            vacancies = SuperJobVacancy.objects.all()[offset:offset + batch_size]
            batch_to_create = []

            for vacancy in vacancies:
                sid = str(vacancy.superjob_id)
                if sid in existing_ids:
                    skipped += 1
                    continue

                try:
                    normalized = NormalizedVacancy(
                        source='superjob',
                        source_id=sid,
                        source_url=vacancy.url or '',
                        parsing_mode='api',
                        task_item=None,
                        title=vacancy.title or '',
                        company_name=vacancy.company_name or '',
                        company_url=vacancy.company_url or None,
                        description=vacancy.description or '',
                        salary_from=vacancy.salary_from,
                        salary_to=vacancy.salary_to,
                        salary_currency=_normalize_currency(vacancy.salary_currency),
                        salary_gross=vacancy.salary_gross if vacancy.salary_gross is not None else False,
                        area_name=vacancy.city or '',
                        address=vacancy.address or '',
                        employment_type=_to_list(vacancy.employment_type),
                        experience=vacancy.experience_level or None,
                        schedule=_to_list(vacancy.schedule_type),
                        key_skills=vacancy.key_skills if isinstance(vacancy.key_skills, list) else _to_list(vacancy.key_skills),
                        is_active=vacancy.is_active,
                        archived=False,
                        published_at=vacancy.published_at or timezone.now(),
                        has_test=vacancy.has_test,
                        response_letter_required=vacancy.response_letter_required,
                        source_specific_data={
                            'requirements': getattr(vacancy, 'requirements', None),
                            'responsibilities': getattr(vacancy, 'responsibilities', None),
                            'employer_id': getattr(vacancy, 'employer_id', None),
                        },
                    )
                    batch_to_create.append(normalized)
                    migrated += 1
                except Exception as e:
                    logger.error(f'Ошибка миграции SuperJob вакансии {vacancy.id}: {e}')
                    errors += 1

            if batch_to_create and not dry_run:
                try:
                    with transaction.atomic():
                        NormalizedVacancy.objects.bulk_create(batch_to_create, batch_size=batch_size)
                    for n in batch_to_create:
                        existing_ids.add(n.source_id)
                except Exception as e:
                    logger.error(f'Ошибка сохранения батча: {e}')
                    errors += len(batch_to_create)

            progress = min(offset + batch_size, total)
            if total:
                self.stdout.write(f'Обработано: {progress}/{total} ({100 * progress // total}%)')

        self.stdout.write(self.style.SUCCESS(
            f'SuperJob: мигрировано {migrated}, пропущено {skipped}, ошибок {errors}'
        ))
