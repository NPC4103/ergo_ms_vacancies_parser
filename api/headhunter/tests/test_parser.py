"""
Тестовый скрипт для запуска парсера HeadHunter без Celery
"""

import os
import django

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.config.patterns.development')
django.setup()

from modules.vacancies_parser.api.headhunter.scripts import parse_vacancies_by_text

if __name__ == '__main__':
    print('=== Тестовый запуск парсера HeadHunter ===')
    
    # Параметры парсинга
    text_list = ['Python']  # Поисковые запросы
    area = 113  # ID региона (113 = Россия)
    pages = 1  # Количество страниц
    delay = 1.0  # Задержка между запросами
    get_details = True  # Получать детальную информацию

    print('Параметры:')
    print(f'   Запросы: {text_list}')
    print(f'   Регион: {area}')
    print(f'   Страниц: {pages}')
    print(f'   Задержка: {delay} сек')
    print(f'   Детали: {"Да" if get_details else "Нет"}')
    print()
    
    try:
        # Запуск парсинга
        result = parse_vacancies_by_text(
            text_list=text_list,
            area=area,
            pages=pages,
            delay=delay,
            get_details=get_details
        )
        
        print('=== РЕЗУЛЬТАТЫ ПАРСИНГА ===')
        print(f'Всего обработано вакансий: {result["total_vacancies"]}')
        print(f'Новых вакансий добавлено: {result["new_vacancies"]}')
        print(f'Обновлено вакансий: {result["updated_vacancies"]}')
        print(f'Всего в базе данных: {result["total_in_db"]}')
        
    except Exception as e:
        print(f'Ошибка при выполнении парсинга:')
        print(f'   {type(e).__name__}: {e}')
        import traceback
        traceback.print_exc()

