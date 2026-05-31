import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _api_url(method: str) -> str:
    return f'https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/{method}'


def send_message(chat_id: str, text: str) -> bool:
    if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN == 'replace-me':
        return False
    try:
        response = requests.post(_api_url('sendMessage'), json={'chat_id': chat_id, 'text': text}, timeout=10)
        response.raise_for_status()
        return True
    except requests.RequestException:
        logger.exception('Telegram sendMessage failed.')
        return False


def get_updates(offset: int | None = None, timeout: int = 30) -> list[dict]:
    if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN == 'replace-me':
        return []
    params = {'timeout': timeout}
    if offset is not None:
        params['offset'] = offset
    response = requests.get(_api_url('getUpdates'), params=params, timeout=timeout + 5)
    response.raise_for_status()
    return response.json().get('result', [])


def delete_webhook(drop_pending_updates: bool = False) -> bool:
    if not settings.TELEGRAM_BOT_TOKEN or settings.TELEGRAM_BOT_TOKEN == 'replace-me':
        return False
    response = requests.post(
        _api_url('deleteWebhook'),
        json={'drop_pending_updates': drop_pending_updates},
        timeout=10,
    )
    response.raise_for_status()
    return bool(response.json().get('ok'))
