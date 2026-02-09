import logging

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Avg, Min, Max, Q
from django.utils import timezone
from datetime import timedelta
from celery.result import AsyncResult

from src.core.utils.mixins import SwaggerSafeMixin
from .models import Vacancy, VacancyVersion, VacancyChangeHistory
from .serializers import (
    VacancyListSerializer, VacancyDetailSerializer, VacancyVersionSerializer,
    VacancyChangeHistorySerializer, VacancyStatsSerializer, ParsingTaskStatusSerializer,
)
from .tasks import (
    parse_habr_vacancies_task,
    parse_habr_archived_vacancies_task,
    parse_habr_all_vacancies_task,
)
from modules.vacancies_parser.api.core.utils.task_runner import safe_task_run
from modules.vacancies_parser.api.core.utils.celery_broker import BrokerUnavailableError

logger = logging.getLogger('modules.vacancies_parser.habr_career')


class VacancyViewSet(SwaggerSafeMixin, viewsets.ReadOnlyModelViewSet):
    """ViewSet для работы с вакансиями Хабр Карьеры"""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['title', 'company_name', 'description', 'city', 'qualification']
    ordering_fields = ['published_at', 'created_at', 'salary_from', 'salary_to', 'title']
    ordering = ['-published_at']
    filterset_fields = {
        'city': ['exact', 'icontains'],
        'employment_type': ['exact'],
        'experience_level': ['exact'],
        'qualification': ['exact', 'icontains'],
        'is_active': ['exact'],
        'premium': ['exact'],
        'marked': ['exact'],
        'published_at': ['gte', 'lte', 'exact'],
        'salary_from': ['gte'],
        'salary_to': ['lte'],
    }

    def get_queryset(self):
        if self.is_swagger_fake_view():
            return Vacancy.objects.none()

        queryset = Vacancy.objects.all()

        skills = self.request.query_params.getlist('skills')
        if skills:
            for skill in skills:
                queryset = queryset.filter(skills__icontains=skill)

        salary_min = self.request.query_params.get('salary_min')
        salary_max = self.request.query_params.get('salary_max')
        if salary_min:
            queryset = queryset.filter(
                Q(salary_to__gte=int(salary_min)) | Q(salary_from__gte=int(salary_min))
            )
        if salary_max:
            queryset = queryset.filter(
                Q(salary_from__lte=int(salary_max)) | Q(salary_to__lte=int(salary_max))
            )

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return VacancyListSerializer
        return VacancyDetailSerializer

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        """Получить все версии вакансии"""
        vacancy = self.get_object()
        versions = vacancy.versions.all().select_related('vacancy')
        serializer = VacancyVersionSerializer(versions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def version_detail(self, request, pk=None):
        """Получить детали конкретной версии"""
        vacancy = self.get_object()
        version_number = request.query_params.get('version')

        if not version_number:
            return Response(
                {'error': 'Не указан номер версии'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            version = vacancy.versions.get(version_number=int(version_number))
            serializer = VacancyVersionSerializer(version)
            return Response(serializer.data)
        except VacancyVersion.DoesNotExist:
            return Response(
                {'error': 'Версия не найдена'},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=True, methods=['get'])
    def changes(self, request, pk=None):
        """Получить историю изменений вакансии"""
        vacancy = self.get_object()
        version_number = request.query_params.get('version')

        if version_number:
            try:
                version = vacancy.versions.select_related('vacancy').get(
                    version_number=int(version_number)
                )
                changes = version.changes.all().select_related('vacancy', 'version')
            except VacancyVersion.DoesNotExist:
                return Response(
                    {'error': 'Версия не найдена'},
                    status=status.HTTP_404_NOT_FOUND,
                )
        else:
            changes = vacancy.change_history.all().select_related('vacancy', 'version')

        serializer = VacancyChangeHistorySerializer(changes, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Получить статистику по вакансиям"""
        if self.is_swagger_fake_view():
            return Response(VacancyStatsSerializer({}).data)

        queryset = self.get_queryset()

        total_vacancies = queryset.count()
        active_vacancies = queryset.filter(is_active=True).count()

        salary_stats = queryset.filter(
            Q(salary_from__isnull=False) | Q(salary_to__isnull=False)
        ).aggregate(
            avg_salary_from=Avg('salary_from'),
            avg_salary_to=Avg('salary_to'),
            min_salary_from=Min('salary_from'),
            max_salary_to=Max('salary_to'),
        )

        vacancies_by_city = dict(
            queryset.values('city').annotate(count=Count('id')).values_list('city', 'count')
        )

        vacancies_by_qualification = dict(
            queryset.exclude(qualification__isnull=True)
            .values('qualification')
            .annotate(count=Count('id'))
            .values_list('qualification', 'count')
        )

        vacancies_by_experience = dict(
            queryset.exclude(experience_level__isnull=True)
            .values('experience_level')
            .annotate(count=Count('id'))
            .values_list('experience_level', 'count')
        )

        recent_date = timezone.now() - timedelta(days=7)
        recent_vacancies_count = queryset.filter(published_at__gte=recent_date).count()

        stats_data = {
            'total_vacancies': total_vacancies,
            'active_vacancies': active_vacancies,
            'avg_salary_from': salary_stats['avg_salary_from'],
            'avg_salary_to': salary_stats['avg_salary_to'],
            'min_salary_from': salary_stats['min_salary_from'],
            'max_salary_to': salary_stats['max_salary_to'],
            'vacancies_by_city': vacancies_by_city,
            'vacancies_by_qualification': vacancies_by_qualification,
            'vacancies_by_experience': vacancies_by_experience,
            'recent_vacancies_count': recent_vacancies_count,
        }

        serializer = VacancyStatsSerializer(stats_data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def task_status(self, request):
        """Получить статус задачи парсинга"""
        task_id = request.query_params.get('task_id')

        if not task_id:
            return Response(
                {'error': 'Не указан task_id'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            task_result = AsyncResult(task_id)
            status_data = {
                'task_id': task_id,
                'status': task_result.status,
                'progress': None,
                'result': None,
                'error': None,
            }

            if task_result.ready():
                if task_result.successful():
                    status_data['result'] = task_result.result
                else:
                    status_data['error'] = str(task_result.info)
            else:
                if hasattr(task_result, 'info') and isinstance(task_result.info, dict):
                    status_data['progress'] = task_result.info

            serializer = ParsingTaskStatusSerializer(status_data)
            return Response(serializer.data)
        except Exception as e:
            logger.error(f'Ошибка при получении статуса задачи {task_id}: {str(e)}', exc_info=True)
            return Response(
                {'error': f'Ошибка при получении статуса: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ParsingControlViewSet(SwaggerSafeMixin, viewsets.ViewSet):
    """ViewSet для управления парсингом вакансий Хабр Карьеры"""
    permission_classes = [permissions.IsAuthenticated]

    def _run_parsing_task(self, request, task_func, message, extra_params=None):
        """Общий метод запуска задачи парсинга"""
        access_token = request.data.get('access_token')
        if not access_token:
            return Response(
                {'error': 'Не указан access_token'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        params = {
            'access_token': access_token,
            'pages': request.data.get('pages', 5),
            'delay': request.data.get('delay', 1.0),
        }
        if extra_params:
            params.update(extra_params)

        try:
            result = safe_task_run(
                task_func, params,
                prefer_async=True,
                fallback_to_sync=False,
            )
            return Response({
                'task_id': result.id,
                'status': 'started',
                'message': message,
            }, status=status.HTTP_202_ACCEPTED)
        except BrokerUnavailableError as e:
            logger.error(f'Ошибка брокера: {e}')
            return Response({
                'error': f'Celery брокер недоступен: {e}',
                'broker_error': True,
                'suggestion': 'Запустите Celery worker: ergoms start-worker',
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            logger.error(f'Ошибка при запуске задачи парсинга: {e}', exc_info=True)
            return Response(
                {'error': f'Ошибка при запуске задачи: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=['post'])
    def parse_active(self, request):
        """Запустить парсинг активных вакансий"""
        return self._run_parsing_task(
            request,
            parse_habr_vacancies_task,
            'Парсинг активных вакансий Хабр Карьеры запущен',
            extra_params={'get_details': request.data.get('get_details', True)},
        )

    @action(detail=False, methods=['post'])
    def parse_archived(self, request):
        """Запустить парсинг архивных вакансий"""
        return self._run_parsing_task(
            request,
            parse_habr_archived_vacancies_task,
            'Парсинг архивных вакансий Хабр Карьеры запущен',
        )

    @action(detail=False, methods=['post'])
    def parse_all(self, request):
        """Запустить парсинг всех вакансий (активных и архивных)"""
        return self._run_parsing_task(
            request,
            parse_habr_all_vacancies_task,
            'Парсинг всех вакансий Хабр Карьеры запущен',
            extra_params={'get_details': request.data.get('get_details', True)},
        )
