import logging
from django.apps import AppConfig

logger = logging.getLogger('celery.module.vacancies_parser')


class VacanciesParserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.vacancies_parser.api'
    label = 'vacancies_parser'
    
    def __init__(self, app_name, app_module):
        """Инициализация конфигурации приложения"""
        super().__init__(app_name, app_module)
        # Флаг для предотвращения повторного логирования в рамках одного экземпляра
        self._ready_called = False
    
    def ready(self):
        """Инициализация модуля при загрузке"""
        # Импорт парсеров для гарантированной регистрации в ParserFactory
        # Регистрация происходит автоматически при импорте модулей
        from .core.parsers import api_parsers, html_parsers  # noqa
        
        # Логируем итоговое состояние регистрации только один раз для этого экземпляра
        # (Django может вызывать ready() несколько раз в режиме разработки)
        if not self._ready_called:
            from .core.parsers.base import ParserFactory
            available_parsers = ParserFactory.get_available_parsers()
            if available_parsers:
                parsers_list = ', '.join([f"{p['source']}/{p['mode']}" for p in available_parsers])
                logger.info(f"Модуль vacancies_parser инициализирован. Доступные парсеры: {parsers_list}")
            self._ready_called = True