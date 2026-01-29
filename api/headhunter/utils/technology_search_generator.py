"""
Генератор поисковых запросов на основе технологий.

Создает оптимизированные поисковые запросы для HeadHunter
используя базу данных технологий и их синонимов.
"""

import logging
from typing import List, Dict, Set, Tuple, Optional
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
                         categories: Optional[List[str]] = None,
                         min_popularity: int = 0,
                         include_aliases: bool = True,
                         limit: Optional[int] = None) -> int:
        """
        Загрузка технологий из базы данных.
        
        Args:
            categories (List[str]): Список категорий для фильтрации (LANG, FRAMEWORK и т.д.)
            min_popularity (int): Минимальная популярность технологии
            include_aliases (bool): Включать ли алиасы в результат (используется для логирования)
            limit (int): Ограничение количества технологий
        
        Returns:
            int: Количество загруженных технологий
        """
        logger.info('Загрузка технологий для генерации поисковых запросов...')
        
        # Формируем запрос
        query = Technology.objects.all()  # type: ignore[attr-defined]
        
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
        
        # Всегда используем prefetch_related для оптимизации загрузки алиасов
        # Это позволяет избежать N+1 запросов при работе с алиасами
        query = query.prefetch_related('aliases')
        
        self.technologies = list(query)
        self.loaded = True
        
        # Подсчитываем общее количество алиасов для логирования
        total_aliases = sum(
            len(tech._prefetched_objects_cache.get('aliases', []))
            if hasattr(tech, '_prefetched_objects_cache') 
            else tech.aliases.count()
            for tech in self.technologies
        )
        
        logger.info(f'Загружено {len(self.technologies)} технологий')
        if include_aliases:
            logger.info(f'Загружено алиасов: {total_aliases}')
        
        return len(self.technologies)
    
    def generate_search_queries(self, 
                                use_aliases: bool = True,
                                max_queries: Optional[int] = None,
                                combine_with_keywords: Optional[List[str]] = None,
                                include_duplicate_aliases: bool = False) -> List[str]:
        """
        Генерация списка поисковых запросов.
        
        Args:
            use_aliases (bool): Использовать ли алиасы как отдельные запросы
            max_queries (int): Максимальное количество запросов
            combine_with_keywords (List[str]): Дополнительные ключевые слова для комбинации
                                              (например, ['разработчик', 'developer'])
            include_duplicate_aliases (bool): Включать ли алиасы, которые точно совпадают с названием
        
        Returns:
            List[str]: Список поисковых запросов
        """
        if not self.loaded:
            self.load_technologies()
        
        queries = []
        skipped_aliases_exact_duplicate = 0
        total_aliases_count = 0
        
        for tech in self.technologies:
            # Добавляем основное название
            queries.append(tech.name)
            
            # Добавляем алиасы (учитываем регистр - добавляем все, даже если отличаются только регистром)
            if use_aliases:
                # Проверяем, были ли алиасы загружены через prefetch_related
                # Если prefetch был выполнен, используем кэшированные данные
                if hasattr(tech, '_prefetched_objects_cache') and 'aliases' in tech._prefetched_objects_cache:
                    aliases_queryset = tech._prefetched_objects_cache['aliases']
                elif hasattr(tech, 'aliases'):
                    # Если prefetch не был выполнен, делаем запрос к БД
                    aliases_queryset = tech.aliases.all()
                else:
                    aliases_queryset = []
                
                for alias_obj in aliases_queryset:
                    alias = alias_obj.alias
                    total_aliases_count += 1
                    # Добавляем алиас если он не совпадает с названием, или если включен флаг include_duplicate_aliases
                    if alias != tech.name or include_duplicate_aliases:
                        queries.append(alias)
                    else:
                        skipped_aliases_exact_duplicate += 1
            
            # Комбинируем с ключевыми словами
            if combine_with_keywords:
                for keyword in combine_with_keywords:
                    queries.append(f"{tech.name} {keyword}")
        
        total_before_dedup = len(queries)
        
        # Убираем только точные дубликаты (с учетом регистра), сохраняя порядок
        seen = set()
        unique_queries = []
        skipped_exact_duplicates = 0
        for query in queries:
            if query not in seen:
                seen.add(query)
                unique_queries.append(query)
            else:
                skipped_exact_duplicates += 1
        
        # Ограничиваем количество если требуется
        if max_queries and len(unique_queries) > max_queries:
            unique_queries = unique_queries[:max_queries]
        
        logger.info(
            f'Сгенерировано {len(unique_queries)} уникальных поисковых запросов '
            f'(технологий: {len(self.technologies)}, всего алиасов: {total_aliases_count}, '
            f'до дедупликации: {total_before_dedup}, '
            f'пропущено алиасов точно совпадающих с названием: {skipped_aliases_exact_duplicate}, '
            f'пропущено точных дубликатов: {skipped_exact_duplicates})'
        )
        
        return unique_queries
    
    def generate_by_category(self, 
                           category: str,
                           use_aliases: bool = True,
                           max_per_category: Optional[int] = None) -> List[str]:
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
                                    max_per_category: Optional[int] = None) -> Dict[str, List[str]]:
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
        categories: List[str] = [
            str(choice[0]) for choice in TechnologyCategory.choices if choice[0]
        ]
        
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
            
            # Подсчитываем алиасы с учетом prefetch
            if hasattr(tech, '_prefetched_objects_cache') and 'aliases' in tech._prefetched_objects_cache:
                stats['total_aliases'] += len(tech._prefetched_objects_cache['aliases'])
            elif hasattr(tech, 'aliases'):
                stats['total_aliases'] += tech.aliases.count()
        
        return stats

