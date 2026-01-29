"""
ViewSets для API модуля vacancies_parser.

Содержит:
- ParsingTaskViewSet - управление задачами парсинга
- TaskItemViewSet - просмотр элементов задач
- NormalizedVacancyViewSet - просмотр вакансий
- ParsingStatisticsViewSet - просмотр статистики
"""

import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Count
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from src.core.utils.mixins import SwaggerSafeMixin
from .models import ParsingTask, TaskItem
from .normalized_models import NormalizedVacancy, VacancyChangeHistory, ParsingStatistics
from .serializers import (
    ParsingTaskListSerializer,
    ParsingTaskDetailSerializer,
    ParsingTaskCreateSerializer,
    TaskItemSerializer,
    NormalizedVacancyListSerializer,
    NormalizedVacancyDetailSerializer,
    VacancyChangeHistorySerializer,
    ParsingStatisticsSerializer,
    TaskProgressSerializer,
    TaskControlSerializer,
)
from .scheduler import default_scheduler
# Импортируем задачи напрямую из tasks.py (файл), а не из пакета tasks/ (директория)
# Используем прямой импорт модуля для избежания конфликта с пакетом core/tasks/
from modules.vacancies_parser.api.core import tasks as core_tasks_module
pause_task = core_tasks_module.pause_task
resume_task = core_tasks_module.resume_task
stop_task = core_tasks_module.stop_task

logger = logging.getLogger('celery.module.vacancies_parser.api')


class StandardResultsSetPagination(PageNumberPagination):
    """Стандартная пагинация для модуля vacancies_parser"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class ParsingTaskViewSet(SwaggerSafeMixin, viewsets.ModelViewSet):
    """
    ViewSet для управления задачами парсинга.
    
    Endpoints:
    - GET /api/vacancies_parser/tasks/ - список задач
    - POST /api/vacancies_parser/tasks/ - создание задачи
    - GET /api/vacancies_parser/tasks/{id}/ - детальная информация
    - PATCH /api/vacancies_parser/tasks/{id}/ - обновление задачи
    - DELETE /api/vacancies_parser/tasks/{id}/ - удаление задачи
    
    Custom actions:
    - GET /api/vacancies_parser/tasks/{id}/progress/ - прогресс выполнения
    - POST /api/vacancies_parser/tasks/{id}/pause/ - приостановка
    - POST /api/vacancies_parser/tasks/{id}/resume/ - возобновление
    - POST /api/vacancies_parser/tasks/{id}/stop/ - остановка
    - GET /api/vacancies_parser/tasks/{id}/items/ - элементы задачи
    - GET /api/vacancies_parser/tasks/{id}/statistics/ - статистика задачи
    """
    
    queryset = ParsingTask.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    
    # Фильтры
    filterset_fields = {
        'source': ['exact', 'in'],
        'parsing_mode': ['exact', 'in'],
        'status': ['exact', 'in'],
        'created_at': ['gte', 'lte'],
    }
    
    # Поиск
    search_fields = ['name', 'config']
    
    # Сортировка
    ordering_fields = ['created_at', 'updated_at', 'progress_percent', 'total_items']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        """Выбор serializer в зависимости от action"""
        if self.action == 'list':
            return ParsingTaskListSerializer
        elif self.action == 'create':
            return ParsingTaskCreateSerializer
        elif self.action == 'progress':
            return TaskProgressSerializer
        elif self.action in ['pause', 'resume', 'stop']:
            return TaskControlSerializer
        else:
            return ParsingTaskDetailSerializer
    
    def get_queryset(self):
        """Фильтрация queryset"""
        queryset = super().get_queryset()
        
        # Оптимизация: select_related для ForeignKey
        queryset = queryset.select_related('created_by')
        
        # Проверка на Swagger fake view или AnonymousUser
        if self.is_swagger_fake_view():
            return queryset.none()
        
        # Проверка на аутентифицированного пользователя
        if not hasattr(self.request, 'user') or not self.request.user.is_authenticated:
            return queryset.none()
        
        # Фильтр по пользователю (если не admin)
        if not self.request.user.is_staff:
            queryset = queryset.filter(
                Q(created_by=self.request.user) | Q(created_by__isnull=True)
            )
        
        return queryset
    
    def perform_create(self, serializer):
        """Создание задачи через Celery"""
        result = serializer.save()
        return result
    
    @action(detail=True, methods=['get'], url_path='progress')
    def progress(self, request, pk=None):
        """
        Получение прогресса выполнения задачи.
        
        GET /api/vacancies_parser/tasks/{id}/progress/
        
        Response:
        {
            "total": 100,
            "pending": 50,
            "in_progress": 10,
            "completed": 38,
            "failed": 2,
            "retrying": 0,
            "blocked": 0,
            "progress_percent": 38.0,
            "task_status": "running"
        }
        """
        task = self.get_object()
        progress_data = default_scheduler.get_task_progress(task.id)
        
        serializer = TaskProgressSerializer(progress_data)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], url_path='pause')
    def pause(self, request, pk=None):
        """
        Приостановка задачи.
        
        POST /api/vacancies_parser/tasks/{id}/pause/
        """
        task = self.get_object()
        
        serializer = TaskControlSerializer(
            data={'action': 'pause'},
            context={'task_id': task.id}
        )
        serializer.is_valid(raise_exception=True)
        
        # Запуск Celery задачи приостановки
        pause_task.apply_async(args=[task.id])
        
        logger.info(f"Запущена приостановка задачи {task.id}")
        
        return Response({
            'status': 'success',
            'message': f'Задача {task.id} приостанавливается'
        })
    
    @action(detail=True, methods=['post'], url_path='resume')
    def resume(self, request, pk=None):
        """
        Возобновление задачи.
        
        POST /api/vacancies_parser/tasks/{id}/resume/
        """
        task = self.get_object()
        
        serializer = TaskControlSerializer(
            data={'action': 'resume'},
            context={'task_id': task.id}
        )
        serializer.is_valid(raise_exception=True)
        
        # Запуск Celery задачи возобновления
        resume_task.apply_async(args=[task.id])
        
        logger.info(f"Запущено возобновление задачи {task.id}")
        
        return Response({
            'status': 'success',
            'message': f'Задача {task.id} возобновляется'
        })
    
    @action(detail=True, methods=['post'], url_path='stop')
    def stop(self, request, pk=None):
        """
        Остановка задачи.
        
        POST /api/vacancies_parser/tasks/{id}/stop/
        """
        task = self.get_object()
        
        serializer = TaskControlSerializer(
            data={'action': 'stop'},
            context={'task_id': task.id}
        )
        serializer.is_valid(raise_exception=True)
        
        # Запуск Celery задачи остановки
        stop_task.apply_async(args=[task.id])
        
        logger.info(f"Запущена остановка задачи {task.id}")
        
        return Response({
            'status': 'success',
            'message': f'Задача {task.id} останавливается'
        })
    
    @action(detail=True, methods=['get'], url_path='items')
    def items(self, request, pk=None):
        """
        Получение списка элементов задачи.
        
        GET /api/vacancies_parser/tasks/{id}/items/
        
        Query params:
        - status: фильтр по статусу (pending, in_progress, completed, failed, etc.)
        - limit: количество элементов (по умолчанию 100)
        - offset: смещение для пагинации
        """
        task = self.get_object()
        
        # Фильтры с оптимизацией
        items_qs = TaskItem.objects.filter(task=task).select_related('task')
        
        status_filter = request.query_params.get('status')
        if status_filter:
            items_qs = items_qs.filter(status=status_filter)
        
        # Пагинация
        limit = int(request.query_params.get('limit', 100))
        offset = int(request.query_params.get('offset', 0))
        
        total_count = items_qs.count()
        items = items_qs[offset:offset+limit]
        
        serializer = TaskItemSerializer(items, many=True)
        
        return Response({
            'count': total_count,
            'limit': limit,
            'offset': offset,
            'results': serializer.data
        })
    
    @action(detail=True, methods=['get'], url_path='statistics')
    def statistics(self, request, pk=None):
        """
        Получение статистики по задаче.
        
        GET /api/vacancies_parser/tasks/{id}/statistics/
        """
        task = self.get_object()
        
        try:
            # Оптимизация: select_related для ForeignKey
            stats = ParsingStatistics.objects.select_related('task', 'task__created_by').get(task=task)
            serializer = ParsingStatisticsSerializer(stats)
            return Response(serializer.data)
        except ParsingStatistics.DoesNotExist:
            return Response({
                'status': 'not_available',
                'message': 'Статистика еще не сформирована (задача не завершена)'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['get'], url_path='sources')
    def sources(self, request):
        """
        Получение списка доступных источников и режимов парсинга.
        
        GET /api/vacancies_parser/tasks/sources/
        
        Response:
        {
            "sources": [
                {
                    "id": "headhunter",
                    "name": "HeadHunter",
                    "modes": [
                        {"id": "api", "name": "API режим", "available": true},
                        {"id": "html", "name": "HTML режим", "available": true}
                    ]
                },
                ...
            ]
        }
        """
        from .parsers.base import ParserFactory
        
        sources_data = []
        
        for source_id, source_name in ParsingTask.SOURCE_CHOICES:
            modes_data = []
            
            for mode_id, mode_name in ParsingTask.PARSING_MODE_CHOICES:
                # Проверяем доступность парсера
                try:
                    parser_class = ParserFactory.get_parser(source_id, mode_id)
                    available = parser_class is not None
                except (KeyError, Exception):
                    available = False
                
                modes_data.append({
                    'id': mode_id,
                    'name': mode_name,
                    'available': available
                })
            
            sources_data.append({
                'id': source_id,
                'name': source_name,
                'modes': modes_data
            })
        
        return Response({'sources': sources_data})


class TaskItemViewSet(SwaggerSafeMixin, viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для просмотра элементов задач (read-only).
    
    Endpoints:
    - GET /api/vacancies_parser/items/ - список элементов
    - GET /api/vacancies_parser/items/{id}/ - детальная информация
    """
    
    queryset = TaskItem.objects.all().select_related('task', 'task__created_by')
    serializer_class = TaskItemSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    
    filterset_fields = {
        'task': ['exact'],
        'status': ['exact', 'in'],
        'last_error_type': ['exact', 'in'],
        'created_at': ['gte', 'lte'],
    }
    
    ordering_fields = ['created_at', 'updated_at', 'attempts_count']
    ordering = ['-created_at']


class NormalizedVacancyViewSet(SwaggerSafeMixin, viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для просмотра вакансий (read-only).
    
    Endpoints:
    - GET /api/vacancies_parser/vacancies/ - список вакансий
    - GET /api/vacancies_parser/vacancies/{id}/ - детальная информация
    - GET /api/vacancies_parser/vacancies/{id}/changes/ - история изменений
    """
    
    queryset = NormalizedVacancy.objects.all().select_related('task_item', 'task_item__task')
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    
    filterset_fields = {
        'source': ['exact', 'in'],
        'parsing_mode': ['exact', 'in'],
        'company_name': ['exact', 'icontains'],
        'area_name': ['exact', 'icontains'],
        'archived': ['exact'],
        'published_at': ['gte', 'lte'],
        'created_at': ['gte', 'lte'],
    }
    
    search_fields = ['title', 'company_name', 'description', 'area_name']
    ordering_fields = ['created_at', 'updated_at', 'published_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return NormalizedVacancyListSerializer
        else:
            return NormalizedVacancyDetailSerializer
    
    @action(detail=True, methods=['get'], url_path='changes')
    def changes(self, request, pk=None):
        """
        Получение истории изменений вакансии.
        
        GET /api/vacancies_parser/vacancies/{id}/changes/
        """
        vacancy = self.get_object()
        changes = VacancyChangeHistory.objects.filter(vacancy=vacancy).order_by('-changed_at')
        
        serializer = VacancyChangeHistorySerializer(changes, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def export(self, request):
        """
        Экспорт вакансий в CSV.
        
        GET /api/vacancies_parser/vacancies/export/
        """
        import csv
        import io
        from django.http import HttpResponse
        
        # Получаем отфильтрованный queryset
        queryset = self.filter_queryset(self.get_queryset())
        
        # CSV экспорт
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Заголовки
        writer.writerow([
            'ID', 'Источник', 'Название', 'Компания', 'Город',
            'Зарплата от', 'Зарплата до', 'Валюта',
            'Опыт', 'Занятость', 'График',
            'Опубликовано', 'Создано', 'URL'
        ])
        
        # Данные
        for vacancy in queryset:
            writer.writerow([
                vacancy.id,
                vacancy.get_source_display(),
                vacancy.title,
                vacancy.company_name or '',
                vacancy.area_name or '',
                vacancy.salary_from or '',
                vacancy.salary_to or '',
                vacancy.salary_currency or '',
                vacancy.experience or '',
                vacancy.employment or '',
                vacancy.schedule or '',
                vacancy.published_at.isoformat() if vacancy.published_at else '',
                vacancy.created_at.isoformat() if vacancy.created_at else '',
                vacancy.url or ''
            ])
        
        response = HttpResponse(output.getvalue(), content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = 'attachment; filename="vacancies.csv"'
        return response


class ParsingStatisticsViewSet(SwaggerSafeMixin, viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для просмотра статистики парсинга (read-only).
    
    Endpoints:
    - GET /api/vacancies_parser/statistics/ - список статистик
    - GET /api/vacancies_parser/statistics/{id}/ - детальная информация
    """
    
    queryset = ParsingStatistics.objects.all().select_related('task', 'task__created_by')
    serializer_class = ParsingStatisticsSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    
    filterset_fields = {
        'task': ['exact'],
        'started_at': ['gte', 'lte'],
        'finished_at': ['gte', 'lte'],
    }
    
    ordering_fields = ['started_at', 'finished_at', 'items_per_second']
    ordering = ['-started_at']
