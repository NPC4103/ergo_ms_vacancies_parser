"""
Генератор поисковых запросов на основе технологий (competence_core).

Используется HeadHunter, SuperJob и Habr Career для единого источника запросов.
"""

import logging
from typing import List, Dict, Optional

from modules.competence_core.api.skill_map.models import Technology, TechnologyCategory

logger = logging.getLogger('modules.vacancies_parser.technologies')


class TechnologySearchGenerator:
    """
    Генератор поисковых запросов для парсинга вакансий по технологиям.
    Использует БД competence_core (Technology, TechnologyCategory).
    """

    def __init__(self):
        self.technologies = []
        self.loaded = False

    def load_technologies(
        self,
        categories: Optional[List[str]] = None,
        min_popularity: int = 0,
        include_aliases: bool = True,
        limit: Optional[int] = None,
    ) -> int:
        query = Technology.objects.all()
        if categories:
            query = query.filter(category__in=categories)
        if min_popularity > 0:
            query = query.filter(popularity__gte=min_popularity)
        query = query.order_by('-popularity', '-relevance', 'name')
        if limit:
            query = query[:limit]
        query = query.prefetch_related('aliases')
        self.technologies = list(query)
        self.loaded = True
        total_aliases = sum(
            len(tech._prefetched_objects_cache.get('aliases', []))
            if hasattr(tech, '_prefetched_objects_cache')
            else tech.aliases.count()
            for tech in self.technologies
        )
        logger.info('Загружено %d технологий (алиасов: %d)', len(self.technologies), total_aliases)
        return len(self.technologies)

    def generate_search_queries(
        self,
        use_aliases: bool = True,
        max_queries: Optional[int] = None,
        combine_with_keywords: Optional[List[str]] = None,
        include_duplicate_aliases: bool = False,
    ) -> List[str]:
        if not self.loaded:
            self.load_technologies()
        queries = []
        for tech in self.technologies:
            queries.append(tech.name)
            if use_aliases:
                if hasattr(tech, '_prefetched_objects_cache') and 'aliases' in tech._prefetched_objects_cache:
                    aliases_queryset = tech._prefetched_objects_cache['aliases']
                elif hasattr(tech, 'aliases'):
                    aliases_queryset = tech.aliases.all()
                else:
                    aliases_queryset = []
                for alias_obj in aliases_queryset:
                    alias = alias_obj.alias
                    if alias != tech.name or include_duplicate_aliases:
                        queries.append(alias)
            if combine_with_keywords:
                for keyword in combine_with_keywords:
                    queries.append(f"{tech.name} {keyword}")
        seen = set()
        unique_queries = []
        for q in queries:
            if q not in seen:
                seen.add(q)
                unique_queries.append(q)
        if max_queries and len(unique_queries) > max_queries:
            unique_queries = unique_queries[:max_queries]
        logger.debug('Сгенерировано %d уникальных запросов', len(unique_queries))
        return unique_queries

    def generate_by_category(
        self,
        category: str,
        use_aliases: bool = True,
        max_per_category: Optional[int] = None,
    ) -> List[str]:
        self.load_technologies(categories=[category])
        return self.generate_search_queries(
            use_aliases=use_aliases,
            max_queries=max_per_category,
        )

    def generate_grouped_by_category(
        self,
        use_aliases: bool = True,
        max_per_category: Optional[int] = None,
    ) -> Dict[str, List[str]]:
        result = {}
        categories = [str(choice[0]) for choice in TechnologyCategory.choices if choice[0]]
        for category in categories:
            count = self.load_technologies(categories=[category])
            if count > 0:
                result[category] = self.generate_search_queries(
                    use_aliases=use_aliases,
                    max_queries=max_per_category,
                )
        return result

    def generate_priority_queries(
        self,
        top_n: int = 50,
        use_aliases: bool = False,
    ) -> List[str]:
        self.load_technologies(limit=top_n, include_aliases=use_aliases)
        return self.generate_search_queries(use_aliases=use_aliases)

    def get_statistics(self) -> Dict:
        if not self.loaded:
            return {'error': 'Технологии не загружены'}
        stats = {'total_technologies': len(self.technologies), 'by_category': {}, 'total_aliases': 0}
        for tech in self.technologies:
            stats['by_category'][tech.category] = stats['by_category'].get(tech.category, 0) + 1
            if hasattr(tech, '_prefetched_objects_cache') and 'aliases' in tech._prefetched_objects_cache:
                stats['total_aliases'] += len(tech._prefetched_objects_cache['aliases'])
            elif hasattr(tech, 'aliases'):
                stats['total_aliases'] += tech.aliases.count()
        return stats
