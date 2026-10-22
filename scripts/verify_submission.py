"""Read-only package integrity checks. Standard library only; no network or credentials."""
import hashlib
import json
from pathlib import Path
import re
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def verify(root=ROOT):
    problems = []
    manifest = json.loads((root / 'submission-manifest.json').read_text(encoding='utf-8'))
    actual = {p.relative_to(root).as_posix(): p for p in root.rglob('*') if p.is_file()}
    expected = set(manifest['sha256']) | {'submission-manifest.json'}
    for name in sorted(expected - actual.keys()):
        problems.append('Missing: ' + name)
    for name in sorted(actual.keys() - expected):
        problems.append('Unexpected file: ' + name)
    for name, digest in manifest['sha256'].items():
        if name in actual and hashlib.sha256(actual[name].read_bytes()).hexdigest() != digest:
            problems.append('Package bytes changed: ' + name)
    experiment = root / 'evaluation/experiment'
    frozen = json.loads((experiment / 'manifest.json').read_text(encoding='utf-8'))
    for name, digest in frozen['sha256'].items():
        if not (root / name).is_file() or hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
            problems.append('Frozen experiment bytes changed: ' + name)
    reviews = json.loads((experiment / 'manual_reviews.json').read_text(encoding='utf-8'))['rows']
    for row in reviews:
        p = experiment / 'outputs' / (row['case_id'] + '_' + row['mode'] + '.json')
        if hashlib.sha256(p.read_bytes()).hexdigest() != row['output_sha256']:
            problems.append('Reviewed output changed: ' + p.name)
    cards = [json.loads(line) for line in (root / 'data/cards/cards.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    cases = json.loads((experiment / 'cases.json').read_text(encoding='utf-8'))['cases']
    checklist_data = json.loads((experiment / 'checklists.json').read_text(encoding='utf-8'))
    # Frozen checklist collection uses checklists, while case collection uses cases.
    checklists = checklist_data['checklists']
    outputs = list((experiment / 'outputs').glob('*.json'))
    pairs = {(row['case_id'], row['mode']) for row in reviews}
    if len(cards) != 32 or len(cases) != 6 or len(checklists) != 6 or len(outputs) != 12 or len(pairs) != 12:
        problems.append('Required dataset/case/checklist/output counts do not match')
    words = len((root / 'docs/paper-summary.txt').read_text(encoding='utf-8').split())
    if not 200 <= words <= 300:
        problems.append('Paper summary is outside 200–300 words')
    pptx = root / 'slides/AIMScribe_Research_Prototype.pptx'
    with ZipFile(pptx) as archive:
        slides = [n for n in archive.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml', n)]
        notes = [n for n in archive.namelist() if re.fullmatch(r'ppt/notesSlides/notesSlide\d+\.xml', n)]
        if len(slides) != 10 or len(notes) != 10:
            problems.append('Offline deck must have 10 slides and 10 note parts')
        if not any('আজ'.encode() in archive.read(n) for n in notes):
            problems.append('Bengali rehearsal notes are absent')
    patterns = [re.compile(rb'AIza[0-9A-Za-z_-]{30,}'), re.compile(rb'gsk_[0-9A-Za-z]{25,}'),
                re.compile(rb'gh[pousr]_[0-9A-Za-z]{25,}'), re.compile(rb'github_pat_[0-9A-Za-z_]{30,}')]
    for name, p in actual.items():
        if any(part in ('.git', '.venv', '__pycache__', '.local') for part in p.relative_to(root).parts) or name.endswith('secrets.toml'):
            problems.append('Private/generated path included: ' + name)
        blobs = [(name, p.read_bytes())]
        if p.suffix == '.pptx':
            with ZipFile(p) as archive:
                blobs = [(name + ':' + n, archive.read(n)) for n in archive.namelist() if n.endswith(('.xml', '.rels'))]
        for label, blob in blobs:
            if any(pattern.search(blob) for pattern in patterns):
                problems.append('Credential-like value found in: ' + label)
    return {'passed': not problems, 'errors': problems, 'file_count': len(actual),
            'frozen_file_count': len(frozen['sha256']), 'card_count': len(cards),
            'case_count': len(cases), 'checklist_count': len(checklists),
            'output_count': len(outputs), 'reviewed_output_count': len(reviews),
            'summary_words': words, 'slide_count': len(slides), 'note_count': len(notes),
            'scope': 'File integrity, required structure and targeted credential-pattern checks only; not clinical validation.'}


if __name__ == '__main__':
    result = verify()
    print(json.dumps(result, indent=2))
    sys.exit(0 if result['passed'] else 1)
