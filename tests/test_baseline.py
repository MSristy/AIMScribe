"""Infrastructure checks, not clinical grades or model quality claims."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from src.engine import messages_for, output_errors, retrieve
from src.patient import prepare_patient, retrieval_query
from src.retrieval import build_index, CardIndex, CARDS
from src.model import selection_schema
from src.prompt_transport import unpack, pack
from jsonschema import Draft202012Validator


class BaselineTests(unittest.TestCase):
    def test_unknown_false_and_zero_preserved(self):
        original = {'chief_complaint': 'Fever', 'age_years': 0,
                    'history': {'pregnant': None, 'may_become_pregnant': False}}
        patient = prepare_patient(original)
        self.assertEqual(patient, original)
        patient['history']['pregnant'] = True
        self.assertIsNone(original['history']['pregnant'])
        query = retrieval_query(original)
        self.assertNotIn('pregnant', query)
        self.assertIn('0', query)

    def test_disease_name_not_required(self):
        patient, _, hits = retrieve({'chief_complaint': 'Acute watery diarrhoea and thirst'})
        self.assertNotIn('disease', patient)
        self.assertTrue(hits)
        self.assertEqual(hits[0]['card']['disease'], 'cholera')

    def test_bad_numbers_rejected(self):
        for value in [-1, 200, True, float('nan')]:
            with self.assertRaises(ValueError):
                prepare_patient({'chief_complaint': 'Fever', 'age_years': value})

    def test_corpus_change_requires_rebuild(self):
        with tempfile.TemporaryDirectory() as tmp:
            cards, index = Path(tmp)/'cards.jsonl', Path(tmp)/'index.json'
            cards.write_bytes(CARDS.read_bytes())
            report = build_index(cards, index)
            self.assertEqual(report['card_count'], 32)
            self.assertTrue(CardIndex(index, cards).search('fever'))
            cards.write_bytes(cards.read_bytes() + b'\n')
            with self.assertRaisesRegex(ValueError, 'Rebuild'):
                CardIndex(index, cards)

    def test_prompt_uses_patient_and_retrieved_cards_only(self):
        patient, _, hits = retrieve({'chief_complaint': 'Fever and rash', 'history': {'pregnant': None}})
        messages = messages_for(patient, hits)
        data = json.loads(messages[1]['content'])
        self.assertEqual(set(data), {'patient_facts', 'question_fields', 'question_slots', 'derived_context', 'cards', 'sources', 'evidence_note', 'missing_information_policy'})
        self.assertEqual(next(f['value'] for f in data['patient_facts'] if f['path'] == 'chief_complaint'), patient['chief_complaint'])
        decoded = data['cards']
        for compact, hit in zip(decoded, hits):
            for key in ('card_id', 'applicability', 'exclusions', 'required_patient_fields',
                        'recommended_action', 'medications', 'limitations'):
                self.assertEqual(compact[key], hit['card'][key])
            self.assertEqual([e['evidence_id'] for e in compact['evidence_refs']],
                             [e['evidence_id'] for e in hit['card']['evidence']])
            self.assertTrue(all(e['passage'] for e in hit['card']['evidence']))
        self.assertFalse(any(f['path'] == 'case_id' for f in data['patient_facts']))
        self.assertIn('exclusions', decoded[0])

    def test_transport_roundtrip_all_canonical_fields(self):
        cards = [json.loads(line) for line in CARDS.read_text(encoding='utf-8').splitlines() if line.strip()]
        self.assertEqual(unpack(pack(cards)), cards)

    def test_invented_citation_is_rejected(self):
        _, _, hits = retrieve({'chief_complaint': 'Fever'})
        output = {'patient_summary': 'Fever, duration unknown.', 'recommendations': [],
                  'missing_information': [{'question': 'How long?', 'why_needed': 'Timing matters.',
                                           'card_ids': [hits[0]['card']['card_id']]}], 'limitations': []}
        self.assertEqual(output_errors(output, hits), [])
        invalid = copy.deepcopy(output)
        invalid['missing_information'][0]['card_ids'] = ['INVENTED']
        self.assertTrue(output_errors(invalid, hits))
        invalid['missing_information'][0]['card_ids'] = []
        self.assertTrue(output_errors(invalid, hits))

    def test_model_selection_cannot_override_clinical_text(self):
        _, _, hits = retrieve({'chief_complaint': 'Fever'})
        schema = selection_schema([h['card']['card_id'] for h in hits])
        payload = {'selections': [{'card_id': hits[0]['card']['card_id'], 'patient_reason': 'Reported fever.'}],
                   'questions': [], 'limitations': []}
        validator = Draft202012Validator(schema)
        self.assertTrue(validator.is_valid(payload))
        payload['selections'][0]['dose'] = 'an invented dose'
        self.assertFalse(validator.is_valid(payload))
        del payload['selections'][0]['dose']
        payload['selections'][0]['card_id'] = 'INVENTED'
        self.assertFalse(validator.is_valid(payload))


if __name__ == '__main__':
    unittest.main()
