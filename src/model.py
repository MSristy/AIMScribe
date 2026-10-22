"""Explicit configured-provider dispatch and structured output contract."""
import json
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

BASE_URL = 'http://127.0.0.1:11434'
MODEL = 'qwen2.5:0.5b'
SETTINGS = {'temperature': 0, 'seed': 42, 'num_ctx': 16384, 'num_predict': 2600}


def object_schema(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


TEXT = {'type': 'string', 'minLength': 1}
NULL_TEXT = {'type': ['string', 'null']}
IDS = {'type': 'array', 'items': TEXT, 'minItems': 1, 'uniqueItems': True}
RECOMMENDATION = object_schema({
    'category': {'enum': ['probable_diagnosis', 'investigations', 'medication_guidance', 'advice']},
    'action': TEXT, 'patient_reason': TEXT, 'purpose': NULL_TEXT, 'timing': NULL_TEXT,
    'medication': {'anyOf': [{'type': 'null'}, object_schema({
        'name': TEXT, 'dose': NULL_TEXT, 'route': NULL_TEXT, 'frequency': NULL_TEXT,
        'duration': NULL_TEXT, 'instructions': NULL_TEXT})]},
    'card_ids': IDS})
OUTPUT_SCHEMA = object_schema({
    'patient_summary': TEXT,
    'recommendations': {'type': 'array', 'items': RECOMMENDATION},
    'missing_information': {'type': 'array', 'items': object_schema({'question': TEXT, 'why_needed': TEXT, 'card_ids': IDS})},
    'limitations': {'type': 'array', 'items': TEXT}})


def selection_schema(card_ids, fact_ids=None, missing_fields=None):
    card_id = {'type': 'string', 'enum': list(card_ids)}
    if fact_ids is not None:
        slots_by_card = missing_fields if isinstance(missing_fields, dict) else {cid: list(missing_fields or []) for cid in card_ids}
        slots = sorted({slot for allowed in slots_by_card.values() for slot in allowed})
        decision = object_schema({'card_id': card_id,
            'decision': {'type': 'string', 'enum': ['recommend', 'needs_information', 'not_applicable']},
            'fact_ids': {'$ref': '#/$defs/facts'},
            'missing_fields': {'type': 'array', 'maxItems': max(1, len(slots)),
                               'items': {'type': 'string', 'enum': slots or ['NONE']}}})
        result = object_schema({'decisions': {'type': 'array', 'minItems': len(card_ids), 'maxItems': len(card_ids), 'items': decision}})
        result['$defs'] = {'facts': {'type': 'array', 'maxItems': 4,
                                    'items': {'type': 'string', 'pattern': '^F[0-9]+$'}}}
        return result
    return object_schema({
        'selections': {'type': 'array', 'items': object_schema({'card_id': card_id, 'patient_reason': TEXT})},
        'questions': {'type': 'array', 'items': object_schema({'card_id': card_id, 'question': TEXT, 'why_needed': TEXT})},
        'limitations': {'type': 'array', 'items': TEXT}})


def request_json(path, payload=None, timeout=15):
    body = None if payload is None else json.dumps(payload).encode('utf-8')
    request = Request(BASE_URL + path, data=body, headers={'Content-Type': 'application/json'})
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except HTTPError as exc:
        detail = exc.read(2000).decode('utf-8', errors='replace')
        raise RuntimeError(f'Local Ollama request failed ({path}, HTTP {exc.code}): {detail}') from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f'Local Ollama request failed ({path}): {exc}') from exc


def local_model_status():
    tags = request_json('/api/tags')
    version = request_json('/api/version')
    models = tags.get('models', [])
    selected = next((m for m in models if m.get('name') == MODEL), None)
    return {'runtime': version, 'model': MODEL, 'installed': selected is not None,
            'model_details': selected, 'endpoint': BASE_URL, 'settings': SETTINGS}


def configured_model_name():
    from src.gemini import provider, model_name
    return MODEL if provider() == 'ollama' else model_name()


def model_status():
    from src.gemini import provider, model_status as gemini_status
    if provider() == 'ollama':
        return local_model_status()
    if provider() == 'groq':
        from src.groq_api import model_status as groq_status
        return groq_status()
    if provider() != 'gemini':
        raise RuntimeError('Unknown model provider; no automatic fallback.')
    return gemini_status()


def chat(messages, schema=None, timeout=1800):
    from src.gemini import provider, chat as gemini_chat
    if provider() == 'gemini':
        return gemini_chat(messages, schema or OUTPUT_SCHEMA)
    if provider() == 'groq':
        from src.groq_api import chat as groq_chat
        return groq_chat(messages, schema or OUTPUT_SCHEMA)
    if provider() != 'ollama':
        raise RuntimeError('Unknown model provider; no automatic fallback.')
    status = local_model_status()
    if not status['installed']:
        raise RuntimeError(f'Local model is not installed. Run: ollama pull {MODEL}')
    result = request_json('/api/chat', {
        'model': MODEL, 'messages': messages, 'stream': False,
        'format': schema or OUTPUT_SCHEMA, 'options': SETTINGS, 'keep_alive': '5m'}, timeout=timeout)
    return result, status
