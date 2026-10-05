#!/usr/bin/env python3
"""Approved service preparation only; never reads tokens or starts the connector."""
import os
from pathlib import Path
import shutil
import subprocess

root = Path(__file__).resolve().parents[1]
if root != Path('/home/taylor/patch-vigilantes-counter'):
    raise RuntimeError('unexpected deployment directory')
os.umask(0o077)
subprocess.run(['sudo', '-n', 'true'], check=True)
names = ['patch-vigilantes-counter.service', 'patch-vigilantes-counter-tunnel.service']
for name in names:
    destination = Path('/etc/systemd/system') / name
    if destination.exists() and destination.read_bytes() != (root / 'deploy' / name).read_bytes():
        raise RuntimeError('installed counter unit differs from its prepared template; inspect before replacing')
runtime = root / 'runtime'
runtime.mkdir(mode=0o700, exist_ok=True)
if not (runtime / 'cloudflared').is_file():
    binary = Path('/home/taylor/server-migration-production/shazchat/runtime/cloudflared')
    if not binary.is_file():
        raise RuntimeError('verified Cloudflare binary is unavailable')
    shutil.copy2(str(binary), str(runtime / 'cloudflared'))
    os.chmod(str(runtime / 'cloudflared'), 0o700)
settings = root / 'runtime.env'
expected_settings = 'COUNTER_PUBLIC_HOST=counter.novatec.casa\n'
if settings.exists() and settings.read_text() != expected_settings:
    raise RuntimeError('counter hostname settings differ; inspect before replacing')
if not settings.exists():
    settings.write_text(expected_settings)
active = subprocess.run(['systemctl', 'is-active', '--quiet', 'patch-vigilantes-counter.service']).returncode == 0
if not active and (root / 'staging.pid').exists():
    subprocess.run(['/usr/bin/python3', str(root / 'deploy' / 'staging.py'), '--stop'], check=True)
changed = False
for name in names:
    destination = Path('/etc/systemd/system') / name
    if not destination.exists():
        subprocess.run(['sudo', '-n', 'install', '-m', '644', str(root / 'deploy' / name), str(destination)], check=True)
        changed = True
if changed:
    subprocess.run(['sudo', '-n', 'systemctl', 'daemon-reload'], check=True)
subprocess.run(['sudo', '-n', 'systemctl', 'enable', '--now', 'patch-vigilantes-counter.service'], check=True)
print('Counter boot service enabled. Dedicated connector prepared but not enabled or started; user credential handoff required.')
