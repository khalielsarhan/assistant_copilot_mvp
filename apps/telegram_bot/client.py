import requests
from django.conf import settings


def send_message(chat_id: str, text: str) -> None:
    if not settings.TELEGRAM_BOT_TOKEN:
        return
    url = f'https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage'
    requests.post(url, json={'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}, timeout=10)
