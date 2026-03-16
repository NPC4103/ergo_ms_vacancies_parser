from django.contrib import admin

from .core.models import ParsingTask, TaskItem
from .core.monitoring_models import TaskRun, ExternalApiEvent


@admin.register(ParsingTask)
class ParsingTaskAdmin(admin.ModelAdmin):
    list_display = ('id', 'source', 'parsing_mode', 'status', 'total_items', 'completed_items', 'failed_items', 'updated_at')
    list_filter = ('source', 'parsing_mode', 'status')
    search_fields = ('id', 'name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(TaskItem)
class TaskItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'task_id', 'status', 'attempts', 'max_attempts', 'worker_id', 'lease_expires_at', 'updated_at')
    list_filter = ('status',)
    search_fields = ('id', 'task_id', 'worker_id')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(TaskRun)
class TaskRunAdmin(admin.ModelAdmin):
    list_display = (
        'started_at', 'source', 'task_name', 'status',
        'duration_sec', 'processed', 'saved', 'updated',
        'errors', 'timeouts', 'http_429', 'retries',
    )
    list_filter = ('source', 'status', 'task_name')
    search_fields = ('celery_task_id', 'task_name', 'parsing_task_id', 'error_type')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ExternalApiEvent)
class ExternalApiEventAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'source', 'event_type', 'endpoint', 'count', 'celery_task_id')
    list_filter = ('source', 'event_type')
    search_fields = ('endpoint', 'celery_task_id')
    readonly_fields = ('created_at',)

