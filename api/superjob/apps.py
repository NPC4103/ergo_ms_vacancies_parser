import os
from pathlib import Path

from django.apps import AppConfig


class VacanciesParserSuperjobConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.vacancies_parser.api.superjob'
    label = 'vacancies_parser_superjob'

    def ready(self):
        self._load_env()

    @staticmethod
    def _load_env():
        """Загрузка переменных из локального .env (без перезаписи уже заданных)."""
        env_path = Path(__file__).resolve().parent / '.env'
        if not env_path.is_file():
            return
        try:
            for line in env_path.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, _, val = line.partition('=')
                key, val = key.strip(), val.strip()
                if key and key not in os.environ:
                    os.environ[key] = val
        except OSError:
            pass