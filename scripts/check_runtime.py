"""Check configured model metadata, without generation or model downloads."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.model import model_status

try:
    report = model_status()
    report['metadata_ready'] = report['installed']
except RuntimeError as exc:
    report = {'metadata_ready': False, 'error': str(exc)}
path = ROOT/'data/index/runtime_status.json'
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
sys.exit(0 if report['metadata_ready'] else 1)
