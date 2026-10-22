"""Verify the original freeze and a separately audited post-experiment rename."""
import base64
import hashlib
import json
from pathlib import Path


def verify_frozen_snapshot(root, read_bytes=None):
    root = Path(root)
    read = read_bytes or (lambda name: (root / name).read_bytes())
    manifest = json.loads(read('evaluation/experiment/manifest.json'))
    amendment_path = root / 'evaluation/experiment/branding-amendment.json'
    amendment = json.loads(read('evaluation/experiment/branding-amendment.json')) if amendment_path.exists() else None
    changes = amendment['files'] if amendment else {}
    if amendment:
        assert amendment['original_manifest_sha256'] == hashlib.sha256(read('evaluation/experiment/manifest.json')).hexdigest()
        assert set(changes) == {'app.py', 'src/__init__.py', 'src/groq_api.py', 'scripts/run_comparison.py'}
    for name, original_hash in manifest['sha256'].items():
        current = read(name)
        current_hash = hashlib.sha256(current).hexdigest()
        if name not in changes:
            if current_hash != original_hash:
                raise ValueError('Frozen file changed: ' + name)
            continue
        change = changes[name]
        if change['original_sha256'] != original_hash or change['release_sha256'] != current_hash:
            raise ValueError('Branding release bytes changed: ' + name)
        restored = current
        for replacement in reversed(change['replacements']):
            before = base64.b64decode(replacement['before_base64'], validate=True)
            after = base64.b64decode(replacement['after_base64'], validate=True)
            count = replacement['count']
            if not after or restored.count(after) != count:
                raise ValueError('Branding substitution mismatch: ' + name)
            restored = restored.replace(after, before)
        if hashlib.sha256(restored).hexdigest() != original_hash:
            raise ValueError('Cannot reconstruct original frozen bytes: ' + name)
    return manifest
