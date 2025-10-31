"""
Тестовый скрипт для парсинга вакансий по технологиям.

Демонстрирует работу автоматической генерации поисковых запросов
на основе технологий из базы данных.
"""

import os
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.config.patterns.development')
django.setup()

from modules.vacancies_parser.api.headhunter.utils import TechnologySearchGenerator

if __name__ == '__main__':
    print('=== Тест: Генерация поисковых запросов по технологиям ===')
    
    # Создаем генератор
    generator = TechnologySearchGenerator()
    
    print('\n--- Тест 1: Топ-10 технологий (без алиасов) ---')

    generator.load_technologies(limit=10, include_aliases=False)
    queries = generator.generate_search_queries(use_aliases=False)

    print(f'Сгенерировано {len(queries)} запросов:')
    for i, query in enumerate(queries, 1):
        print(f'   {i}. {query}')
    
    print('\n--- Тест 2: Топ-10 технологий (с алиасами) ---')

    generator.load_technologies(limit=10, include_aliases=True)
    queries = generator.generate_search_queries(use_aliases=True)

    print(f'Сгенерировано {len(queries)} запросов:')
    for i, query in enumerate(queries, 1):
        print(f'   {i}. {query}')
    
    print('\n--- Тест 3: Категория LANG (языки программирования) ---')

    queries = generator.generate_by_category('LANG', use_aliases=True)

    print(f'Сгенерировано {len(queries)} запросов:')
    for i, query in enumerate(queries, 1):
        print(f'   {i}. {query}')
    
    print('\n--- Тест 4: Категория FRAMEWORK (фреймворки) ---')

    queries = generator.generate_by_category('FRAMEWORK', use_aliases=False)

    print(f'Сгенерировано {len(queries)} запросов (первые 15):')
    for i, query in enumerate(queries[:15], 1):
        print(f'   {i}. {query}')
    
    print('\n--- Тест 5: Статистика по всем технологиям ---')

    generator.load_technologies(include_aliases=True)
    stats = generator.get_statistics()

    print('Статистика:')
    print(f'   Всего технологий: {stats["total_technologies"]}')
    print(f'   Всего алиасов: {stats["total_aliases"]}')
    print('   По категориям:')
    for category, count in stats['by_category'].items():
        print(f'     - {category}: {count}')
    
    print('\n--- Тест 6: Топ-20 приоритетных запросов ---')

    queries = generator.generate_priority_queries(top_n=20, use_aliases=False)

    print(f'Сгенерировано {len(queries)} запросов:')
    for i, query in enumerate(queries, 1):
        print(f'   {i}. {query}')

    print('\n=== Все тесты пройдены успешно! ===')

    print('\nДля запуска реального парсинга используйте:')
    print('   python src/manage.py parse_hh_by_technologies --top 10 --wait')
    print('   или')
    print('   python src/manage.py parse_hh_by_technologies --category LANG --wait')
    print()

