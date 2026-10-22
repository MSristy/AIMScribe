"""Validate manual source review and compile results, without an AI judge/API."""
import hashlib
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_comparison import verify_manifest
from src.engine import output_errors

FOLDER = ROOT/'evaluation/experiment'
KEYS = ('expected_behaviour', 'citation_support', 'restrictions', 'missing_information')


def main():
    manifest = verify_manifest()
    review = json.loads((FOLDER/'manual_reviews.json').read_text(encoding='utf-8'))
    rows = review['rows']
    patients = {c['case_id']: c['patient'] for c in json.loads((FOLDER/'cases.json').read_text(encoding='utf-8'))['cases']}
    canonical = {c['card_id']: c for c in (json.loads(line) for line in (ROOT/'data/cards/cards.jsonl').read_text(encoding='utf-8').splitlines() if line.strip())}
    assert len(rows) == 12 and len({(r['case_id'], r['mode']) for r in rows}) == 12
    records, report_rows = {}, []
    for row in rows:
        path = FOLDER/'outputs'/(row['case_id']+'_'+row['mode']+'.json')
        assert hashlib.sha256(path.read_bytes()).hexdigest() == row['output_sha256'], 'Reviewed output changed'
        record = json.loads(path.read_text(encoding='utf-8'))
        assert record['patient'] == patients[row['case_id']], 'Frozen input mismatch'
        assert all(hit['card'] == canonical[hit['card']['card_id']] for hit in record['retrieved']), 'Noncanonical retrieved content'
        assert record['mode'] == row['mode'] and record['case_id'] == row['case_id']
        assert not record.get('postprocessing_replay'), 'Final comparison cannot use replay'
        assert record['model']['model'] == manifest['model']
        assert record['model']['settings'] == manifest['settings']
        assert not output_errors(record['output'], record['retrieved'])
        assert set(row['checks']) == set(KEYS)
        for key, check in row['checks'].items():
            assert check['verdict'] in ('pass', 'fail', 'not_applicable')
            assert check['reason'] and check['sources']
        records[(row['case_id'], row['mode'])] = record
        report_rows.append({**row, 'elapsed_seconds': record['timing_seconds']['total'],
                            'usage': record['raw_response'].get('provider_response', {}).get('usage', {}),
                            'selected_cards': [s['card_id'] for s in record['raw_selection']['selections']]})
    for cid in ('C01', 'C02', 'C03', 'C04', 'C05', 'C06'):
        b, i = records[(cid, 'baseline')], records[(cid, 'improved')]
        assert b['patient'] == i['patient'] and b['retrieved'] == i['retrieved']
        assert b['messages'][0] == i['messages'][0]
        context = json.loads(i['messages'][1]['content'])
        assert context.pop('applicability_preview')
        assert context == json.loads(b['messages'][1]['content'])
    counts = {}
    for mode in ('baseline', 'improved'):
        subset = [r for r in report_rows if r['mode'] == mode]
        by_check = {}
        for key in KEYS:
            verdicts = [r['checks'][key]['verdict'] for r in subset]
            passed, failed, na = (verdicts.count(value) for value in ('pass', 'fail', 'not_applicable'))
            by_check[key] = {'pass': passed, 'fail': failed, 'not_applicable': na,
                             'applicable_denominator': passed+failed, 'total_outputs': 6}
        counts[mode] = {'checks': by_check,
                        'all_four_pass_cases': sum(all(r['checks'][key]['verdict'] == 'pass' for key in KEYS) for r in subset),
                        'case_denominator': 6,
                        'passed_check_count': sum(r['checks'][key]['verdict'] == 'pass' for r in subset for key in KEYS),
                        'check_denominator': 24,
                        'mean_seconds': round(statistics.mean(r['elapsed_seconds'] for r in subset), 4),
                        'prompt_tokens': sum(r['usage'].get('prompt_tokens', 0) for r in subset),
                        'completion_tokens': sum(r['usage'].get('completion_tokens', 0) for r in subset)}
    gains, losses = [], []
    for cid in ('C01', 'C02', 'C03', 'C04', 'C05', 'C06'):
        pair = {r['mode']: r for r in rows if r['case_id'] == cid}
        for key in KEYS:
            b, i = (pair[m]['checks'][key]['verdict'] for m in ('baseline', 'improved'))
            if b == 'fail' and i == 'pass':
                gains.append(cid+':'+key)
            if b == 'pass' and i == 'fail':
                losses.append(cid+':'+key)
    result = {'scope': 'Six self-authored cases, source-reviewed once per mode; not clinical accuracy or RAG-versus-no-RAG evidence.',
              'reviewer': review['reviewer'], 'counts': counts, 'matched_gains': gains, 'matched_losses': losses,
              'isolation_verified': True, 'frozen_hashes_verified': True,
              'additional_prompt_tokens': counts['improved']['prompt_tokens']-counts['baseline']['prompt_tokens'],
              'additional_model_calls_per_case': 0, 'rows': report_rows}
    (FOLDER/'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    labels = {'pass': 'P', 'fail': 'F', 'not_applicable': 'NA'}
    lines = ['# Q2 comparison results', '', 'P = pass; F = fail; NA = not applicable. Source codes: D = Bangladesh dengue 5e (2025); H = Bangladesh hypertension 2e (2023); C = WHO cholera (2024); K = Bangladesh chikungunya (2017). Numbers are PDF positions, cover counted as page 1. Full reasons and per-check source IDs/pages: `manual_reviews.json`.', '',
             '| Case | Mode | Expected | Citations | Restrictions | Missing info | Seconds | Source PDF pages | Failure / limitation |',
             '|---|---|---|---|---|---|---:|---|---|']
    for row in report_rows:
        cells = [row['case_id'], row['mode']]
        for key in KEYS:
            check = row['checks'][key]
            cells.append(labels[check['verdict']])
        notes = {'C01': 'Generic ask wording remains.', 'C02': 'None observed.', 'C03': 'None observed.',
                 'C04': 'Raw admission error; shared guard withheld.', 'C06': 'None observed.'}
        note = notes.get(row['case_id'], 'Epidemiology clarification missing; '+('conditional tests added.' if row['mode'] == 'improved' else 'conditional tests omitted.'))
        cells += [str(row['elapsed_seconds']), row['checks']['expected_behaviour']['source_label'], note]
        lines.append('| '+' | '.join(cells)+' |')
    lines += ['', '## Counts and denominators', '', '| Check | Baseline P/F/NA | Improved P/F/NA |', '|---|---|---|']
    for key in KEYS:
        values = [counts[m]['checks'][key] for m in ('baseline', 'improved')]
        lines.append('| '+key+' | '+' | '.join(f"{v['pass']}/{v['fail']}/{v['not_applicable']} (of 6; applicable {v['applicable_denominator']})" for v in values)+' |')
    for mode in ('baseline', 'improved'):
        c = counts[mode]
        lines += ['', f"{mode.title()}: {c['passed_check_count']}/24 passed checks; {c['all_four_pass_cases']}/6 cases passed all four checks; mean elapsed {c['mean_seconds']} s; input tokens {c['prompt_tokens']}; completion tokens {c['completion_tokens']}."]
    lines += ['', f"Matched fail-to-pass gains: {len(gains)}; pass-to-fail losses: {len(losses)}. Additional improved input tokens: {result['additional_prompt_tokens']}; additional model calls per case: 0. Quota waits excluded from elapsed times. No unsupported clinical accuracy claim."]
    (FOLDER/'results-table.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps({key: result[key] for key in ('counts', 'matched_gains', 'matched_losses', 'additional_prompt_tokens')}, indent=2))


if __name__ == '__main__':
    main()
