import os
import logging
import urllib.parse

import requests
from django.contrib.auth import get_user_model
from django.core import signing
from django.utils import timezone

from .models import OAuthToken

logger = logging.getLogger('modules.vacancies_parser.habr_career')

AUTH_URL = 'https://career.habr.com/integrations/oauth/authorize'
TOKEN_URL = 'https://career.habr.com/integrations/oauth/token'

STATE_SALT = 'habr-career-oauth'
STATE_MAX_AGE = 600  # 10 минут на авторизацию

User = get_user_model()


def _get_setting(name):
    return os.environ.get(name, '')


class HabrCareerOAuth:
    """Сервис для работы с OAuth 2.0 Хабр Карьеры"""

    def __init__(self):
        self.client_id = _get_setting('HABR_CAREER_CLIENT_ID')
        self.client_secret = _get_setting('HABR_CAREER_CLIENT_SECRET')
        self.redirect_uri = _get_setting('HABR_CAREER_REDIRECT_URI')

    def get_authorization_url(self, user):
        """
        Формирует URL авторизации с подписанным state-параметром.
        state содержит user_id, чтобы callback мог идентифицировать пользователя без JWT.
        """
        state = signing.dumps({'uid': user.pk}, salt=STATE_SALT)
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'state': state,
        }
        return f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

    @staticmethod
    def verify_state(state):
        """
        Проверяет и декодирует state-параметр.
        Возвращает объект User или None, если state невалиден/просрочен.
        """
        try:
            data = signing.loads(state, salt=STATE_SALT, max_age=STATE_MAX_AGE)
            return User.objects.get(pk=data['uid'])
        except (signing.BadSignature, signing.SignatureExpired, User.DoesNotExist, KeyError):
            return None

    def exchange_code(self, code):
        """
        Обменивает authorization code на access_token.
        Возвращает dict с ключами access_token, refresh_token, expires_in (если есть).
        """
        payload = {
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }

        try:
            response = requests.post(TOKEN_URL, data=payload, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Ошибка обмена code на token: {e}")
            return None

    def refresh_access_token(self, token_obj):
        """
        Обновляет access_token через refresh_token.
        Возвращает обновлённый OAuthToken или None.
        """
        if not token_obj.refresh_token:
            logger.warning("Нет refresh_token для обновления")
            return None

        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': token_obj.refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
        }

        try:
            response = requests.post(TOKEN_URL, data=payload, timeout=30)
            response.raise_for_status()
            data = response.json()

            token_obj.access_token = data['access_token']
            if data.get('refresh_token'):
                token_obj.refresh_token = data['refresh_token']
            token_obj.expires_at = _calc_expires_at(data.get('expires_in'))
            token_obj.save()

            logger.info(f"Токен пользователя {token_obj.user} обновлён")
            return token_obj
        except requests.RequestException as e:
            logger.error(f"Ошибка обновления токена: {e}")
            return None

    def save_token(self, user, token_data):
        """Сохраняет или обновляет токен Хабр Карьеры для пользователя"""
        defaults = {
            'access_token': token_data['access_token'],
            'refresh_token': token_data.get('refresh_token'),
            'expires_at': _calc_expires_at(token_data.get('expires_in')),
        }

        token_obj, created = OAuthToken.objects.update_or_create(
            user=user,
            defaults=defaults
        )

        action = 'создан' if created else 'обновлён'
        logger.info(f"OAuth токен Хабр Карьеры {action} для {user}")
        return token_obj

    def get_valid_token(self, user):
        """
        Получает валидный access_token Хабр Карьеры.
        Если истёк и есть refresh_token — обновляет автоматически.
        Возвращает строку access_token или None.
        """
        try:
            token_obj = OAuthToken.objects.get(user=user)
        except OAuthToken.DoesNotExist:
            return None

        if token_obj.is_expired:
            refreshed = self.refresh_access_token(token_obj)
            if not refreshed:
                return None
            token_obj = refreshed

        return token_obj.access_token

    @staticmethod
    def revoke_token(user):
        """Удаляет токен Хабр Карьеры пользователя"""
        deleted, _ = OAuthToken.objects.filter(user=user).delete()
        return deleted > 0

    @staticmethod
    def get_token_status(user):
        """Возвращает информацию о состоянии токена Хабр Карьеры"""
        try:
            token_obj = OAuthToken.objects.get(user=user)
            return {
                'connected': True,
                'expired': token_obj.is_expired,
                'has_refresh': bool(token_obj.refresh_token),
                'expires_at': token_obj.expires_at,
                'updated_at': token_obj.updated_at,
            }
        except OAuthToken.DoesNotExist:
            return {
                'connected': False,
                'expired': None,
                'has_refresh': False,
                'expires_at': None,
                'updated_at': None,
            }


def _calc_expires_at(expires_in):
    """Вычисляет datetime истечения по значению expires_in (секунды)"""
    if not expires_in:
        return None
    return timezone.now() + timezone.timedelta(seconds=int(expires_in))
