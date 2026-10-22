"""Fresh paired generations from frozen inputs. Does not read expected checklists."""
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.engine import recommend, retrieve, messages_for
from src.model import configured_model_name
from src.groq_api import SETTINGS

FOLDER = ROOT/'evaluation/experiment'


def verify_manifest():
    from src.release_integrity import verify_frozen_snapshot
    manifest = verify_frozen_snapshot(ROOT)
    if configured_model_name() != manifest['model'] or SETTINGS != manifest['settings']:
        raise ValueError('Model/settings changed after freeze.')
    return manifest


def main():
    manifest = verify_manifest()
    if (FOLDER/'branding-amendment.json').exists():
        raise SystemExit('This post-experiment branding release preserves the original saved comparison. Create a separately versioned plan/freeze for new batch calls; do not attribute renamed runtime bytes to the original freeze.')
    cases = json.loads((FOLDER/'cases.json').read_text(encoding='utf-8'))['cases']
    destination = FOLDER/'outputs'
    destination.mkdir(exist_ok=True)
    if list(destination.glob('*.json')):
        raise SystemExit('Output directory is not empty; refuse overwrite/cherry-picked rerun.')
    previous_start = None
    for index, case in enumerate(cases):
        modes = ('baseline', 'improved') if index % 2 == 0 else ('improved', 'baseline')
        pair = []
        for mode in modes:
            if previous_start is not None:
                remaining = 65-(time.monotonic()-previous_start)
                while remaining > 0:
                    time.sleep(min(15, remaining))
                    remaining = 65-(time.monotonic()-previous_start)
            verify_manifest()
            previous_start = time.monotonic()
            print('Generating '+case['case_id']+' '+mode, flush=True)
            record = recommend(case['patient'], mode=mode)
            record.update(case_id=case['case_id'], experiment_id=manifest['experiment_id'],
                          freeze_manifest_sha256=hashlib.sha256((FOLDER/'manifest.json').read_bytes()).hexdigest())
            path = destination/(case['case_id']+'_'+mode+'.json')
            path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps({'case_id': case['case_id'], 'mode': mode, 'status': record['status'],
                              'seconds': record['timing_seconds']['total'], 'errors': record['errors']}), flush=True)
            pair.append(record)
            if record['status'] != 'completed':
                raise SystemExit('Stopped on failed generation; original failure preserved, no automatic retry/fallback.')
        # Verify isolation using exact saved requests, not just configuration.
        first, second = pair
        assert first['patient'] == second['patient']
        assert first['retrieved'] == second['retrieved']
        assert first['model']['model'] == second['model']['model']
        assert first['model']['settings'] == second['model']['settings']
        b = next(r for r in pair if r['mode'] == 'baseline')['messages']
        i = next(r for r in pair if r['mode'] == 'improved')['messages']
        assert b[0] == i[0]
        context = json.loads(i[1]['content'])
        assert context.pop('applicability_preview')
        assert context == json.loads(b[1]['content'])
        print('Pair isolation verified: '+case['case_id'], flush=True)
    verify_manifest()
    print('Completed 12 fresh outputs; frozen hashes and six pair-isolation checks verified.', flush=True)


if __name__ == '__main__':
    main()
