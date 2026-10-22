"""Deterministic lexical BM25 card retrieval; no embedding/model dependency."""
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / 'data/cards/cards.jsonl'
INDEX = ROOT / 'data/index/bm25.json'
STOP = set('a an the and or of to in on at for is are be with as by this that from patient patients should may not no if then'.split())


def tokenize(text):
    return [x for x in re.findall(r'[a-z]+[a-z0-9]*|\d+(?:\.\d+)?', text.lower().replace('_', ' ')) if x not in STOP]


def search_text(card):
    parts = [card['disease'], card['title'], card['clinical_context'], card['recommended_action']]
    parts.extend(card['relevant_symptoms'])
    parts.extend(card['required_patient_fields'])
    parts.extend(m['name'] for m in card['medications'])
    parts.extend(e['passage'] for e in card['evidence'])
    return ' '.join(parts)


def build_index(cards_path=CARDS, output_path=INDEX):
    cards_path, output_path = Path(cards_path), Path(output_path)
    raw = cards_path.read_bytes()
    cards = [json.loads(line) for line in raw.decode('utf-8-sig').splitlines() if line.strip()]
    if not cards or len({c['card_id'] for c in cards}) != len(cards):
        raise ValueError('Canonical cards must be nonempty with unique IDs.')
    documents, frequencies = [], Counter()
    for card in cards:
        tf = Counter(tokenize(search_text(card)))
        frequencies.update(tf.keys())
        documents.append({'card': card, 'term_frequencies': dict(tf), 'length': sum(tf.values())})
    payload = {'index_version': 1, 'algorithm': 'BM25', 'k1': 1.5, 'b': 0.75,
               'corpus_sha256': hashlib.sha256(raw).hexdigest(), 'card_count': len(cards),
               'average_length': sum(d['length'] for d in documents)/len(documents),
               'document_frequencies': dict(frequencies), 'documents': documents,
               'corpus_scope': 'Canonical cards only; no cases, checklists or expected answers.'}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
    return {k: payload[k] for k in ('algorithm', 'card_count', 'corpus_sha256', 'corpus_scope')}


class CardIndex:
    def __init__(self, index_path=INDEX, cards_path=CARDS):
        self.data = json.loads(Path(index_path).read_text(encoding='utf-8'))
        actual = hashlib.sha256(Path(cards_path).read_bytes()).hexdigest()
        if self.data['corpus_sha256'] != actual:
            raise ValueError('Card dataset changed. Rebuild the index: python scripts/build_index.py')

    def search(self, query, top_k=12):
        if not 1 <= top_k <= len(self.data['documents']):
            raise ValueError('top_k must be between 1 and the card count.')
        terms = set(tokenize(query))
        n = self.data['card_count']
        average = self.data['average_length'] or 1
        k1, b = self.data['k1'], self.data['b']
        ranked = []
        for doc in self.data['documents']:
            score, matched = 0.0, []
            for term in sorted(terms):
                tf = doc['term_frequencies'].get(term, 0)
                if not tf:
                    continue
                df = self.data['document_frequencies'][term]
                idf = math.log(1 + (n - df + 0.5)/(df + 0.5))
                score += idf * tf * (k1 + 1)/(tf + k1*(1-b+b*doc['length']/average))
                matched.append(term)
            if score > 0:
                ranked.append({'card': doc['card'], 'score': round(score, 6), 'matched_terms': matched})
        ranked.sort(key=lambda item: (-item['score'], item['card']['card_id']))
        return ranked[:top_k]

    def recommendation_search(self, query, top_k=12):
        """Choose candidate protocols from diagnostic evidence, then cover categories.

        Candidate disease names come from the indexed cards, never case labels.
        Candidate-protocol membership is not a diagnosis or applicability decision.
        """
        ranked = self.search(query, len(self.data['documents']))
        diagnostic = [h for h in ranked if h['card']['clinical_category'] == 'probable_diagnosis']
        if not diagnostic:
            return ranked[:top_k]
        disease_scores = {}
        for hit in diagnostic:
            disease = hit['card']['disease']
            disease_scores[disease] = max(disease_scores.get(disease, 0), hit['score'])
        query_terms = set(tokenize(query))
        anchors = {}
        for doc in self.data['documents']:
            card = doc['card']
            if card['clinical_category'] == 'probable_diagnosis':
                anchors.setdefault(card['disease'], set()).update(tokenize(' '.join(card['relevant_symptoms'])))
        candidates = [d for d in sorted(disease_scores, key=lambda d: (-disease_scores[d], d))
                      if query_terms & anchors.get(d, set())][:2]
        if not candidates:
            return ranked[:top_k]
        by_id = {h['card']['card_id']: h for h in ranked}
        pools = {}
        for disease in candidates:
            pool = [by_id.get(doc['card']['card_id'], {'card': doc['card'], 'score': 0.0, 'matched_terms': []})
                    for doc in self.data['documents'] if doc['card']['disease'] == disease]
            pools[disease] = sorted(pool, key=lambda h: (-h['score'], h['card']['card_id']))
        chosen = []
        # Complete the primary protocol first; use remaining budget for differentials.
        for disease in candidates:
            for category in ('probable_diagnosis', 'investigations', 'medication_guidance', 'advice'):
                match = next((h for h in pools[disease] if h['card']['clinical_category'] == category), None)
                if match and len(chosen) < top_k and match['card']['card_id'] not in {h['card']['card_id'] for h in chosen}:
                    chosen.append(match)
            if disease == candidates[0]:
                for hit in pools[disease]:
                    if len(chosen) >= top_k:
                        break
                    if hit['card']['card_id'] not in {h['card']['card_id'] for h in chosen}:
                        chosen.append(hit)
        ids = {h['card']['card_id'] for h in chosen}
        # Fill remaining slots from primary protocol, then secondary, by BM25.
        for disease in candidates:
            for hit in pools[disease]:
                if len(chosen) >= top_k:
                    break
                if hit['card']['card_id'] not in ids:
                    chosen.append(hit)
                    ids.add(hit['card']['card_id'])
        return [{**h, 'retrieval_policy': 'diagnostic-protocol/category coverage + BM25',
                 'candidate_protocols': candidates} for h in chosen]
