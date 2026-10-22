"""App interaction smoke checks using Streamlit's simulated UI; no model answers mocked."""
import json
from pathlib import Path
import unittest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]


class AppTests(unittest.TestCase):
    def setUp(self):
        self.app = AppTest.from_file(str(ROOT/'app.py'), default_timeout=15).run()

    def click(self, label):
        next(button for button in self.app.button if button.label == label).click().run()
        self.assertEqual(len(self.app.exception), 0)

    def test_editable_new_input_and_evidence_preview(self):
        self.assertEqual(len(self.app.exception), 0)
        patient = {'chief_complaint': 'Acute watery diarrhoea and marked thirst', 'age_years': 35}
        self.app.radio[0].set_value('Advanced JSON').run()
        next(t for t in self.app.text_area if t.label == 'Editable patient JSON').set_value(json.dumps(patient)).run()
        self.click('Preview evidence')
        record = self.app.session_state['record']
        self.assertEqual(record['patient'], patient)
        self.assertEqual(record['status'], 'preview')
        self.assertTrue(record['retrieved'])
        self.assertIsNone(record['output'])

    def test_example_load_and_reset(self):
        next(s for s in self.app.selectbox if s.label == 'Fictional examples').select('C06').run()
        self.click('Load example')
        patient = json.loads(self.app.session_state['patient_json'])
        self.assertTrue(patient['history']['may_become_pregnant'])
        self.assertNotIn('case_id', patient)
        self.click('New patient')
        patient = json.loads(self.app.session_state['patient_json'])
        self.assertEqual(patient['chief_complaint'], '')
        self.assertIsNone(patient['history']['pregnant'])
        self.assertEqual(next(t for t in self.app.text_area if t.label == 'Chief complaint / symptoms').value, '')
        self.assertIsNone(next(n for n in self.app.number_input if n.label == 'Age (years)').value)

    def test_guided_entry_without_json_and_stale_plan_notice(self):
        next(t for t in self.app.text_area if t.label == 'Chief complaint / symptoms').set_value('Fever and headache').run()
        next(n for n in self.app.number_input if n.label == 'Age (years)').set_value(31.0).run()
        next(n for n in self.app.number_input if n.label == 'Day of illness').set_value(2).run()
        self.click('Preview evidence')
        self.assertEqual(self.app.session_state['record']['patient']['age_years'], 31)
        self.assertEqual(self.app.session_state['record']['patient']['illness_day'], 2)
        next(t for t in self.app.text_area if t.label == 'Chief complaint / symptoms').set_value('A different complaint').run()
        self.assertTrue(any('has changed' in message.value for message in self.app.info))


if __name__ == '__main__':
    unittest.main()
