from django.apps import AppConfig

class VacanciesParserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.vacancies_parser.api'
    label = 'vacancies_parser'
    
    def ready(self):
        """Инициализация модуля при загрузке"""
        # Импорт парсеров для гарантированной регистрации в ParserFactory
        from .core.parsers import api_parsers, html_parsers  # noqa