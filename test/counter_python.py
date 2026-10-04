import concurrent.futures
from contextlib import closing
import hashlib
import http.client
import importlib.util
import json
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest

spec = importlib.util.spec_from_file_location('counter', Path(__file__).resolve().parents[1] / 'server' / 'counter.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
ORIGIN = 'https://t24085.github.io'
HEADERS = {'origin': ORIGIN, 'content-type': 'application/json', 'user-agent': 'Mozilla/5.0'}


class CounterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.counter = module.Counter(self.temp.name, ORIGIN, ['/patch-vigilantes/', '/patch-vigilantes/index.html'], 500, 200)

    def tearDown(self):
        self.temp.cleanup()

    def event(self, **overrides):
        event = {'path': '/patch-vigilantes/', 'eventId': secrets.token_hex(16), 'challenge': self.counter.challenge()}
        event.update(overrides)
        return json.dumps(event).encode()

    def post(self, event=None, headers=None):
        return self.counter.handle('POST', headers or HEADERS, event or self.event())

    def test_zero_read_increment_restart_and_privacy(self):
        self.assertEqual(self.counter.handle('GET', {})[1], {'pageViews': 0})
        self.assertEqual(self.post()[1], {'pageViews': 1, 'counted': True})
        restarted = module.Counter(self.temp.name, ORIGIN, ['/patch-vigilantes/'])
        self.assertEqual(restarted.count(), 1)
        with closing(sqlite3.connect(self.counter.database, isolation_level=None)) as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            columns = [row[1] for row in db.execute('PRAGMA table_info(aggregate)')]
            self.assertEqual(columns, ['id', 'page_views'])
            self.assertEqual(len(db.execute('SELECT digest FROM events').fetchone()[0]), 64)
        self.counter.rate_allowed('198.51.100.31')
        self.assertNotIn('198.51.100.31', repr(self.counter.rates))

    def test_duplicate_and_one_use_challenge(self):
        event = json.loads(self.event())
        self.assertTrue(self.post(json.dumps(event).encode())[1]['counted'])
        self.assertFalse(self.post(json.dumps(event).encode())[1]['counted'])
        old_challenge = event['challenge']
        event['challenge'] = self.counter.challenge()
        self.assertFalse(self.post(json.dumps(event).encode())[1]['counted'])
        event.update(eventId=secrets.token_hex(16), challenge=old_challenge)
        self.assertEqual(self.post(json.dumps(event).encode())[0], 409)
        self.assertEqual(self.counter.count(), 1)

    def test_parallel_atomic_increments(self):
        events = [self.event() for _ in range(40)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(self.post, events))
        self.assertTrue(all(status == 200 and body['counted'] for status, body in results))
        self.assertEqual(self.counter.count(), 40)

    def test_parallel_retries_only_count_once(self):
        event = self.event()
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(lambda _: self.post(event), range(30)))
        self.assertEqual(sum(body['counted'] for status, body in results), 1)
        self.assertEqual(self.counter.count(), 1)

    def test_invalid_requests(self):
        for raw in [b'null', b'[]', b'0', b'{}', b'{', b'\xff', b'x' * 1025]:
            with self.subTest(raw=raw[:20]):
                self.assertIn(self.post(raw)[0], [400, 413])
        for overrides in [{'path': []}, {'path': '/admin'}, {'eventId': None}, {'challenge': None}, {'challenge': 'fake'}, {'challenge': '1.' + 'a' * 32 + '.' + 'b' * 64}, {'challenge': str(int(time.time())) + '.' + 'a' * 32 + '.' + '\u00e9'}, {'challenge': '\u00b2.' + 'a' * 32 + '.' + 'b' * 64}]:
            self.assertIn(self.post(self.event(**overrides))[0], [400, 403])
        self.assertEqual(self.post(headers={**HEADERS, 'origin': 'https://evil.example'})[0], 403)
        self.assertEqual(self.post(headers={'content-type': 'application/json'})[0], 403)
        self.assertEqual(self.post(headers={**HEADERS, 'content-type': 'text/plain'})[0], 415)
        self.assertEqual(self.counter.handle('DELETE', HEADERS)[0], 405)
        self.assertEqual(self.counter.count(), 0)

    def test_bot_and_test_events(self):
        for headers in [{**HEADERS, 'user-agent': 'Googlebot'}, {**HEADERS, 'x-workshop-test': '1'}]:
            self.assertEqual(self.post(headers=headers)[1], {'pageViews': 0, 'counted': False})
        self.assertNotIn('challenge', self.counter.handle('GET', {**HEADERS, 'user-agent': 'Googlebot'})[1])

    def test_rate_limit(self):
        limited = module.Counter(self.temp.name, ORIGIN, ['/patch-vigilantes/'], 500, 2)
        for _ in range(2):
            self.assertEqual(limited.handle('POST', HEADERS, self.event(challenge=limited.challenge()))[0], 200)
        self.assertEqual(limited.handle('POST', HEADERS, self.event(challenge=limited.challenge()))[0], 429)
        self.assertEqual(limited.count(), 2)

    def test_expired_digests_pruned(self):
        self.post()
        with closing(sqlite3.connect(self.counter.database, isolation_level=None)) as db:
            db.execute('UPDATE events SET expires=0')
            db.execute('UPDATE tickets SET expires=0')
        self.counter.prune()
        with closing(sqlite3.connect(self.counter.database, isolation_level=None)) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM events').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM tickets').fetchone()[0], 0)
        self.assertEqual(self.counter.count(), 1)

    def test_http_routes_cors_and_parallel(self):
        server = module.Server(('127.0.0.1', 0), self.counter)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        def request(method='GET', path='/counter', body=None, headers=None):
            connection = http.client.HTTPConnection('127.0.0.1', server.server_port, timeout=5)
            connection.request(method, path, body, headers or {})
            response = connection.getresponse()
            result = response.status, dict(response.getheaders()), response.read()
            connection.close()
            return result
        try:
            status, headers, payload = request(headers=HEADERS)
            self.assertEqual(status, 200)
            self.assertEqual(headers['Access-Control-Allow-Origin'], ORIGIN)
            self.assertNotIn('Set-Cookie', headers)
            self.assertEqual(request(path='/admin')[0], 404)
            self.assertEqual(request(headers={'Host': 'evil.example'})[0], 421)
            self.assertEqual(request('OPTIONS', headers={'Origin': ORIGIN, 'Access-Control-Request-Method': 'POST', 'Access-Control-Request-Headers': 'Content-Type'})[0], 200)
            self.assertEqual(request('OPTIONS', headers={'Origin': 'https://evil.example', 'Access-Control-Request-Method': 'POST'})[0], 403)
            self.assertEqual(request('POST', body=b'x' * 1025, headers=HEADERS)[0], 413)
            events = [self.event() for _ in range(20)]
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
                responses = list(pool.map(lambda event: request('POST', body=event, headers=HEADERS), events))
            self.assertTrue(all(response[0] == 200 for response in responses))
            self.assertEqual(self.counter.count(), 20)
        finally:
            server.shutdown()
            worker.join()
            server.server_close()

    def test_persistence_across_real_process_restart(self):
        directory = str(Path(self.temp.name) / 'process-data')
        command = [sys.executable, str(Path(__file__).resolve().parents[1] / 'server' / 'counter.py'), '--directory', directory, '--port', '0']
        event_id = secrets.token_hex(16)
        for iteration in range(2):
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            try:
                line = process.stdout.readline()
                self.assertIn('loopback port ', line)
                port = int(line.rsplit(' ', 1)[1])
                connection = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
                connection.request('GET', '/counter', headers=HEADERS)
                read = json.loads(connection.getresponse().read())
                connection.close()
                self.assertEqual(read['pageViews'], iteration)
                connection = http.client.HTTPConnection('127.0.0.1', port, timeout=5)
                connection.request('POST', '/counter', self.event(eventId=event_id, challenge=read['challenge']), HEADERS)
                result = json.loads(connection.getresponse().read())
                connection.close()
                self.assertEqual(result['pageViews'], 1)
                self.assertEqual(result['counted'], iteration == 0)
            finally:
                process.terminate()
                process.wait(timeout=10)
                process.stdout.close()
                process.stderr.close()


if __name__ == '__main__':
    unittest.main(verbosity=2)
