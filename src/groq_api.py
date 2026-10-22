"""Explicit Groq free-plan transport; no upgrades, retries or provider fallback."""
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from src.gemini import configuration

DEFAULT_MODEL = 'qwen/qwen3.8-27b'
FREE_MODELS = {DEFAULT_MODEL}
ENDPOINT = 'https://api.groq.com/openai/v1'
SETTINGS = {'temperature': 0, 'max_completion_tokens': 900, 'reasoning_effort': 'none'}


def credentials():
    config = configuration()
    model = config.get('model', {}).get('name', DEFAULT_MODEL)
    if model not in FREE_MODELS:
        raise RuntimeError('Groq model is outside the explicit free-plan allowlist; no fallback.')
    section = config.get('groq', {})
    if section.get('free_tier_confirmed') is not True:
        raise RuntimeError('Confirm Groq Free plan with no payment method, then set [groq] free_tier_confirmed = true. The app cannot inspect billing.')
    key = section.get('api_key', '').strip()
    if not key:
        raise RuntimeError('Groq key missing. Save it only in [groq] in .streamlit/secrets.toml, never in chat or Git.')
    return key, model


def request(path, key, payload=None):
    body = None if payload is None else json.dumps(payload).encode('utf-8')
    req = Request(ENDPOINT+path, data=body,
                  headers={'Content-Type': 'application/json', 'Authorization': 'Bearer '+key,
                           'User-Agent': 'Mozilla/5.0 (compatible; AIMScribe-Prototype/0.1)'})
    try:
        with urlopen(req, timeout=180) as response:
            return json.load(response)
    except HTTPError as exc:
        detail = exc.read(2500).decode('utf-8', errors='replace').replace(key, '[REDACTED]')
        if exc.code == 429:
            raise RuntimeError('Groq free-plan rate limit reached. Stopped: no retry, upgrade or paid fallback. Wait for quota reset. '+detail) from None
        raise RuntimeError(f'Groq HTTP {exc.code}: {detail}') from None
    except (URLError, TimeoutError, OSError):
        raise RuntimeError('Groq network request failed; no automatic retry or fallback.') from None


def status_base(model):
    return {'provider': 'groq', 'model': model, 'endpoint': ENDPOINT,
            'settings': SETTINGS, 'installed': False, 'generation_verified': False,
            'billing_note': 'Free plan/no payment confirmed by user, not independently inspected by app.'}


def model_status():
    model = configuration().get('model', {}).get('name', DEFAULT_MODEL)
    status = status_base(model)
    try:
        key, model = credentials()
    except RuntimeError as exc:
        status['setup_hint'] = str(exc)
        return status
    metadata = request('/models/'+model, key)
    status.update(installed=True, model_details=metadata,
                  setup_hint='Metadata available; generation permission/quota still require a successful real run.')
    return status


def chat(messages, schema):
    key, model = credentials()
    payload = {'model': model, 'messages': messages, **SETTINGS,
               'response_format': {'type': 'json_schema', 'json_schema': {
                   'name': 'card_selection', 'strict': True, 'schema': schema}}}
    raw = request('/chat/completions', key, payload)
    choices = raw.get('choices', [])
    if not choices:
        raise RuntimeError('Groq returned no choice; no answer invented.')
    choice = choices[0]
    if choice.get('finish_reason') != 'stop':
        raise RuntimeError('Groq generation incomplete: '+str(choice.get('finish_reason')))
    content = choice.get('message', {}).get('content')
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError('Groq returned no selection text.')
    status = status_base(model)
    status.update(installed=True, generation_verified=True, model_version=raw.get('model'),
                  system_fingerprint=raw.get('system_fingerprint'))
    usage = raw.get('usage', {})
    return {'message': {'role': 'assistant', 'content': content}, 'done': True,
            'done_reason': 'stop', 'prompt_eval_count': usage.get('prompt_tokens'),
            'eval_count': usage.get('completion_tokens'), 'provider_response': raw}, status
