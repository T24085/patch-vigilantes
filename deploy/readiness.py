"""Bounded readiness wait for the counter; no credentials or writes."""
import json
import time
import urllib.request


def wait_for_counter(timeout=15, opener=urllib.request.urlopen):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with opener('http://127.0.0.1:4319/healthz', timeout=min(1, max(.01, deadline - time.monotonic()))) as response:
                if response.status == 200 and json.load(response).get('ok') is True:
                    return
        except (OSError, ValueError, AttributeError):
            pass
        time.sleep(min(.25, max(0, deadline - time.monotonic())))
    raise RuntimeError('Counter did not become healthy within {} seconds; connector not started.'.format(timeout))
