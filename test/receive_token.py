import base64
import importlib.util
import json
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('receiver', Path(__file__).resolve().parents[1] / 'deploy' / 'receive_token.py')
receiver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(receiver)
ID = '38ddc6da-6585-4b69-b7b4-a68e31663f0b'
TOKEN = base64.b64encode(json.dumps({'a': 'fixture-account', 't': ID, 's': 'DISPOSABLE-TEST-ONLY'}).encode()).decode()


class ReceiverTests(unittest.TestCase):
    def test_raw_and_command_formats(self):
        for value in [TOKEN, 'sudo cloudflared service install ' + TOKEN, 'cloudflared tunnel run --token ' + TOKEN]:
            token = receiver.extract_token(value)
            self.assertEqual(token, TOKEN)
            receiver.validate_token(token, ID)

    def test_invalid_and_wrong_tunnel(self):
        for value in ['not a token', base64.b64encode(b'[]').decode().ljust(40, 'a'), TOKEN]:
            with self.assertRaises(ValueError):
                receiver.validate_token(value, '00000000-0000-4000-8000-000000000002')


if __name__ == '__main__':
    unittest.main(verbosity=2)
