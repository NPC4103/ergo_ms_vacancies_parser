"""
Модели модуля vacancies_parser.

Реэкспортирует модели из core для обнаружения Django.
"""

from .core.models import ParsingTask, TaskItem
from .core.normalized_models import (
    NormalizedVacancy,
    VacancyChangeHistory,
    ParsingStatistics
)

__all__ = [
    'ParsingTask',
    'TaskItem',
    'NormalizedVacancy',
    'VacancyChangeHistory',
    'ParsingStatistics',
]
