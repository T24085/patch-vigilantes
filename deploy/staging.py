#!/usr/bin/env python3
"""Start/stop only this counter manually. Does not install boot services/routes."""
import argparse
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import time
import urllib.request

root = Path(__file__).resolve().parents[1]
expected = Path('/home/taylor/patch-vigilantes-counter')
parser = argparse.ArgumentParser()
parser.add_argument('--stop', action='store_true')
args = parser.parse_args()
if root != expected:
    parser.error('staging launcher must live in its dedicated Jetson directory')
os.umask(0o077)
pidfile = root / 'staging.pid'
server = str(root / 'server' / 'counter.py')
if args.stop:
    if not pidfile.exists():
        print('no staging PID recorded')
    else:
        pid = int(pidfile.read_text())
        command = Path('/proc/{}/cmdline'.format(pid))
        if command.exists():
            if server.encode() not in command.read_bytes().split(b'\x00'):
                raise RuntimeError('PID no longer belongs to this counter; nothing stopped')
            os.kill(pid, signal.SIGTERM)
            for _ in range(50):
                if not command.exists():
                    break
                time.sleep(0.1)
            else:
                raise RuntimeError('counter did not stop; no other process signalled')
        pidfile.unlink()
        print('only this counter staging process stopped; data preserved')
else:
    if pidfile.exists():
        raise RuntimeError('staging PID exists; inspect/stop it before starting another')
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 4319))
    with open(str(root / 'staging.log'), 'ab', buffering=0) as logfile:
        process = subprocess.Popen(['/usr/bin/python3', server, '--directory', str(root / 'counter-data'), '--port', '4319'], stdin=subprocess.DEVNULL, stdout=logfile, stderr=logfile, start_new_session=True)
    for _ in range(50):
        if process.poll() is not None:
            raise RuntimeError('counter exited before readiness; check its staging log')
        try:
            with urllib.request.urlopen('http://127.0.0.1:4319/counter', timeout=1) as response:
                count = json.load(response)['pageViews']
            pidfile.write_text(str(process.pid))
            print(json.dumps({'pid': process.pid, 'loopbackPort': 4319, 'pageViews': count, 'bootServiceInstalled': False, 'publicRouteActivated': False}))
            break
        except (OSError, ValueError):
            time.sleep(0.1)
    else:
        process.terminate()
        raise RuntimeError('counter failed readiness; only its own process terminated')
