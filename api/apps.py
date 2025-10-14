from django.apps import AppConfig

class VacanciesParserConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.vacancies_parser.api'
    label = 'vacancies_parser'