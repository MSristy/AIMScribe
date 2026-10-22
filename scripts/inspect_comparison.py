"""Readable saved-output inspection for manual source review; never calls a model."""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--case', nargs='+')
args = parser.parse_args()
for path in sorted((ROOT/'evaluation/experiment/outputs').glob('*.json')):
    record = json.loads(path.read_text(encoding='utf-8'))
    if args.case and record['case_id'] not in args.case:
        continue
    print('\n'+path.stem+' '+record['status']+' '+str(record['timing_seconds']['total'])+' seconds')
    if record['errors']:
        print(record['errors'])
        continue
    for item in record['output']['recommendations']:
        print(json.dumps({'cards': item['card_ids'], 'category': item['category'], 'action': item['action'],
                          'reason': item['patient_reason'], 'medication': item['medication']}, ensure_ascii=False))
    print('QUESTIONS '+json.dumps(record['raw_selection']['questions'], ensure_ascii=False))
    print('LIMITATIONS '+json.dumps(record['output']['limitations'], ensure_ascii=False))
