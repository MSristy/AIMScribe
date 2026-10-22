"""Validate example or canonical JSON/JSONL cards; does not validate clinical truth.

Default: python scripts/validate_cards.py
Other cards: python scripts/validate_cards.py --input data/cards/cards.jsonl
Requires jsonschema. No LLM/API calls or changes to source files.
"""
import argparse
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


def leaves(condition):
    if condition['op'] in ('all', 'any'):
        for child in condition['conditions']:
            yield from leaves(child)
    else:
        yield condition


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', default='data/cards/examples', help='JSON/JSONL file or directory of JSON cards, relative to project root')
    args = parser.parse_args()
    path = Path(args.input)
    if not path.is_absolute():
        path = ROOT / path
    schema = json.loads((ROOT / 'data/cards/card.schema.json').read_text(encoding='utf-8-sig'))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    manifest = json.loads((ROOT / 'sources/source_manifest.json').read_text(encoding='utf-8-sig'))
    sources = {s['source_id']: s for s in manifest['sources']}
    paths = sorted(path.glob('*.json')) if path.is_dir() else [path]
    if not paths:
        raise ValueError(f'No card files found: {path}')
    cards, errors = [], []
    for file in paths:
        try:
            raw = file.read_text(encoding='utf-8-sig')
            entries = [json.loads(line) for line in raw.splitlines() if line.strip()] if file.suffix == '.jsonl' else [json.loads(raw)]
            cards.extend((str(file.relative_to(ROOT)) if file.is_relative_to(ROOT) else str(file), c) for c in entries)
        except (OSError, ValueError) as exc:
            errors.append(f'{file}: {exc}')
    seen = set()
    for origin, card in cards:
        failures = sorted(validator.iter_errors(card), key=lambda e: str(list(e.absolute_path)))
        if failures:
            errors.extend(f'{origin} / {list(e.absolute_path)}: {e.message}' for e in failures)
            continue
        cid = card['card_id']
        if cid in seen:
            errors.append(f'{cid}: duplicate card ID')
        seen.add(cid)
        evidence_ids = [e['evidence_id'] for e in card['evidence']]
        if len(evidence_ids) != len(set(evidence_ids)):
            errors.append(f'{cid}: duplicate evidence IDs')
        for ev in card['evidence']:
            source = sources.get(ev['source_id'])
            if source is None:
                errors.append(f'{cid}: unknown source {ev["source_id"]}')
                continue
            if ev['source_title'] != source['title'] or ev['source_version'] != source['version']:
                errors.append(f'{cid}/{ev["evidence_id"]}: source title/version mismatch')
            allowed = {n for a, b in source['assigned_pdf_page_ranges'] for n in range(a, b+1)}
            allowed.update(source.get('additional_pages_used', []))
            if ev['pdf_page'] not in allowed or ev['pdf_page'] > source['total_pdf_pages']:
                errors.append(f'{cid}/{ev["evidence_id"]}: unregistered/out-of-bounds source page')
        conditions = list(leaves(card['applicability']))
        for exclusion in card['exclusions']:
            conditions.extend(leaves(exclusion))
        fields = {c['field'] for c in conditions}
        if fields != set(card['required_patient_fields']):
            errors.append(f'{cid}: required_patient_fields must match all condition/exclusion fields')
        extra = [card['investigation_details']] if 'investigation_details' in card else []
        if card['clinical_category'] == 'investigations' and not extra:
            errors.append(f'{cid}: investigation purpose/timing/conditions are required')
        if 'monitoring_details' in card:
            extra.append(card['monitoring_details'])
        for item in conditions + card['medications'] + extra:
            if not set(item['evidence_ids']).issubset(set(evidence_ids)):
                errors.append(f'{cid}: broken evidence ID reference')
    if not cards:
        errors.append('No cards loaded')
    report = {'input': args.input, 'card_count': len(cards), 'passed': not errors,
              'errors': errors, 'scope': 'Schema, ID, registered-source/page and reference consistency only; not clinical or applicability execution validation.'}
    out = ROOT / 'data/cards/validation_report.json'
    out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
