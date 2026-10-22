"""Verify mode isolation and no expected-answer leakage; no API calls."""
import copy
import json
import unittest
from pathlib import Path
from src.engine import messages_for, retrieve, recommend
from streamlit.testing.v1 import AppTest


class ExperimentTests(unittest.TestCase):
    def test_only_preview_changes_between_modes(self):
        patient, _, hits = retrieve({'chief_complaint': 'Fever and body pain', 'illness_day': None})
        before = copy.deepcopy((patient, hits))
        baseline = messages_for(patient, hits, 'baseline')
        improved = messages_for(patient, hits, 'improved')
        self.assertEqual(baseline[0], improved[0])
        b, i = json.loads(baseline[1]['content']), json.loads(improved[1]['content'])
        preview = i.pop('applicability_preview')
        self.assertEqual(b, i)
        self.assertEqual(set(preview['cards']), {h['card']['card_id'] for h in hits})
        self.assertEqual(before, (patient, hits))
        self.assertTrue(any(v in ('model_review', 'needs_information', 'trigger_review') for v in preview['cards'].values()))
        self.assertNotIn('checklist', json.dumps(i))

    def test_invalid_mode_rejected_before_api(self):
        with self.assertRaises(ValueError):
            recommend({'chief_complaint': 'Fever'}, mode='invented')

    def test_mode_switch_hides_previous_result(self):
        app = AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'), default_timeout=15).run()
        next(t for t in app.text_area if t.label == 'Chief complaint / symptoms').set_value('Fever').run()
        next(b for b in app.button if b.label == 'Preview evidence').click().run()
        self.assertEqual(app.session_state['record']['mode'], 'baseline')
        next(s for s in app.selectbox if s.label == 'Recommendation mode').select('improved').run()
        self.assertTrue(any('mode has changed' in message.value for message in app.info))
        next(b for b in app.button if b.label == 'Preview evidence').click().run()
        self.assertEqual(app.session_state['record']['mode'], 'improved')
        self.assertFalse(app.exception)
