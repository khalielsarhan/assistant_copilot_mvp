import json

import requests
from django.conf import settings


def generate(prompt: str, system: str = 'You are a concise CEO chief-of-staff assistant.', timeout: int = 60) -> str:
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
        r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json().get('message', {}).get('content', '').strip()
    except Exception as exc:
        return f'AI unavailable: {exc}'


def generate_json(prompt: str, system: str = 'Return only valid JSON.', timeout: int = 30) -> dict:
    response = generate(prompt, system=system, timeout=timeout)
    if response.startswith('AI unavailable'):
        return {}
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        start = response.find('{')
        end = response.rfind('}')
        if start == -1 or end == -1 or end <= start:
            return {}
        try:
            return json.loads(response[start:end + 1])
        except json.JSONDecodeError:
            return {}
