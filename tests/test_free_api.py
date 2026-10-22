"""No real API calls: verify free-tier guard, no retries and secret redaction."""
import io
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from src import gemini


class FreeApiTests(unittest.TestCase):
    def test_no_request_before_free_project_confirmation(self):
        config = {'gemini': {'api_key': 'TEST_NOT_A_REAL_KEY', 'free_tier_confirmed': False}}
        with patch.object(gemini, 'configuration', return_value=config), patch.object(gemini, 'urlopen') as network:
            with self.assertRaisesRegex(RuntimeError, 'Free tier'):
                gemini.chat([], {})
            network.assert_not_called()

    def test_no_request_for_nonallowlisted_model(self):
        config = {'model': {'name': 'not-an-allowed-model'},
                  'gemini': {'api_key': 'TEST_NOT_A_REAL_KEY', 'free_tier_confirmed': True}}
        with patch.object(gemini, 'configuration', return_value=config), patch.object(gemini, 'urlopen') as network:
            with self.assertRaisesRegex(RuntimeError, 'allowlist'):
                gemini.chat([], {})
            network.assert_not_called()

    def test_quota_error_stops_without_retry(self):
        error = HTTPError('https://example.invalid', 429, 'quota', {}, io.BytesIO(b'quota'))
        with patch.object(gemini, 'urlopen', side_effect=error) as network:
            with self.assertRaisesRegex(RuntimeError, 'no retry'):
                gemini.request('/models/test', 'TEST_NOT_A_REAL_KEY', {})
            self.assertEqual(network.call_count, 1)

    def test_api_error_redacts_key(self):
        key = 'TEST_NOT_A_REAL_KEY'
        error = HTTPError('https://example.invalid', 403, 'error', {}, io.BytesIO(key.encode()))
        with patch.object(gemini, 'urlopen', side_effect=error):
            with self.assertRaises(RuntimeError) as result:
                gemini.request('/models/test', key)
            self.assertNotIn(key, str(result.exception))


if __name__ == '__main__':
    unittest.main()
