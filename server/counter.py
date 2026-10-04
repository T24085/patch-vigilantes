#!/usr/bin/env python3
"""Aggregate counter: Python 3.8+, stdlib only, no request logging."""
import argparse
from contextlib import closing
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import signal
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_COUNT = 9007199254740991
BOT = re.compile(r'bot|crawler|spider|headless|playwright|selenium', re.I)
EVENT = re.compile(r'^[a-f0-9]{32}$')
SIGNATURE = re.compile(r'^[a-f0-9]{64}$')


class Counter:
    def __init__(self, directory, origin, paths, request_limit=60, write_limit=12):
        self.origin, self.paths = origin, frozenset(paths)
        self.key, self.rate_key = secrets.token_bytes(32), secrets.token_bytes(32)
        self.lock = threading.Lock()
        self.rate_epoch, self.rates = int(time.time() // 60), {}
        self.request_limit, self.write_limit = request_limit, write_limit
        directory = Path(directory)
        directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.database = str(directory / 'page-views.sqlite3')
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.execute('CREATE TABLE IF NOT EXISTS aggregate (id INTEGER PRIMARY KEY CHECK(id=1), page_views INTEGER NOT NULL CHECK(page_views>=0))')
            db.execute('INSERT OR IGNORE INTO aggregate VALUES (1,0)')
            db.execute('CREATE TABLE IF NOT EXISTS events (digest TEXT PRIMARY KEY, expires INTEGER NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS tickets (digest TEXT PRIMARY KEY, event TEXT NOT NULL, expires INTEGER NOT NULL)')
        if os.name != 'nt':
            os.chmod(self.database, 0o600)

    def connect(self):
        db = sqlite3.connect(self.database, timeout=5, isolation_level=None)
        db.execute('PRAGMA synchronous=FULL')
        return closing(db)

    def prune(self):
        with self.connect() as db:
            now = int(time.time())
            db.execute('DELETE FROM events WHERE expires < ?', (now,))
            db.execute('DELETE FROM tickets WHERE expires < ?', (now,))

    def count(self):
        with self.connect() as db:
            return db.execute('SELECT page_views FROM aggregate WHERE id=1').fetchone()[0]

    def rate_allowed(self, address, writing=False):
        # HMAC immediately; no address is retained/logged. Buckets and their
        # random key rotate each minute and never touch persistent storage.
        epoch = int(time.time() // 60)
        with self.lock:
            if epoch != self.rate_epoch:
                self.rate_epoch, self.rate_key, self.rates = epoch, secrets.token_bytes(32), {}
            digest = hmac.new(self.rate_key, address.encode(), hashlib.sha256).digest()
            if digest not in self.rates and len(self.rates) >= 4096:
                return False
            bucket = self.rates.setdefault(digest, [0, 0])
            global_bucket = self.rates.setdefault(b'global', [0, 0])
            slot = 1 if writing else 0
            limit = self.write_limit if writing else self.request_limit
            if bucket[slot] >= limit or global_bucket[slot] >= (240 if writing else 1200):
                return False
            bucket[slot] += 1
            global_bucket[slot] += 1
            return True

    def challenge(self):
        payload = '{}.{}'.format(int(time.time()), secrets.token_hex(16))
        return payload + '.' + hmac.new(self.key, payload.encode(), hashlib.sha256).hexdigest()

    def valid_challenge(self, token, now):
        if not isinstance(token, str) or len(token) > 120:
            return False
        parts = token.split('.')
        if len(parts) != 3 or not re.fullmatch(r'[0-9]{1,12}', parts[0]) or not EVENT.fullmatch(parts[1]) or not SIGNATURE.fullmatch(parts[2]):
            return False
        expected = hmac.new(self.key, '.'.join(parts[:2]).encode(), hashlib.sha256).hexdigest()
        return 0 <= now - int(parts[0]) <= 120 and hmac.compare_digest(expected, parts[2])

    def handle(self, method, headers, body=b'', address='loopback'):
        origin = headers.get('origin')
        if origin and origin != self.origin:
            return 403, {'error': 'origin_rejected'}
        if not self.rate_allowed(address):
            return 429, {'error': 'rate_limited'}
        if method == 'GET':
            result = {'pageViews': self.count()}
            if origin == self.origin and not BOT.search(headers.get('user-agent', '')):
                result['challenge'] = self.challenge()
            return 200, result
        if method != 'POST':
            return 405, {'error': 'method_rejected'}
        if origin != self.origin:
            return 403, {'error': 'origin_required'}
        if headers.get('content-type', '').lower() != 'application/json':
            return 415, {'error': 'json_required'}
        if len(body) > 1024:
            return 413, {'error': 'body_too_large'}
        try:
            event = json.loads(body.decode('utf-8'))
        except (ValueError, UnicodeError):
            return 400, {'error': 'invalid_json'}
        if not isinstance(event, dict) or set(event) != {'path', 'eventId', 'challenge'}:
            return 400, {'error': 'invalid_event'}
        if not isinstance(event['path'], str) or event['path'] not in self.paths:
            return 400, {'error': 'invalid_path'}
        if not isinstance(event['eventId'], str) or not EVENT.fullmatch(event['eventId']):
            return 400, {'error': 'invalid_event_id'}
        if BOT.search(headers.get('user-agent', '')) or headers.get('x-workshop-test'):
            return 200, {'pageViews': self.count(), 'counted': False}
        now = int(time.time())
        if not self.valid_challenge(event['challenge'], now):
            return 403, {'error': 'invalid_challenge'}
        if not self.rate_allowed(address, writing=True):
            return 429, {'error': 'rate_limited'}
        event_digest = hashlib.sha256(event['eventId'].encode()).hexdigest()
        ticket_digest = hashlib.sha256(event['challenge'].encode()).hexdigest()
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                db.execute('DELETE FROM events WHERE expires < ?', (now,))
                db.execute('DELETE FROM tickets WHERE expires < ?', (now,))
                count = db.execute('SELECT page_views FROM aggregate WHERE id=1').fetchone()[0]
                ticket = db.execute('SELECT event FROM tickets WHERE digest=?', (ticket_digest,)).fetchone()
                if ticket:
                    db.commit()
                    return (200, {'pageViews': count, 'counted': False}) if ticket[0] == event_digest else (409, {'error': 'challenge_used'})
                duplicate = db.execute('SELECT 1 FROM events WHERE digest=?', (event_digest,)).fetchone()
                if count >= MAX_COUNT:
                    db.rollback()
                    return 503, {'error': 'counter_full'}
                db.execute('INSERT INTO tickets VALUES (?,?,?)', (ticket_digest, event_digest, now + 120))
                if not duplicate:
                    db.execute('INSERT INTO events VALUES (?,?)', (event_digest, now + 30))
                    db.execute('UPDATE aggregate SET page_views=page_views+1 WHERE id=1')
                    count += 1
                db.commit()
                return 200, {'pageViews': count, 'counted': not bool(duplicate)}
            except Exception:
                db.rollback()
                raise


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, counter, public_host=''):
        self.counter = counter
        self.hosts = {public_host, '127.0.0.1:' + str(address[1]), 'localhost:' + str(address[1])} - {''}
        self.slots = threading.BoundedSemaphore(32)
        super().__init__(address, Handler)
        if address[1] == 0:
            self.hosts.add('127.0.0.1:' + str(self.server_port))

    def process_request(self, request, address):
        if not self.slots.acquire(False):
            request.close()
            return
        try:
            super().process_request(request, address)
        except Exception:
            self.slots.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.slots.release()

    def handle_error(self, request, address):
        print('counter request failed', flush=True)


class Handler(BaseHTTPRequestHandler):
    server_version, sys_version = 'WorkshopCounter', ''
    protocol_version = 'HTTP/1.1'

    def setup(self):
        super().setup()
        self.connection.settimeout(3)

    def log_message(self, *args):
        pass

    def send_json(self, status, data, cors=False):
        payload = json.dumps(data, separators=(',', ':')).encode()
        self.send_response(status)
        for key, value in [('Content-Type', 'application/json; charset=utf-8'), ('Content-Length', str(len(payload))), ('Cache-Control', 'no-store'), ('X-Content-Type-Options', 'nosniff'), ('Vary', 'Origin'), ('Connection', 'close')]:
            self.send_header(key, value)
        if status == 429:
            self.send_header('Retry-After', '60')
        if status == 405:
            self.send_header('Allow', 'GET, POST, OPTIONS')
        if cors:
            self.send_header('Access-Control-Allow-Origin', self.server.counter.origin)
            self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.send_header('Access-Control-Max-Age', '600')
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(payload)
        self.close_connection = True

    def serve(self):
        headers = {key.lower(): value for key, value in self.headers.items()}
        cors = headers.get('origin') == self.server.counter.origin
        if headers.get('host', '').lower() not in self.server.hosts:
            return self.send_json(421, {'error': 'host_rejected'})
        if self.path == '/healthz' and self.command == 'GET':
            try:
                self.server.counter.count()
                return self.send_json(200, {'ok': True})
            except (sqlite3.Error, OSError):
                return self.send_json(503, {'ok': False})
        if self.path != '/counter':
            return self.send_json(404, {'error': 'not_found'})
        if self.command == 'OPTIONS':
            if not cors or headers.get('access-control-request-method') not in {'GET', 'POST'}:
                return self.send_json(403, {'error': 'preflight_rejected'})
            requested = {h.strip().lower() for h in headers.get('access-control-request-headers', '').split(',') if h.strip()}
            if not requested <= {'content-type'}:
                return self.send_json(403, {'error': 'headers_rejected'})
            return self.send_json(200, {}, True)
        body = b''
        if self.command == 'POST':
            lengths = self.headers.get_all('Content-Length') or []
            if 'transfer-encoding' in headers or len(lengths) != 1 or not lengths[0].isdigit():
                return self.send_json(400, {'error': 'invalid_length'}, cors)
            length = int(lengths[0])
            if length > 1024:
                return self.send_json(413, {'error': 'body_too_large'}, cors)
            body = self.rfile.read(length)
            if len(body) != length:
                return self.send_json(400, {'error': 'incomplete_body'}, cors)
        # Listener is loopback only. Trust this header only from the local
        # connector; do not put a LAN listener in front of this service.
        address = headers.get('cf-connecting-ip', self.client_address[0])
        if len(address) > 64:
            return self.send_json(400, {'error': 'invalid_proxy_address'}, cors)
        try:
            status, data = self.server.counter.handle(self.command, headers, body, address)
        except (sqlite3.Error, OSError):
            status, data = 503, {'error': 'storage_unavailable'}
        self.send_json(status, data, cors)

    do_GET = do_POST = do_OPTIONS = do_PUT = do_DELETE = do_PATCH = do_HEAD = serve


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', required=True)
    parser.add_argument('--port', type=int, default=4319)
    parser.add_argument('--origin', default='https://t24085.github.io')
    parser.add_argument('--public-host', default=os.environ.get('COUNTER_PUBLIC_HOST', ''))
    args = parser.parse_args()
    if args.origin != 'https://t24085.github.io':
        parser.error('production origin must be https://t24085.github.io')
    os.umask(0o077)
    counter = Counter(args.directory, args.origin, ['/patch-vigilantes/', '/patch-vigilantes/index.html'])
    server = Server(('127.0.0.1', args.port), counter, args.public_host)
    cleanup_stop = threading.Event()
    def cleanup():
        while not cleanup_stop.wait(15):
            try:
                counter.prune()
            except (sqlite3.Error, OSError):
                print('counter cleanup unavailable', flush=True)
    counter.prune()
    threading.Thread(target=cleanup, daemon=True).start()
    def stop(signum, frame):
        threading.Thread(target=server.shutdown, daemon=True).start()
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    print('counter listening on loopback port {}'.format(server.server_port), flush=True)
    try:
        server.serve_forever()
    finally:
        cleanup_stop.set()
        server.server_close()


if __name__ == '__main__':
    main()
