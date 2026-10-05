'use strict';
(async () => {
  const status = document.getElementById('counter-status');
  const digits = document.getElementById('counter-digits');
  const raw = document.querySelector('meta[name="counter-endpoint"]')?.content;
  if (!status || !digits || !raw) return;
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 5000);
  try {
    if (location.protocol === 'file:') throw Error('Local preview');
    const endpoint = new URL(raw, location.href);
    if (endpoint.protocol !== 'https:' || endpoint.username || endpoint.password ||
        endpoint.pathname !== '/counter' || endpoint.search || endpoint.hash) {
      throw Error('Invalid counter configuration');
    }
    const options = {credentials: 'omit', cache: 'no-store', signal: controller.signal};
    const read = await fetch(endpoint, options);
    if (!read.ok) throw Error('Counter unavailable');
    let data = await read.json();
    if (data.challenge) {
      // Random event ID, reused for rapid reloads in this tab for 30 seconds.
      // This is not a person/device ID and is never shared across websites.
      let event;
      try { event = JSON.parse(sessionStorage.getItem('workshop-page-event')); } catch {}
      const now = Date.now();
      if (!event || !/^[a-f0-9]{32}$/.test(event.id) ||
          !Number.isFinite(event.created) || now - event.created >= 30000 || now < event.created) {
        const bytes = crypto.getRandomValues(new Uint8Array(16));
        event = {id: [...bytes].map(n => n.toString(16).padStart(2, '0')).join(''), created: now};
        try { sessionStorage.setItem('workshop-page-event', JSON.stringify(event)); } catch {}
      }
      const response = await fetch(endpoint, {...options, method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({path: location.pathname, eventId: event.id, challenge: data.challenge})});
      if (!response.ok) throw Error('Counter unavailable');
      data = await response.json();
    }
    if (!Number.isSafeInteger(data.pageViews) || data.pageViews < 0) throw Error('Invalid count');
    const count = String(data.pageViews).padStart(6, '0');
    digits.replaceChildren(...[...count].map(n => {
      const span = document.createElement('span');
      span.textContent = n;
      return span;
    }));
    digits.style.setProperty('--counter-length', String(count.length));
    status.textContent = data.pageViews.toLocaleString() +
      (data.pageViews === 1 ? ' page view recorded.' : ' page views recorded.');
  } catch {
    status.textContent = 'Counter unavailable. Try another visit.';
  } finally {
    clearTimeout(timeout);
  }
})();
