"""Check explicit observed prerequisites only; no inferred diagnosis/dehydration class."""
import operator
from src.patient_facts import at_path
from src.clinical_context import normalized_context

PATHS = {'age_years': 'age_years', 'illness_day': 'illness_day', 'temperature_c': 'temperature_c',
         'pregnant': 'history.pregnant', 'may_become_pregnant': 'history.may_become_pregnant',
         'home_management_eligible_assessed': 'clinical_assessment.home_management_eligible',
         'dengue_excluded_by_clinician': 'clinical_assessment.dengue_excluded',
         'preexisting_liver_or_kidney_disease': 'history.preexisting_liver_or_kidney_disease',
         'severe_arthralgia_or_arthritis': 'symptoms.severe_arthralgia_or_arthritis',
         'joint_symptoms_explained_by_other_condition': 'history.alternative_condition_explaining_joint_symptoms',
         'residence_or_travel_to_epidemic_area': 'epidemiology.residence_or_travel_to_epidemic_area',
         'reported_transmission_within_15_days_before_onset': 'epidemiology.reported_local_transmission_within_15_days_before_onset',
         'cholera_outbreak_declared': 'epidemiology.cholera_outbreak_declared_in_area'}
PATHS.update({'bleeding_present': 'symptoms.bleeding', 'severe_abdominal_pain': 'symptoms.severe_abdominal_pain',
              'breathing_difficulty': 'symptoms.breathing_difficulty', 'altered_sensorium': 'symptoms.altered_sensorium',
              'haemodynamic_instability': 'examination.haemodynamic_instability',
              'oliguria_assessed_by_clinician': 'examination.oliguria_assessed_by_clinician',
              'chikungunya_high_risk': 'clinical_assessment.chikungunya_high_risk'})
OPS = {'eq': operator.eq, 'ne': operator.ne, 'gt': operator.gt, 'gte': operator.ge, 'lt': operator.lt, 'lte': operator.le}


def observed(node, patient, derived=None):
    """Return True/False/None using only registered exact fields."""
    derived = normalized_context(patient) if derived is None else derived
    if node['op'] in ('all', 'any'):
        values = [observed(child, patient, derived) for child in node['conditions']]
        if node['op'] == 'all':
            return False if False in values else True if all(v is True for v in values) else None
        return True if True in values else False if all(v is False for v in values) else None
    path = PATHS.get(node['field'])
    value = at_path(patient, path) if path else None
    if value is None:
        value = derived.get(node['field'], {}).get('value')
    if value is None:
        return None
    expected = node['value']
    if isinstance(expected, bool) and not isinstance(value, bool):
        return None
    if node['op'] in ('gt', 'gte', 'lt', 'lte') and (isinstance(value, bool) or not isinstance(value, (int, float))):
        return None
    try:
        return OPS[node['op']](value, expected)
    except TypeError:
        return None


def mandatory_unknowns(node, patient):
    # Unknown members of OR are not necessarily required; do not require them all.
    if node['op'] == 'any':
        return []
    if node['op'] == 'all':
        return [field for child in node['conditions'] for field in mandatory_unknowns(child, patient)]
    path = PATHS.get(node['field'])
    question_path = 'symptoms.severe_joint_pain' if node['field'] == 'severe_arthralgia_or_arthritis' else path
    derived = normalized_context(patient)
    return [question_path] if path and at_path(patient, path) is None and node['field'] not in derived else []


def constraint_review(card, patient):
    truth = observed(card['applicability'], patient)
    exclusions = [observed(exclusion, patient) for exclusion in card['exclusions']]
    if truth is False:
        return 'blocked', []
    if any(value is True for value in exclusions):
        return 'blocked', []
    # Active referral/escalation advice with OR-trigger criteria requires an
    # established trigger. Keep independent anticipatory warning education.
    if card['clinical_category'] == 'advice' and card['applicability']['op'] == 'all':
        triggers = [node for node in card['applicability']['conditions'] if node['op'] == 'any']
        if any(observed(node, patient) is None for node in triggers):
            return 'trigger_review', []
    unknown = mandatory_unknowns(card['applicability'], patient)
    if unknown:
        return 'needs_information', sorted(set(unknown))
    return ('eligible', []) if truth is True and all(value is False for value in exclusions) else ('model_review', [])
