import io
import importlib.util
from pathlib import Path
import time
import unittest

spec = importlib.util.spec_from_file_location('readiness', Path(__file__).resolve().parents[1] / 'deploy' / 'readiness.py')
readiness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(readiness)


class ReadinessTests(unittest.TestCase):
    def test_retries_refused_connection_before_ready(self):
        attempts = []
        def opener(url, timeout):
            attempts.append(url)
            if len(attempts) < 3:
                raise ConnectionRefusedError(111, 'fixture refusal')
            response = io.BytesIO(b'{"ok":true}')
            response.status = 200
            return response
        readiness.wait_for_counter(timeout=2, opener=opener)
        self.assertEqual(len(attempts), 3)

    def test_failure_is_bounded(self):
        def opener(url, timeout):
            raise ConnectionRefusedError(111, 'fixture refusal')
        started = time.monotonic()
        with self.assertRaisesRegex(RuntimeError, 'connector not started'):
            readiness.wait_for_counter(timeout=.1, opener=opener)
        self.assertLess(time.monotonic() - started, .5)


if __name__ == '__main__':
    unittest.main(verbosity=2)
