"""Transport and spend guards; mocked requests do not establish model quality."""
import io
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from src import groq_api
from src.model import selection_schema


class GroqTests(unittest.TestCase):
    def config(self, confirmed=True):
        return {'model': {'provider': 'groq', 'name': groq_api.DEFAULT_MODEL},
                'groq': {'api_key': 'FAKE_KEY_FOR_TEST', 'free_tier_confirmed': confirmed}}

    def test_unconfirmed_plan_never_calls_network(self):
        with patch.object(groq_api, 'configuration', return_value=self.config(False)), patch.object(groq_api, 'request') as network:
            with self.assertRaisesRegex(RuntimeError, 'Free plan'):
                groq_api.chat([], {})
            network.assert_not_called()

    def test_nonallowed_model_never_calls_network(self):
        config = self.config()
        config['model']['name'] = 'unknown-model'
        with patch.object(groq_api, 'configuration', return_value=config), patch.object(groq_api, 'request') as network:
            with self.assertRaisesRegex(RuntimeError, 'allowlist'):
                groq_api.chat([], {})
            network.assert_not_called()

    def test_rate_limit_redacted_without_retry(self):
        key = 'FAKE_KEY_FOR_TEST'
        error = HTTPError('https://example.invalid', 429, 'quota', {}, io.BytesIO(key.encode()))
        with patch.object(groq_api, 'urlopen', side_effect=error) as network:
            with self.assertRaises(RuntimeError) as raised:
                groq_api.request('/chat/completions', key, {})
            self.assertEqual(network.call_count, 1)
            self.assertIn('no retry', str(raised.exception))
            self.assertNotIn(key, str(raised.exception))

    def test_strict_selection_request_and_usage(self):
        schema = selection_schema(['CARD_1'])
        response = {'model': groq_api.DEFAULT_MODEL, 'choices': [{'finish_reason': 'stop',
                    'message': {'content': '{"selections":[],"questions":[],"limitations":[]}'}}],
                    'usage': {'prompt_tokens': 100, 'completion_tokens': 30}}
        with patch.object(groq_api, 'configuration', return_value=self.config()), patch.object(groq_api, 'request', return_value=response) as network:
            result, status = groq_api.chat([{'role': 'user', 'content': 'test'}], schema)
            payload = network.call_args.args[2]
            self.assertTrue(payload['response_format']['json_schema']['strict'])
            self.assertEqual(payload['response_format']['json_schema']['schema'], schema)
            self.assertEqual(result['prompt_eval_count'], 100)
            self.assertTrue(status['generation_verified'])

    def test_truncated_completion_is_not_success(self):
        with patch.object(groq_api, 'configuration', return_value=self.config()), patch.object(groq_api, 'request', return_value={'choices': [{'finish_reason': 'length'}]}):
            with self.assertRaisesRegex(RuntimeError, 'incomplete'):
                groq_api.chat([], {})
