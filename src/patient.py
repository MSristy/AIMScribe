"""Input preservation and lexical query construction, not clinical inference."""
import copy
import json
import math
from src.retrieval_context import positive_text


def prepare_patient(value):
    if not isinstance(value, dict):
        raise ValueError('Patient input must be a JSON object.')
    if len(json.dumps(value, ensure_ascii=False)) > 40000:
        raise ValueError('Patient input is too long; keep it under 40,000 characters.')
    patient = copy.deepcopy(value)
    complaint = patient.get('chief_complaint')
    if not isinstance(complaint, str) or not complaint.strip():
        raise ValueError('Enter a chief complaint or symptoms; a disease name is not required.')
    for key, maximum in [('age_years', 130), ('weight_kg', 500), ('illness_day', 36500), ('temperature_c', 50)]:
        item = patient.get(key)
        if item is None:
            continue
        if isinstance(item, bool) or not isinstance(item, (int, float)) or not math.isfinite(item):
            raise ValueError(f'{key} must be a finite number or null.')
        if not 0 <= item <= maximum:
            raise ValueError(f'{key} is outside the supported input range.')
    return patient


def retrieval_query(patient):
    """Use available patient facts; don't add disease labels or expected answers.

    False/null structured findings are not positive search terms. They remain in
    the full patient object supplied to the model. Explicit absent/unknown prose
    clauses are omitted from the search copy only by a limited English heuristic.
    """
    pieces = []

    def walk(value, label=''):
        if value is None or value is False:
            return
        if value is True:
            pieces.append(label.replace('_', ' '))
        elif isinstance(value, str):
            positive = positive_text(value)
            if positive:
                pieces.append(label.replace('_', ' ') + ' ' + positive)
        elif isinstance(value, (int, float)):
            pieces.append(label.replace('_', ' ') + ' ' + str(value))
        elif isinstance(value, dict):
            for key, item in value.items():
                walk(item, key)
        elif isinstance(value, list):
            for item in value:
                walk(item, label)

    walk(patient)
    return ' '.join(pieces)
