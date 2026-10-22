"""Check development cases/checklists and the single-field modified pair.

Run manually: python scripts/validate_cases.py
This does not freeze cases, grade model responses or establish clinical truth.
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def differences(a, b, path='patient'):
    if isinstance(a, dict) and isinstance(b, dict):
        result = []
        for key in sorted(set(a) | set(b)):
            if key not in a or key not in b:
                result.append(f'{path}.{key}')
            else:
                result.extend(differences(a[key], b[key], f'{path}.{key}'))
        return result
    return [] if type(a) is type(b) and a == b else [path]


def main():
    cases_doc = json.loads((ROOT / 'evaluation/cases/draft_cases.json').read_text(encoding='utf-8-sig'))
    checks_doc = json.loads((ROOT / 'evaluation/checklists/draft_checklists.json').read_text(encoding='utf-8-sig'))
    manifest = json.loads((ROOT / 'sources/source_manifest.json').read_text(encoding='utf-8-sig'))
    cards = [json.loads(line) for line in (ROOT / 'data/cards/cards.jsonl').read_text(encoding='utf-8-sig').splitlines() if line.strip()]
    cases = cases_doc['cases']
    checks = checks_doc['checklists']
    ids = [c['case_id'] for c in cases]
    check_ids = [c['case_id'] for c in checks]
    errors = []
    if len(cases) != 6 or len(set(ids)) != 6:
        errors.append('Expected six uniquely identified cases')
    if len(checks) != 6 or len(set(check_ids)) != 6 or set(ids) != set(check_ids):
        errors.append('Expected one checklist per case')
    expected_types = {'ordinary': 4, 'ambiguous_incomplete': 1, 'modified': 1}
    if dict(Counter(c['case_type'] for c in cases)) != expected_types:
        errors.append('Expected four ordinary, one ambiguous/incomplete and one modified case')
    if cases_doc.get('frozen') is not False or checks_doc.get('frozen') is not False:
        errors.append('These development files must remain explicitly unfrozen')
    allowed_case_keys = {'case_id', 'case_type', 'modified_from', 'patient'}
    forbidden = {'expected_answer','expected_behaviour','key_expected_behaviour','card_ids','sources','checklist','disease','diagnosis'}

    def inspect_patient(value, path):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in forbidden:
                    errors.append(f'{path}.{key}: forbidden answer/reference/diagnosis-label key')
                inspect_patient(child, f'{path}.{key}')
        elif isinstance(value, list):
            for index, child in enumerate(value):
                inspect_patient(child, f'{path}[{index}]')

    for case in cases:
        if set(case) != allowed_case_keys or not isinstance(case.get('patient'), dict):
            errors.append(f'{case.get("case_id")}: invalid case envelope')
        inspect_patient(case.get('patient'), case.get('case_id', '?'))
    known_cards = {c['card_id'] for c in cards}
    sources = {s['source_id']: s for s in manifest['sources']}
    dimensions = {'expected_behaviour','citation_support','restrictions','missing_information'}
    for check in checks:
        cid = check['case_id']
        for field in ('key_expected_behaviour','conditions','unsupported_action_to_avoid','coverage_status'):
            if not isinstance(check.get(field), str) or not check[field].strip():
                errors.append(f'{cid}: missing {field}')
        if set(check.get('checks', {})) != dimensions:
            errors.append(f'{cid}: expected four evaluation dimensions')
        if not check.get('card_ids') or not set(check['card_ids']).issubset(known_cards):
            errors.append(f'{cid}: missing or unknown mapped cards')
        if not check.get('sources'):
            errors.append(f'{cid}: source-linked expectation required')
        for reference in check.get('sources', []):
            source = sources.get(reference['source_id'])
            if source is None:
                errors.append(f'{cid}: unknown source')
                continue
            allowed = {n for start,end in source['assigned_pdf_page_ranges'] for n in range(start,end+1)}
            allowed.update(source.get('additional_pages_used', []))
            if not reference.get('pdf_pages') or not set(reference['pdf_pages']).issubset(allowed):
                errors.append(f'{cid}: unregistered source page')
    by_id = {c['case_id']: c for c in cases}
    modified_differences = []
    if 'C02' not in by_id or 'C06' not in by_id:
        errors.append('Expected C02/C06 modified pair')
    else:
        modified_differences = differences(by_id['C02']['patient'], by_id['C06']['patient'])
        if by_id['C06']['modified_from'] != 'C02' or modified_differences != ['patient.history.may_become_pregnant']:
            errors.append('Modified pair must change only pregnancy potential')
        if by_id['C02']['patient']['history']['may_become_pregnant'] is not False or by_id['C06']['patient']['history']['may_become_pregnant'] is not True:
            errors.append('Expected explicit false-to-true pregnancy-potential change')
    report = {'case_count': len(cases), 'checklist_count': len(checks), 'frozen': False,
              'passed': not errors, 'errors': errors, 'modified_patient_fields': modified_differences,
              'scope': 'Development file structure, references and input-difference checks only. No clinical grading, model run, semantic leakage proof or final freeze.'}
    (ROOT / 'evaluation/case_validation_report.json').write_text(json.dumps(report, indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
