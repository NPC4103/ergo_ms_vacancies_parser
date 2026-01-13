# Модуль парсинга вакансий (vacancies_parser)

## Описание

Модуль для парсинга вакансий с HeadHunter, Habr Career и SuperJob.

**Возможности:**
- Парсинг через API (официальные API площадок)
- Парсинг через HTML (парсинг веб-страниц с anti-bot защитой)
- Управление задачами: пауза, возобновление, остановка
- Отслеживание прогресса в реальном времени
- Нормализация данных в единый формат
- Экспорт результатов в CSV

## Архитектура

```
modules/vacancies_parser/
├── api/                      # Backend (Django)
│   ├── core/                 # Ядро модуля
│   │   ├── models.py         # ParsingTask, TaskItem
│   │   ├── normalized_models.py  # NormalizedVacancy
│   │   ├── parsers/          # Парсеры
│   │   │   ├── base.py       # BaseParser, ParserFactory
│   │   │   ├── api_parsers.py    # API парсеры
│   │   │   └── html_parsers.py   # HTML парсеры
│   │   ├── scheduler.py      # Планировщик задач
│   │   ├── tasks.py          # Celery задачи
│   │   └── views.py          # API ViewSets
│   ├── headhunter/           # HeadHunter-специфичный код
│   ├── habr_career/          # Habr Career-специфичный код
│   └── superjob/             # SuperJob-специфичный код
└── client/                   # Frontend (Vue.js)
    ├── components/           # Vue компоненты
    ├── composables/          # Vue composables
    └── js/                   # API и endpoints
```

## Источники и режимы парсинга

| Источник | API режим | HTML режим |
|----------|-----------|------------|
| HeadHunter | ✅ | ✅ |
| Habr Career | ✅ | ✅ |
| SuperJob | ✅ | ✅ |

## Использование

### Через UI

1. Перейдите в "Парсинг вакансий" → "Задачи парсинга"
2. Нажмите "Создать задачу"
3. Выберите источник и режим парсинга
4. Заполните конфигурацию (поисковый запрос, регион, количество страниц)
5. Нажмите "Создать"

### Управление задачей

- **Пауза** - приостанавливает выполнение, сохраняя прогресс
- **Возобновление** - продолжает с места остановки
- **Остановка** - полностью останавливает задачу

### Через API

```bash
# Создание задачи
POST /api/vacancies_parser/tasks/
{
    "source": "headhunter",
    "parsing_mode": "api",
    "name": "Python вакансии",
    "config": {
        "text": "Python developer",
        "area": "1",
        "pages": 10
    }
}

# Пауза задачи
POST /api/vacancies_parser/tasks/{id}/pause/

# Возобновление задачи
POST /api/vacancies_parser/tasks/{id}/resume/

# Остановка задачи
POST /api/vacancies_parser/tasks/{id}/stop/

# Прогресс задачи
GET /api/vacancies_parser/tasks/{id}/progress/

# Список вакансий
GET /api/vacancies_parser/vacancies/
```

## Конфигурация парсинга

### HeadHunter API
```json
{
    "text": "Python developer",
    "area": "1",
    "per_page": 100,
    "pages": 10
}
```

### HeadHunter HTML
```json
{
    "text": "Python developer",
    "area": "1",
    "items_per_page": 50,
    "max_pages": 10
}
```

## Celery задачи

Модуль использует Celery для асинхронной обработки:

- `vacancies_parser.tasks.create_parsing_task` - создание и discovery
- `vacancies_parser.tasks.coordinate_parsing_task` - координация worker'ов
- `vacancies_parser.tasks.parse_items_worker` - парсинг элементов
- `vacancies_parser.tasks.pause_task` - приостановка задачи
- `vacancies_parser.tasks.resume_task` - возобновление задачи
- `vacancies_parser.tasks.stop_task` - остановка задачи

## Статусы задачи

| Статус | Описание |
|--------|----------|
| created | Создана, ожидает запуска |
| running | Выполняется |
| paused | Приостановлена |
| stopped | Остановлена пользователем |
| completed | Успешно завершена |
| failed | Завершена с ошибкой |

## Консольные команды

```bash
# Очистка задач
ergoms api clear_tasks --all

# Очистка по статусу
ergoms api clear_tasks --status=failed

# Миграция старых вакансий
ergoms api migrate_old_vacancies
```
