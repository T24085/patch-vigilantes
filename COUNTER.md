# Page-View Counter

The visible retro ticker is unavailable in a local/static-only preview. No fake count is seeded; no browser-local storage pretends to be a global count.

`site/counter.js` activates only when `meta[name=counter-endpoint]` contains a first-party endpoint on the same origin. It sends one page-view event per page load, without cookies, IDs or fingerprints. The counter labels page views, not unique people.

`server/counter-store.cjs` is an optional deployment adapter; it opens no network listener. A separately approved host must wire GET/POST `/counter` to `createCounter`, supply its exact `allowedOrigin`, and provide a persistent filesystem directory outside public assets. Set the HTML meta value to `/counter` only after that route exists. Use a single process; the synchronous read/write path preserves counts across restart in that process. Multiple replicas require an atomic shared database adapter. Serverless ephemeral filesystems are not persistent storage.

State begins at zero. POST increments validated home-page events; GET reads without incrementing. Obvious bot/test user agents and explicit internal-test headers are skipped. These filters are approximate, not abuse prevention or uniqueness guarantees. Only `{pageViews}` is stored; no raw IP, user agent, referrer or identifier is written. Configure any hosting-level access logs separately before public deployment.

Tests: `node test/counter.cjs` — zero baseline, increments, bot/test filtering, origin rejection, malformed-event rejection and persistence. Test counts are disposable under ignored `.preview`; they are never production popularity. No backend has been deployed, no external tracking account created, and no live shared count is claimed.