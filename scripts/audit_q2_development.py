"""Concrete Q2 regression audit of saved outputs, not final clinical grading."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.engine import output_errors
from src.patient_facts import fact_table, display_fact, missing_slots, questions_for_card

cases = json.loads((ROOT/'evaluation/cases/draft_cases.json').read_text(encoding='utf-8'))['cases']
checks = []
records = {}
def check(name, condition, detail):
    checks.append({'check': name, 'passed': bool(condition), 'detail': detail})

for case in cases:
    cid = case['case_id']
    path = ROOT/'evaluation/baseline_development'/f'{cid}.json'
    if not path.exists():
        check(cid+' generation', False, 'Output missing')
        continue
    record = json.loads(path.read_text(encoding='utf-8'))
    records[cid] = record
    check(cid+' generation', record['status'] == 'completed', record.get('errors', []))
    check(cid+' input preserved', record['patient'] == case['patient'], 'Original fictional patient; no answer/checklist fields added')
    if record['status'] != 'completed':
        continue
    check(cid+' output/citations', not output_errors(record['output'], record['retrieved']), 'Schema and retrieved card IDs')
    facts = {f['id']: f for f in fact_table(record['patient'])}
    expected_reasons = {'Relevant supplied findings: '+'; '.join(display_fact(facts[f]) for f in dict.fromkeys(s['fact_ids']))
                        for s in record['raw_selection']['selections']}
    check(cid+' grounded findings', all(r['patient_reason'] in expected_reasons for r in record['output']['recommendations']),
          'Displayed reasons are exact input-fact renderings, not model-authored patient claims')
    unknown = missing_slots(record['patient'])
    by_id = {h['card']['card_id']: h['card'] for h in record['retrieved']}
    questions = record['raw_selection']['questions']
    check(cid+' relevant unknown questions', all(q['field'] in unknown and q['field'] in questions_for_card(record['patient'], by_id[q['card_id']]) for q in questions),
          'No already supplied or unrelated question slots')
    investigations = [r for r in record['output']['recommendations'] if r['category'] == 'investigations']
    check(cid+' investigation details', all(r['purpose'] and r['timing'] for r in investigations),
          'Selected investigations have canonical source-linked purpose/timing; zero investigations does not count as complete coverage')

selected = lambda cid: {s['card_id'] for s in records.get(cid, {}).get('raw_selection', {}).get('selections', [])}
check('C01 day-appropriate investigation', 'DEN_TEST_EARLY' in selected('C01'), 'Dengue source days 1–5; case day 3')
check('C03 Plan B and independent reassessment', {'CHO_PLAN_B', 'CHO_PLAN_B_REASSESS'} <= selected('C03'), 'WHO assessment/Plan B/reassessment source policies')
check('C04 dengue restriction preserved', 'CHIK_PARACETAMOL_SOURCE' not in selected('C04') and 'CHIK_DENGUE_PRECAUTION' in selected('C04'), 'Dengue not excluded; do not use higher chikungunya adult ceiling')
check('C02/C06 prerequisite response', 'HTN_STEP2_FOLLOWUP' in selected('C02') and 'HTN_STEP2_FOLLOWUP' not in selected('C06') and 'HTN_PREGNANCY_POTENTIAL_ALTERNATIVE' in selected('C06'), 'Hypertension PDF 64; pregnancy potential is the only modified input')
for cid in ('C01', 'C02', 'C03', 'C04'):
    categories = {r['category'] for r in records.get(cid, {}).get('output', {}).get('recommendations', [])}
    check(cid+' ordinary-case category coverage', categories == {'probable_diagnosis', 'investigations', 'medication_guidance', 'advice'},
          'All four required output categories are present; presence does not prove clinical correctness')
check('C04 no unestablished active admission', 'CHIK_ADMISSION' not in selected('C04'), 'No documented positive source trigger; criteria remain for clinician review')
check('C04 documented negative exclusion not reasked', all(q.get('field') != 'clinical_assessment.dengue_excluded' for q in records.get('C04', {}).get('raw_selection', {}).get('questions', [])),
      'Explicit clinician statement already says dengue is not excluded')
report = {'scope': 'Targeted development regression checks; not a frozen comparison or independent clinical validation.',
          'passed': all(c['passed'] for c in checks), 'passed_count': sum(c['passed'] for c in checks),
          'check_count': len(checks), 'checks': checks}
destination = ROOT/'evaluation/baseline_development/requirement_audit.json'
destination.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k: report[k] for k in ('scope', 'passed', 'passed_count', 'check_count')}, indent=2))
for item in checks:
    if not item['passed']:
        print(json.dumps(item, ensure_ascii=False))
sys.exit(0 if report['passed'] else 1)
