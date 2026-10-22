"""Regression checks for retrieval abstention and explicit English negative lists."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from src.engine import retrieve, recommend
from src.patient import retrieval_query
from src.retrieval import CardIndex
from src.retrieval_context import positive_text

ROOT = Path(__file__).resolve().parents[1]
URINARY = {
    'chief_complaint': 'Burning pain during urination for 2 days, frequent urination, and mild lower abdominal discomfort. No fever, rash, joint pain, diarrhoea, vomiting, or back pain. Pregnancy status and allergies are unknown. The patient reports taking no current medicines. No physical examination or urine tests have been performed.',
    'age_years': 30, 'sex': 'female', 'illness_day': 2,
    'history': {'current_medicines': [], 'known_allergies': None, 'pregnant': None},
}


class RetrievalScopeTests(unittest.TestCase):
    def test_negative_list_does_not_nominate_protocol(self):
        original = copy.deepcopy(URINARY)
        patient, query, hits = retrieve(URINARY)
        self.assertEqual(hits, [])
        for word in ('fever', 'rash', 'joint pain', 'diarrhoea', 'vomiting'):
            self.assertNotIn(word, query.lower())
        self.assertEqual(patient, original)
        self.assertEqual(URINARY, original)

    def test_abstention_skips_model_in_both_modes(self):
        with patch('src.engine.chat') as model:
            for mode in ('baseline', 'improved'):
                record = recommend(URINARY, mode=mode)
                self.assertEqual(record['status'], 'no_evidence')
                self.assertEqual(record['retrieved'], [])
                self.assertEqual(record['errors'], [])
                self.assertFalse(record['api_call_attempted'])
                self.assertNotIn('messages', record)
            model.assert_not_called()

    def test_explicit_contrast_preserves_positive_finding(self):
        query = retrieval_query({'chief_complaint': 'No fever, rash or diarrhoea, but joint pain.'})
        self.assertNotIn('fever', query)
        self.assertIn('joint pain', query)
        self.assertNotIn('diarrhoea', query)
        self.assertTrue(retrieve({'chief_complaint': 'No fever, but rash and headache.'})[2])

    def test_unknown_and_denied_findings_are_not_positive(self):
        for complaint in ('Denies fever, rash and diarrhoea.', 'Fever status unknown.',
                          'No fever. No rash. No diarrhoea.', 'Age 30, female, day 2.'):
            self.assertEqual(retrieve({'chief_complaint': complaint})[2], [], complaint)

    def test_no_ranked_fallback_for_unrelated_word_overlap(self):
        index = CardIndex()
        query = 'frequent urination mild lower abdominal discomfort age 30 day 2 female'
        self.assertTrue(index.search(query, 10))  # Lexical overlap alone exists.
        self.assertEqual(index.recommendation_search(query, 10), [])

    def test_count_is_a_cap_and_no_zero_score_padding(self):
        _, _, hits = retrieve({'chief_complaint': 'Elevated blood pressure follow-up'})
        self.assertTrue(hits)
        self.assertLess(len(hits), 10)
        self.assertTrue(all(hit['score'] > 0 for hit in hits))
        self.assertTrue(all(hit['card']['disease'] == 'hypertension' for hit in hits))
        self.assertLessEqual(len(retrieve({'chief_complaint': 'Fever and rash'}, top_k=3)[2]), 3)

    def test_existing_ordinary_cases_retain_primary_protocol_categories(self):
        cases = json.loads((ROOT/'evaluation/experiment/cases.json').read_text())['cases']
        expected = {'C01':'dengue', 'C02':'hypertension', 'C03':'cholera', 'C04':'chikungunya', 'C06':'hypertension'}
        for case in cases:
            if case['case_id'] not in expected:
                continue
            hits = retrieve(case['patient'])[2]
            cards = [h['card'] for h in hits if h['card']['disease'] == expected[case['case_id']]]
            self.assertEqual({c['clinical_category'] for c in cards},
                             {'probable_diagnosis','investigations','medication_guidance','advice'})

    def test_ui_abstention_is_not_ready_for_review_or_an_api_cooldown(self):
        with patch('src.engine.chat') as model:
            app = AppTest.from_file(str(ROOT/'app.py'), default_timeout=15).run()
            next(t for t in app.text_area if t.label == 'Chief complaint / symptoms').set_value(URINARY['chief_complaint']).run()
            next(b for b in app.button if b.label == 'Preview evidence').click().run()
            self.assertEqual(app.session_state['record']['status'], 'no_evidence')
            self.assertTrue(any(m.label == 'Retrieved source cards' and m.value == '0' for m in app.metric))
            self.assertTrue(any(m.label == 'Plan status' and m.value == 'Insufficient evidence' for m in app.metric))
            next(b for b in app.button if b.label == 'Generate care plan').click().run()
            saved = Path(app.session_state['record']['saved_path'])
            self.assertEqual(saved.parent, ROOT/'evaluation/interactive_runs')
            self.addCleanup(saved.unlink, missing_ok=True)
            self.assertEqual(app.session_state['record']['status'], 'no_evidence')
            self.assertNotIn('last_api_start', app.session_state)
            self.assertFalse(app.exception)
            model.assert_not_called()

    def test_old_retrieval_record_is_hidden_after_policy_change(self):
        app = AppTest.from_file(str(ROOT/'app.py'), default_timeout=15).run()
        next(t for t in app.text_area if t.label == 'Chief complaint / symptoms').set_value('Fever').run()
        next(b for b in app.button if b.label == 'Preview evidence').click().run()
        app.session_state['record'].pop('retrieval_version')
        app.run()
        self.assertTrue(any('retrieval policy was updated' in message.value for message in app.info))
        self.assertFalse(app.metric)
