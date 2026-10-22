"""Development outputs only; does not import expected checklists or grade cases."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.engine import recommend


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', nargs='+', help='One or more draft case IDs; omit to run all six.')
    parser.add_argument('--patient', type=Path, help='Custom JSON patient object instead of draft cases.')
    parser.add_argument('--interval-seconds', type=float, default=65,
                        help='Minimum time between request starts (default 65 for free-plan token quota). No retries.')
    parser.add_argument('--initial-wait-seconds', type=float, default=0,
                        help='Explicit cooldown before the first call when a previous command just used quota.')
    args = parser.parse_args()
    if args.interval_seconds < 0 or args.initial_wait_seconds < 0:
        parser.error('Waits must be nonnegative.')
    if args.patient and args.case:
        parser.error('Choose --patient or --case, not both.')
    if args.patient:
        cases = [{'case_id': 'custom', 'patient': json.loads(args.patient.read_text(encoding='utf-8-sig'))}]
    else:
        cases = json.loads((ROOT/'evaluation/cases/draft_cases.json').read_text(encoding='utf-8'))['cases']
        if args.case:
            available = {c['case_id'] for c in cases}
            if set(args.case) - available:
                parser.error('Unknown draft case ID.')
            cases = [c for c in cases if c['case_id'] in args.case]
    destination = ROOT/'evaluation/baseline_development'
    destination.mkdir(parents=True, exist_ok=True)
    failed = False
    if args.initial_wait_seconds:
        print(f'Initial free-plan cooldown: {args.initial_wait_seconds:.1f}s; no API call yet.', flush=True)
        until = time.monotonic()+args.initial_wait_seconds
        while time.monotonic() < until:
            time.sleep(min(20, max(0, until-time.monotonic())))
    previous_start = None
    for case in cases:
        if previous_start is not None:
            remaining = args.interval_seconds-(time.monotonic()-previous_start)
            if remaining > 0:
                print(f'Free-plan pacing: waiting {remaining:.1f}s before next case (not a retry).', flush=True)
                while remaining > 0:
                    time.sleep(min(remaining, 20))
                    remaining = args.interval_seconds-(time.monotonic()-previous_start)
        previous_start = time.monotonic()
        print(f"Running {case['case_id']} with configured model...", flush=True)
        record = recommend(case['patient'])
        # The label is added AFTER inference, never to model input or retrieval.
        record['case_id'] = case['case_id']
        path = destination/f"{case['case_id']}.json"
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'case_id': case['case_id'], 'status': record['status'],
                          'seconds': record['timing_seconds']['total'], 'errors': record['errors'],
                          'saved': str(path)}), flush=True)
        if record['status'] != 'completed':
            failed = True
            print('Batch stopped after failed output; no retries or provider fallback.', flush=True)
            break
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
