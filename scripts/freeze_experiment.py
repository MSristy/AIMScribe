"""Freeze the prespecified inputs/checklists/config after development, before calls."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.groq_api import DEFAULT_MODEL, SETTINGS
from src.engine import TOP_K, PROMPT_VERSION, POLICY_VERSION, IMPROVEMENT_VERSION

FOLDER = ROOT/'evaluation/experiment'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    if (FOLDER/'manifest.json').exists():
        raise SystemExit('Already frozen; do not overwrite an experiment manifest.')
    cases = json.loads((ROOT/'evaluation/cases/draft_cases.json').read_text(encoding='utf-8'))
    checklists = json.loads((ROOT/'evaluation/checklists/draft_checklists.json').read_text(encoding='utf-8'))
    timestamp = datetime.now(timezone.utc).isoformat()
    for obj in (cases, checklists):
        obj.update(frozen=True, frozen_at=timestamp, version='q2-comparison-v1')
    cases['purpose'] = 'Frozen fictional inputs; unchanged patient objects from development. No answers in runtime.'
    checklists['usage'] = 'Frozen evaluation-only expectations. Never import into engine, prompts or index.'
    for item in checklists['checklists']:
        # Historical engineering status is not an expected answer and is stale.
        item.pop('coverage_status', None)
    for filename, obj in (('cases.json', cases), ('checklists.json', checklists)):
        (FOLDER/filename).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
    files = [ROOT/'app.py', ROOT/'data/cards/cards.jsonl', ROOT/'data/index/bm25.json',
             FOLDER/'cases.json', FOLDER/'checklists.json', FOLDER/'plan.md',
             FOLDER/'source_review.json', ROOT/'scripts/run_comparison.py']
    files += sorted((ROOT/'src').glob('*.py'))
    manifest = {'experiment_id': 'q2-applicability-preview-v1', 'frozen_at': timestamp,
                'model': DEFAULT_MODEL, 'settings': SETTINGS, 'top_k': TOP_K,
                'prompt_version': PROMPT_VERSION, 'policy_version': POLICY_VERSION,
                'improvement_version': IMPROVEMENT_VERSION,
                'case_count': 6, 'outputs_expected': 12,
                'scope': 'Within-RAG, one pre-model preview change; not independent clinical validation.',
                'sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): sha(p) for p in files}}
    (FOLDER/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({'frozen_at': timestamp, 'files_hashed': len(files), 'case_count': 6}))


if __name__ == '__main__':
    main()
