"""Assemble a clean, self-contained assessment snapshot and ZIP without credentials."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tomllib
from datetime import datetime, timezone
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / 'submission'
ZIP_PATH = ROOT / 'submission.zip'
DECK = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / 'Downloads/Clinical NLP Research Prototype.pptx'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def main():
    # Never overwrite, move or recursively delete a prior submission.
    if DESTINATION.resolve().parent != ROOT.resolve() or ZIP_PATH.resolve().parent != ROOT.resolve():
        raise RuntimeError('Submission destinations must stay directly inside this workspace')
    if DESTINATION.exists() or ZIP_PATH.exists():
        raise RuntimeError('Existing submission folder/ZIP preserved. Use a new versioned destination for a new release.')
    if not DECK.is_file():
        raise RuntimeError('The actual Canva-exported PowerPoint is required before packaging')
    frozen = json.loads((ROOT / 'evaluation/experiment/manifest.json').read_text(encoding='utf-8'))
    sys.path.insert(0, str(ROOT))
    from src.release_integrity import verify_frozen_snapshot
    verify_frozen_snapshot(ROOT)
    DESTINATION.mkdir()

    names = ['app.py', 'requirements.txt', '.streamlit/config.toml', '.streamlit/secrets.toml.example',
             'sources/source_manifest.json', 'sources/protocols/README.md',
             'data/index/bm25.json', 'data/extracted/assigned_pages.jsonl',
             'data/extracted/extraction_report.json',
             'docs/architecture.svg', 'docs/architecture.png', 'docs/architecture.mmd',
             'docs/paper-summary.txt', 'docs/project-documentation.md', 'docs/requirements-tracker.md',
             'docs/q1-card-guide.md', 'slides/canva-delivery.json', 'slides/q4-slide-content.json']
    for folder in ('src', 'tests', 'data/cards', 'evaluation/cases', 'evaluation/checklists', 'evaluation/experiment'):
        names.extend(p.relative_to(ROOT).as_posix() for p in (ROOT / folder).rglob('*')
                     if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
    for name in ('build_cards.py', 'build_index.py', 'validate_cards.py', 'validate_cases.py',
                 'extract_assigned_pages.py', 'render_assigned_pages.py', 'render_architecture.py',
                 'check_runtime.py', 'freeze_experiment.py', 'run_comparison.py',
                 'inspect_comparison.py', 'report_comparison.py', 'verify_submission.py'):
        names.append('scripts/' + name)
    for name in sorted(set(names)):
        source, target = ROOT / name, DESTINATION / name
        if not source.is_file() or not source.resolve().is_relative_to(ROOT.resolve()):
            raise RuntimeError('Invalid source file: ' + name)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    shutil.copy2(ROOT / 'README.md', DESTINATION / 'docs/prototype-readme.md')
    shutil.copy2(ROOT / 'docs/submission-readme-template.md', DESTINATION / 'README.md')
    shutil.copy2(ROOT / 'docs/ai-assistance-disclosure.md', DESTINATION / 'AI_ASSISTANCE_DISCLOSURE.md')
    shutil.copy2(DECK, DESTINATION / 'slides/Clinical_NLP_Research_Prototype.pptx')

    # Select the recorded model for offline report checks, using an EMPTY key only.
    # Remove this temporary configuration before hashing or packaging.
    temporary_config = DESTINATION / '.streamlit/secrets.toml'
    shutil.copy2(DESTINATION / '.streamlit/secrets.toml.example', temporary_config)
    checks = []
    log_dir = ROOT / '.local/submission-build'
    log_dir.mkdir(parents=True, exist_ok=True)
    commands = [
        ['-m', 'unittest', 'discover', '-s', 'tests', '-v'],
        ['scripts/validate_cards.py', '--input', 'data/cards/cards.jsonl'],
        ['scripts/validate_cases.py'],
        ['scripts/report_comparison.py'],
    ]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    try:
        for number, args in enumerate(commands, 1):
            process = subprocess.run([sys.executable, '-B', *args], cwd=DESTINATION, env=env,
                                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=240)
            output = process.stdout.decode('utf-8', errors='replace')
            (log_dir / ('check-' + str(number) + '.txt')).write_text(output, encoding='utf-8')
            tests = re.search(r'Ran (\d+) tests?', output)
            check = {'command': 'python ' + ' '.join(args), 'exit_code': process.returncode,
                     'passed': process.returncode == 0}
            if tests:
                check['test_count'] = int(tests[1])
            checks.append(check)
            print(json.dumps(check), flush=True)
            if process.returncode:
                raise RuntimeError('Package check failed; inspect private log ' + str(number))
    finally:
        if temporary_config.is_file():
            temporary_config.unlink()

    # Recheck exact source bytes after tests/report generation.
    verify_frozen_snapshot(DESTINATION)
    private_values = []
    with (ROOT / '.streamlit/secrets.toml').open('rb') as handle:
        config = tomllib.load(handle)
    for section in config.values():
        if isinstance(section, dict):
            private_values.extend(value.encode() for key, value in section.items()
                                  if any(word in key.lower() for word in ('key', 'token', 'password'))
                                  and isinstance(value, str) and len(value) >= 16)
    files = [p for p in DESTINATION.rglob('*') if p.is_file()]
    for p in files:
        blobs = [p.read_bytes()]
        if p.suffix == '.pptx':
            with ZipFile(p) as archive:
                blobs.extend(archive.read(n) for n in archive.namelist() if n.endswith(('.xml', '.rels')))
        if any(secret in blob for secret in private_values for blob in blobs):
            raise RuntimeError('Private credential detected in packaged file: ' + p.name)
    validation = {'created_at_utc': datetime.now(timezone.utc).isoformat(),
                  'software_and_structure_checks': checks,
                  'all_checks_passed': all(c['passed'] for c in checks),
                  'frozen_files_verified': len(frozen['sha256']),
                  'private_credential_values_checked_without_display': len(private_values),
                  'private_credentials_found': False,
                  'real_api_calls_during_packaging': 0,
                  'clinical_validation_claim': False,
                  'source_pdfs': 'Not bundled: supplied reading materials. Source manifest, assigned extraction and rebuild instructions included.',
                  'slide_source': 'Actual ten-slide Canva PowerPoint export with ten Bengali note parts'}
    write_json(DESTINATION / 'submission-validation.json', validation)
    manifest = {'format': 'Clinical NLP assessment submission v1',
                'created_at_utc': datetime.now(timezone.utc).isoformat(),
                'hash_algorithm': 'SHA256', 'zip_root': 'submission/',
                'sha256': {p.relative_to(DESTINATION).as_posix(): digest(p)
                           for p in sorted(DESTINATION.rglob('*')) if p.is_file()}}
    write_json(DESTINATION / 'submission-manifest.json', manifest)
    process = subprocess.run([sys.executable, '-B', 'scripts/verify_submission.py'],
                             cwd=DESTINATION, env=env, capture_output=True, text=True, timeout=60)
    print(process.stdout, flush=True)
    if process.returncode:
        raise RuntimeError('Final standard-library package verification failed')
    with ZipFile(ZIP_PATH, 'w', compression=ZIP_DEFLATED, compresslevel=6) as archive:
        for p in sorted(DESTINATION.rglob('*')):
            if p.is_file():
                archive.write(p, 'submission/' + p.relative_to(DESTINATION).as_posix())
    with ZipFile(ZIP_PATH) as archive:
        if archive.testzip() is not None:
            raise RuntimeError('ZIP integrity check failed')
        for name, expected in manifest['sha256'].items():
            if hashlib.sha256(archive.read('submission/' + name)).hexdigest() != expected:
                raise RuntimeError('ZIP content differs from folder: ' + name)
    print(json.dumps({'folder': str(DESTINATION), 'zip': str(ZIP_PATH),
                      'zip_bytes': ZIP_PATH.stat().st_size, 'zip_sha256': digest(ZIP_PATH),
                      'file_count': len(manifest['sha256']) + 1, 'zip_verified': True}), flush=True)


if __name__ == '__main__':
    main()
