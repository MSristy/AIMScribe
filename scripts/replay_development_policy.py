"""Apply current deterministic source policy to recorded model decisions.

No API call, altered patient or gold checklist. Original requests/responses and
measured generation times are retained. This is development replay, never a
replacement for the later required fresh frozen comparison runs.
"""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.engine import grounded_selection, render_selection, output_errors, POLICY_VERSION
from src.clinical_context import normalized_context

folder = ROOT/'evaluation/baseline_development'
archive = ROOT/'evaluation/development_trials/qwen_before_policy_replay'
archive.mkdir(parents=True, exist_ok=True)
failed = False
for cid in ('C01', 'C02', 'C03', 'C04', 'C05', 'C06'):
    path = folder/(cid+'.json')
    record = json.loads(path.read_text(encoding='utf-8'))
    if record['status'] != 'completed':
        print(cid+': no successful model response to replay')
        failed = True
        continue
    if not (archive/path.name).exists():
        (archive/path.name).write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    decision = copy.deepcopy(record['raw_decisions'])
    old_fields = json.loads(record['messages'][1]['content'])['question_fields']
    for row in decision['decisions']:
        row['missing_fields'] = [old_fields.get(code, code) for code in row['missing_fields']]
    start = perf_counter()
    selected = grounded_selection(record['patient'], decision, record['retrieved'])
    output = render_selection(record['patient'], selected, record['retrieved'])
    errors = output_errors(output, record['retrieved'])
    record.update(raw_selection=selected, output=output, errors=errors,
                  status='invalid_output' if errors else 'completed', policy_version=POLICY_VERSION)
    record['postprocessing_context'] = normalized_context(record['patient'])
    record['postprocessing_replay'] = {'version': POLICY_VERSION, 'at': datetime.now(timezone.utc).isoformat(),
        'seconds': round(perf_counter()-start, 6),
        'note': 'No new model call. Original exact request/response and generation timing retained; deterministic policy uniformly reapplied.'}
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'case_id': cid, 'status': record['status'], 'model': record['model']['model'], 'errors': errors}))
    failed |= bool(errors)
sys.exit(1 if failed else 0)
