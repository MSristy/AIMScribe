"""Summarize actual saved development runs; not clinical grading or final comparison."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
folder = ROOT/'evaluation/baseline_development'
rows = []
for case_id in ('C01', 'C02', 'C03', 'C04', 'C05', 'C06'):
    path = folder/(case_id+'.json')
    if not path.exists():
        rows.append({'case_id': case_id, 'status': 'missing'})
        continue
    record = json.loads(path.read_text(encoding='utf-8'))
    output = record.get('output') or {}
    selected = (record.get('raw_selection') or {}).get('selections', [])
    rows.append({'case_id': case_id, 'status': record['status'],
                 'selected_cards': [s['card_id'] for s in selected],
                 'categories': sorted({r['category'] for r in output.get('recommendations', [])}),
                 'questions': len(output.get('missing_information', [])),
                 'seconds': record.get('timing_seconds', {}).get('total'),
                 'retrieved_count': len(record.get('retrieved', [])),
                 'prompt_version': record.get('prompt_version'),
                 'model': record.get('model', {}),
                 'usage': record.get('raw_response', {}).get('provider_response', {}).get('usage', {}),
                 'errors': record.get('errors', [])})
report = {'scope': 'Development generation/format summary only. Not clinical grades, frozen cases or an improvement comparison.',
          'completed': sum(r['status'] == 'completed' for r in rows), 'expected': 6, 'cases': rows}
(folder/'summary.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
successful = [r for r in rows if r['status'] == 'completed']
if successful:
    latest = successful[-1]
    status = {**latest['model'], 'metadata_ready': True,
              'verified_by_saved_case': latest['case_id'],
              'verification_scope': 'A saved real generation succeeded; not clinical validation or a guarantee of future quota.'}
    (ROOT/'data/index/runtime_status.json').write_text(json.dumps(status, indent=2), encoding='utf-8')
print(json.dumps({'completed': report['completed'], 'expected': 6, 'summary': str(folder/'summary.json')}, indent=2))
