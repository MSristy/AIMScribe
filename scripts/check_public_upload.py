"""Check exactly staged Git blobs before public upload; never print secret values."""
import json
from pathlib import Path
import re
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def main():
    names = [p.decode('utf-8') for p in git('diff', '--cached', '--name-only', '-z', '--diff-filter=ACM').split(b'\0') if p]
    secret_file = ROOT/'.streamlit/secrets.toml'
    private_values = []
    if secret_file.exists():
        settings = tomllib.loads(secret_file.read_text(encoding='utf-8-sig'))
        for section in settings.values():
            if isinstance(section, dict):
                private_values.extend(value.encode() for name, value in section.items()
                                      if ('key' in name.lower() or 'token' in name.lower() or 'password' in name.lower())
                                      and isinstance(value, str) and len(value) >= 16)
    patterns = [rb'AIza[0-9A-Za-z_-]{30,}', rb'gsk_[0-9A-Za-z]{25,}',
                rb'gh[pousr]_[0-9A-Za-z]{25,}', rb'github_pat_[0-9A-Za-z_]{30,}',
                rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']
    errors, total = [], 0
    manifest = json.loads((ROOT/'evaluation/experiment/manifest.json').read_text(encoding='utf-8'))
    import hashlib
    indexed = {p.decode('utf-8') for p in git('ls-files', '-z').split(b'\0') if p}
    try:
        sys.path.insert(0, str(ROOT))
        from src.release_integrity import verify_frozen_snapshot
        verify_frozen_snapshot(ROOT, read_bytes=lambda name: git('show', ':'+name))
    except (ValueError, AssertionError, subprocess.CalledProcessError) as exc:
        errors.append({'path': 'evaluation/experiment', 'issue': 'Original freeze / audited branding release verification failed: '+str(exc)})
    for name in names:
        if name == '.streamlit/secrets.toml' or name == '.env' or name.startswith(('.venv/', '.local/', 'tmp/')):
            errors.append({'path': name, 'issue': 'Private/local path staged'})
        content = git('show', ':'+name)
        total += len(content)
        if len(content) > 10*1024*1024:
            errors.append({'path': name, 'issue': 'Unexpected large staged file'})
        if any(value in content for value in private_values):
            errors.append({'path': name, 'issue': 'Known local credential value found; value not printed'})
        if any(re.search(pattern, content) for pattern in patterns):
            errors.append({'path': name, 'issue': 'Credential-like pattern found; value not printed'})
        # All frozen/staged release bytes were checked above, including exact
        # reverse reconstruction of the original post-experiment rename.
    print(json.dumps({'staged_file_count': len(names), 'staged_bytes': total,
                      'credential_values_checked_without_display': len(private_values),
                      'passed': bool(names) and not errors, 'errors': errors}, indent=2))
    sys.exit(0 if names and not errors else 1)


if __name__ == '__main__':
    main()
