#!/usr/bin/env python3
"""Taylor runs privately after explicit route/DNS/boot approval."""
import os
from pathlib import Path
import subprocess
import sys
from readiness import wait_for_counter

root = Path(__file__).resolve().parents[1]
expected_id = '38ddc6da-6585-4b69-b7b4-a68e31663f0b'
if root != Path('/home/taylor/patch-vigilantes-counter') or not sys.stdin.isatty():
    sys.exit('Run the staged copy in your own private Jetson SSH terminal.')
token_path = root / 'private' / 'cloudflare.token'
if not token_path.exists():
    subprocess.run(['/usr/bin/python3', str(root / 'deploy' / 'receive_token.py'), '--tunnel-id', expected_id], check=True)
# Inspect only metadata and the separately stored nonsecret ID, never the token.
if token_path.is_symlink() or token_path.stat().st_mode & 0o777 != 0o600:
    sys.exit('Private token file must be a regular mode-600 file.')
if (root / 'private' / 'tunnel-id.txt').read_text().strip() != expected_id:
    sys.exit('Nonsecret tunnel ID record does not match this counter tunnel.')
print('Enter the Jetson sudo password privately if prompted. Only the approved counter services will be installed.', flush=True)
subprocess.run(['sudo', '-v'], check=True)
subprocess.run(['/usr/bin/python3', str(root / 'deploy' / 'activate_backend.py')], check=True)
wait_for_counter()
subprocess.run(['sudo', '-n', 'systemctl', 'enable', '--now', 'patch-vigilantes-counter-tunnel.service'], check=True)
print('Approved counter and connector boot services enabled. Wait for Cloudflare Connected, then Continue. No public route or DNS record was created by this script.', flush=True)
