"""Download the selected free local model through the local Ollama API."""
import json
from pathlib import Path
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.model import BASE_URL, MODEL

request = Request(BASE_URL+'/api/pull', data=json.dumps({'model': MODEL, 'stream': True}).encode(),
                  headers={'Content-Type': 'application/json'})
last = None
success = False
with urlopen(request, timeout=1800) as response:
    for line in response:
        item = json.loads(line)
        if 'error' in item:
            raise RuntimeError(item['error'])
        total = item.get('total')
        bucket = int(item.get('completed', 0)/total*10)*10 if total else None
        state = (item.get('status'), bucket)
        if state != last:
            print(json.dumps({'status': state[0], 'percent': bucket}), flush=True)
            last = state
        if item.get('status') == 'success':
            success = True
if not success:
    raise RuntimeError('Pull ended without a success confirmation.')
