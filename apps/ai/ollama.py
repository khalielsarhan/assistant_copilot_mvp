import requests
from django.conf import settings


def generate(prompt: str, system: str = 'You are a concise CEO chief-of-staff assistant.') -> str:
    url = f'{settings.OLLAMA_BASE_URL.rstrip("/")}/api/chat'
    payload = {
        'model': settings.OLLAMA_MODEL,
        'stream': False,
        'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': prompt},
        ],
    }
    try:
        r = requests.post(url, json=payload, timeout=60)
        r.raise_for_status()
        return r.json().get('message', {}).get('content', '').strip()
    except Exception as exc:
        return f'AI unavailable: {exc}'
