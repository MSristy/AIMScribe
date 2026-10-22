"""Traceable aliases/arithmetic for documented hypertension follow-up facts.

No case IDs, diagnosis training, guessed laboratory thresholds or dehydration
classification. Unresolvable facts remain absent/unknown.
"""
import re
from src.patient_facts import at_path


def normalized_context(patient):
    context = {}
    def put(field, value, paths, method):
        if value is not None:
            context[field] = {'value': value, 'source_paths': paths, 'method': method}
    exclusion = at_path(patient, 'clinical_assessment.dengue_excluded')
    narrative = str(patient.get('additional_context') or '').lower()
    if exclusion is None and 'dengue has not been excluded by the clinician' in narrative:
        put('dengue_excluded_by_clinician', False, ['additional_context'],
            'Exact documented negative clinician statement; not an inference from NS1 or symptoms')
    prior = at_path(patient, 'history.elevated_bp_confirmed_on_prior_visits')
    put('previous_bp_confirmation_documented', prior if isinstance(prior, bool) else None,
        ['history.elevated_bp_confirmed_on_prior_visits'], 'Direct documented-history alias')
    regular = at_path(patient, 'history.medicines_taken_regularly_and_correctly')
    put('medicines_taken_regularly_correctly', regular if isinstance(regular, bool) else None,
        ['history.medicines_taken_regularly_and_correctly'], 'Direct adherence alias')
    medicines = at_path(patient, 'history.current_medicines')
    if isinstance(medicines, list):
        named = [m for m in medicines if isinstance(m, dict)]
        known = [m for m in named if str(m.get('name', '')).strip().lower() in ('amlodipine', 'losartan')]
        active = True if known else False if not medicines else None
        put('on_antihypertensive_treatment', active, ['history.current_medicines'], 'Named medicine from the supplied protocol; empty assessed list means none')
        if len(medicines) == 1 and len(named) == 1:
            med = named[0]
            name = str(med.get('name', '')).strip().lower()
            dose = str(med.get('dose', '')).strip().lower().replace(' ', '')
            frequency = str(med.get('frequency', '')).strip().lower()
            if name == 'amlodipine' and dose == '5mg' and frequency == 'once daily':
                put('current_htn_step', 'amlodipine_5mg_once_daily', ['history.current_medicines.0'], 'Exact documented name/dose/frequency; no regimen guessed')
                months = med.get('months_on_regimen')
                put('months_since_step1_started', months if isinstance(months, (int, float)) and not isinstance(months, bool) else None,
                    ['history.current_medicines.0.months_on_regimen'], 'Direct elapsed-time alias; no time conversion')
    readings = at_path(patient, 'examination.office_bp_readings_mmhg')
    if prior is True or isinstance(readings, list) and readings:
        put('hypertension_under_assessment', True,
            ['history.elevated_bp_confirmed_on_prior_visits', 'examination.office_bp_readings_mmhg'], 'Documented hypertension history or BP-assessment readings, not a new confirmed diagnosis')
    target = at_path(patient, 'examination.clinician_recorded_bp_target')
    numbers = re.search(r'(\d{2,3})\s*/\s*(\d{2,3})', target) if isinstance(target, str) and ('below' in target.lower() or '<' in target) else None
    if numbers and isinstance(readings, list) and readings:
        sbp, dbp = map(int, numbers.groups())
        valid = all(isinstance(r, dict) and all(isinstance(r.get(k), (int, float)) and not isinstance(r.get(k), bool) for k in ('systolic', 'diastolic')) for r in readings)
        if valid:
            below = [r['systolic'] < sbp and r['diastolic'] < dbp for r in readings]
            # Do not invent an averaging rule for mixed readings.
            met = True if all(below) else False if not any(below) else None
            put('bp_target_met', met, ['examination.office_bp_readings_mmhg', 'examination.clinician_recorded_bp_target'],
                'All supplied readings consistently below or not below the clinician-recorded target; mixed readings remain unknown')
    tests = at_path(patient, 'available_tests')
    if isinstance(tests, list):
        for name in ('creatinine', 'potassium'):
            matches = [t for t in tests if isinstance(t, dict) and name in str(t.get('name', '')).lower()]
            checked = True if any(t.get('reviewed_by_clinician') is True for t in matches) else False if not tests else None
            put('pre_losartan_'+name+'_checked', checked, ['available_tests'],
                'Named test explicitly reviewed by clinician; does not establish acceptable numeric values')
    return context
