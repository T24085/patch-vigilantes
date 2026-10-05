#!/usr/bin/env python3
"""Taylor runs this in a private SSH terminal. Never run via assistant tools."""
import argparse
import base64
import getpass
import json
import os
from pathlib import Path
import re
import shlex
import sys
import uuid


def extract_token(value):
    # Cloudflare's copy button may copy the whole install command. Parse it
    # as data; never execute it or put its secret into a process argument.
    parts = shlex.split(value)
    if len(parts) == 1:
        return parts[0]
    if '--token' in parts and parts.index('--token') == len(parts) - 2:
        return parts[-1]
    if len(parts) >= 4 and parts[-3:-1] == ['service', 'install']:
        return parts[-1]
    raise ValueError('Input format not recognized; nothing saved.')


def validate_token(token, expected_id):
    if not isinstance(token, str) or not re.fullmatch(r'[A-Za-z0-9_+/=-]{40,8192}', token):
        raise ValueError('Invalid token format. Paste only the token, not the install command.')
    try:
        decoded = base64.b64decode(token + '=' * (-len(token) % 4), altchars=b'-_', validate=True)
        payload = json.loads(decoded.decode('utf-8'))
        actual_id = str(uuid.UUID(payload['t']))
        if not isinstance(payload.get('a'), str) or not payload['a'] or not isinstance(payload.get('s'), str) or not payload['s']:
            raise ValueError()
    except (ValueError, TypeError, KeyError, UnicodeError):
        raise ValueError('Token format not recognized; nothing saved.') from None
    if actual_id != str(uuid.UUID(expected_id)):
        raise ValueError('Token belongs to a different tunnel; nothing saved.')


def main():
    parser = argparse.ArgumentParser(description='Save this counter tunnel token privately; does not connect or expose anything.')
    parser.add_argument('--tunnel-id', required=True, type=lambda value: str(uuid.UUID(value)))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if root != Path('/home/taylor/patch-vigilantes-counter'):
        parser.error('Run only the staged Jetson copy in its dedicated directory.')
    if not sys.stdin.isatty() or not sys.stderr.isatty():
        parser.error('Use your own private SSH terminal with a TTY; hidden input required.')
    os.umask(0o077)
    private = root / 'private'
    if private.is_symlink():
        parser.error('Private directory must not be a symbolic link.')
    private.mkdir(mode=0o700, exist_ok=True)
    os.chmod(str(private), 0o700)
    target = private / 'cloudflare.token'
    if target.exists() or target.is_symlink():
        parser.error('Credential already exists. No existing credential was read or replaced.')
    token = extract_token(getpass.getpass('Paste this counter tunnel token or its install command (hidden), then Enter: ').strip())
    validate_token(token, args.tunnel_id)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(str(target), flags, 0o600)
    with os.fdopen(fd, 'w') as output:
        output.write(token)
        output.flush()
        os.fsync(output.fileno())
    token = None
    (private / 'tunnel-id.txt').write_text(args.tunnel_id + '\n')
    print('Counter token stored privately with mode 600; tunnel ID matched. No connector or boot service started.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError):
        print('Credential validation or private write failed; no connector started.', file=sys.stderr)
        sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        print('\nCancelled; no connector started.', file=sys.stderr)
        sys.exit(1)
