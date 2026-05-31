import json
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


DEFAULT_OPTIONS = {
    'temperature': getattr(settings, 'OLLAMA_TEMPERATURE', 0.5),
    'top_p': 0.8,
    'num_ctx': 4096,
}


def generate(
    prompt: str,
    system: str = 'You are a concise CEO chief-of-staff assistant. Use only provided facts. If data is missing, say what is missing.',
    timeout: int = 60,
    response_format: str | None = None,
    options: dict | None = None,
) -> str:
    url = f'{settings.OLLAMA_BASE_URL.rstrip("/")}/api/chat'
    payload = {
        'model': settings.OLLAMA_MODEL,
        'stream': False,
        'options': {**DEFAULT_OPTIONS, **(options or {})},
        'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': prompt},
        ],
    }
    if response_format:
        payload['format'] = response_format
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json().get('message', {}).get('content', '').strip()
    except Exception as exc:
        logger.exception('Ollama request failed.')
        return f'AI unavailable: {exc}'


def generate_json(prompt: str, system: str = 'Return only valid JSON. Do not include markdown, comments, or extra text.', timeout: int = 30) -> dict:
    response = generate(
        prompt,
        system=system,
        timeout=timeout,
        response_format='json',
        options={'temperature': 0.0},
    )
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
