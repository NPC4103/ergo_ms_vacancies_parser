"""
Генератор поисковых запросов на основе технологий.

Создает оптимизированные поисковые запросы для HeadHunter
используя базу данных технологий и их синонимов.
"""

import logging
from typing import List, Dict, Set, Tuple
from django.db.models import Q

from modules.competence_core.api.skill_map.models import Technology, TechnologyCategory

logger = logging.getLogger('modules.vacancies_parser.headhunter')


class TechnologySearchGenerator:
    """
    Генератор поисковых запросов для парсинга вакансий по технологиям.
    
    Использует базу данных технологий для создания списка поисковых запросов,
    оптимизированных для поиска на HeadHunter.
    """
    
    def __init__(self):
        """Инициализация генератора."""
        self.technologies = []
        self.loaded = False
    
    def load_technologies(self, 
                         categories: List[str] = None,
                         min_popularity: int = 0,
                         include_aliases: bool = True,
                         limit: int = None) -> int:
        """
        Загрузка технологий из базы данных.
        
        Args:
            categories (List[str]): Список категорий для фильтрации (LANG, FRAMEWORK и т.д.)
            min_popularity (int): Минимальная популярность технологии
            include_aliases (bool): Включать ли алиасы в результат
            limit (int): Ограничение количества технологий
        
        Returns:
            int: Количество загруженных технологий
        """
        logger.info('Загрузка технологий для генерации поисковых запросов...')
        
        # Формируем запрос
        query = Technology.objects.all()
        
        # Фильтрация по категориям
        if categories:
            query = query.filter(category__in=categories)
        
        # Фильтрация по популярности
        if min_popularity > 0:
            query = query.filter(popularity__gte=min_popularity)
        
        # Сортировка по популярности и релевантности
        query = query.order_by('-popularity', '-relevance', 'name')
        
        # Ограничение количества
        if limit:
            query = query[:limit]
        
        # Загружаем алиасы если требуется
        if include_aliases:
            query = query.prefetch_related('aliases')
        
        self.technologies = list(query)
        self.loaded = True
        
        logger.info(f'Загружено {len(self.technologies)} технологий')
        
        return len(self.technologies)
    
    def generate_search_queries(self, 
                                use_aliases: bool = True,
                                max_queries: int = None,
                                combine_with_keywords: List[str] = None) -> List[str]:
        """
        Генерация списка поисковых запросов.
        
        Args:
            use_aliases (bool): Использовать ли алиасы как отдельные запросы
            max_queries (int): Максимальное количество запросов
            combine_with_keywords (List[str]): Дополнительные ключевые слова для комбинации
                                              (например, ['разработчик', 'developer'])
        
        Returns:
            List[str]: Список поисковых запросов
        """
        if not self.loaded:
            self.load_technologies()
        
        queries = []
        
        for tech in self.technologies:
            # Добавляем основное название
            queries.append(tech.name)
            
            # Добавляем алиасы
            if use_aliases and hasattr(tech, 'aliases'):
                for alias_obj in tech.aliases.all():
                    alias = alias_obj.alias
                    # Добавляем только если алиас существенно отличается от основного названия
                    if alias.lower() != tech.name.lower():
                        queries.append(alias)
            
            # Комбинируем с ключевыми словами
            if combine_with_keywords:
                for keyword in combine_with_keywords:
                    queries.append(f"{tech.name} {keyword}")
        
        # Убираем дубликаты, сохраняя порядок
        seen = set()
        unique_queries = []
        for query in queries:
            query_lower = query.lower()
            if query_lower not in seen:
                seen.add(query_lower)
                unique_queries.append(query)
        
        # Ограничиваем количество если требуется
        if max_queries and len(unique_queries) > max_queries:
            unique_queries = unique_queries[:max_queries]
        
        logger.info(f'Сгенерировано {len(unique_queries)} поисковых запросов')
        
        return unique_queries
    
    def generate_by_category(self, 
                           category: str,
                           use_aliases: bool = True,
                           max_per_category: int = None) -> List[str]:
        """
        Генерация запросов для конкретной категории.
        
        Args:
            category (str): Категория технологий (LANG, FRAMEWORK и т.д.)
            use_aliases (bool): Использовать ли алиасы
            max_per_category (int): Максимум запросов для категории
        
        Returns:
            List[str]: Список поисковых запросов для категории
        """
        # Загружаем технологии только указанной категории
        self.load_technologies(categories=[category])
        
        return self.generate_search_queries(
            use_aliases=use_aliases,
            max_queries=max_per_category
        )
    
    def generate_grouped_by_category(self, 
                                    use_aliases: bool = True,
                                    max_per_category: int = None) -> Dict[str, List[str]]:
        """
        Генерация запросов сгруппированных по категориям.
        
        Args:
            use_aliases (bool): Использовать ли алиасы
            max_per_category (int): Максимум запросов на категорию
        
        Returns:
            Dict[str, List[str]]: Словарь {категория: [запросы]}
        """
        result = {}
        
        # Получаем все категории
        categories = [choice[0] for choice in TechnologyCategory.choices]
        
        for category in categories:
            # Загружаем технологии категории
            count = self.load_technologies(categories=[category])
            
            if count > 0:
                queries = self.generate_search_queries(
                    use_aliases=use_aliases,
                    max_queries=max_per_category
                )
                result[category] = queries
        
        logger.info(f'Сгенерированы запросы для {len(result)} категорий')
        
        return result
    
    def generate_priority_queries(self, 
                                 top_n: int = 50,
                                 use_aliases: bool = False) -> List[str]:
        """
        Генерация приоритетных запросов (самые популярные технологии).
        
        Args:
            top_n (int): Количество топовых технологий
            use_aliases (bool): Использовать ли алиасы
        
        Returns:
            List[str]: Список приоритетных поисковых запросов
        """
        # Загружаем только топовые технологии
        self.load_technologies(limit=top_n, include_aliases=use_aliases)
        
        return self.generate_search_queries(use_aliases=use_aliases)
    
    def get_statistics(self) -> Dict:
        """
        Получение статистики по загруженным технологиям.
        
        Returns:
            Dict: Статистика по технологиям
        """
        if not self.loaded:
            return {'error': 'Технологии не загружены'}
        
        stats = {
            'total_technologies': len(self.technologies),
            'by_category': {},
            'total_aliases': 0
        }
        
        for tech in self.technologies:
            category = tech.category
            stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
            
            if hasattr(tech, 'aliases'):
                stats['total_aliases'] += tech.aliases.count()
        
        return stats

