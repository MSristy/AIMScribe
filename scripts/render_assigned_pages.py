"""Render assigned original PDF pages for visual review; does not perform OCR.

Run from project root: python scripts/render_assigned_pages.py
"""
import json
from pathlib import Path

import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / 'sources/source_manifest.json').read_text(encoding='utf-8'))
    output = ROOT / 'data/rendered'
    records = []
    for source in manifest['sources']:
        directory = output / source['source_id']
        directory.mkdir(parents=True, exist_ok=True)
        document = pdfium.PdfDocument(str(ROOT / 'sources' / source['file']))
        try:
            for start, end in source['assigned_pdf_page_ranges']:
                for number in range(start, end + 1):
                    if not 1 <= number <= len(document):
                        raise ValueError(f"Invalid page: {source['source_id']} / {number}")
                    path = directory / f'page-{number:03d}.png'
                    page = document[number - 1]
                    try:
                        bitmap = page.render(scale=2)
                        try:
                            image = bitmap.to_pil()
                            try:
                                image.save(path)
                            finally:
                                image.close()
                        finally:
                            bitmap.close()
                    finally:
                        page.close()
                    records.append({'source_id': source['source_id'], 'pdf_page': number,
                                    'image': path.relative_to(ROOT).as_posix()})
                    print(f"Rendered {source['source_id']} / PDF page {number}")
        finally:
            document.close()
    if len(records) != manifest['required_page_count']:
        raise ValueError('Rendered page count differs from required count')
    if len({(r['source_id'], r['pdf_page']) for r in records}) != len(records):
        raise ValueError('Duplicate source/page pairs')
    report = {'rendered_page_count': len(records), 'scale': 2,
              'note': 'Rendering preserves page appearance; does not establish visual review or clinical validation.',
              'pages': records}
    (output / 'render_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f"Completed: {len(records)} pages. Images and report: {output}")


if __name__ == '__main__':
    main()
