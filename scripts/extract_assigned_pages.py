"""Extract assigned PDF positions without losing original page references.

Run from any directory: python scripts/extract_assigned_pages.py
Requires pypdf. Extracted text is a review aid, not a substitute for visual
inspection of tables, figures, footnotes or algorithms in original PDFs.
"""
import hashlib
import json
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / 'sources/source_manifest.json').read_text(encoding='utf-8'))
    output = ROOT / 'data/extracted'
    output.mkdir(parents=True, exist_ok=True)
    records = []
    counts = {}
    for source in manifest['sources']:
        path = ROOT / 'sources' / source['file']
        digest = hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()
        reader = PdfReader(path)
        pages = [n for start, end in source['assigned_pdf_page_ranges'] for n in range(start, end + 1)]
        if len(pages) != len(set(pages)):
            raise ValueError(f"Overlapping assigned ranges: {source['source_id']}")
        for n in pages:
            if not 1 <= n <= len(reader.pages):
                raise ValueError(f"Invalid PDF position: {source['source_id']} / {n}")
            records.append({
                'source_id': source['source_id'], 'source_title': source['title'],
                'version': source['version'], 'original_file': source['file'],
                'source_sha256': digest, 'pdf_page': n,
                'text': reader.pages[n-1].extract_text() or '',
                'visual_review_required': True,
            })
        counts[source['source_id']] = len(pages)
    if len(records) != manifest['required_page_count']:
        raise ValueError('Assigned page count differs from manifest')
    (output / 'assigned_pages.jsonl').write_text(
        ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in records), encoding='utf-8')
    summary = {'total_assigned_pages': len(records), 'per_source': counts,
               'empty_text_pages': [{'source_id': r['source_id'], 'pdf_page': r['pdf_page']}
                                    for r in records if not r['text'].strip()],
               'note': 'Extraction only; visual review and clinical validation are separate.'}
    (output / 'extraction_report.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
