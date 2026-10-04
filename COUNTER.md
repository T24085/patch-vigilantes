# Page View Counter

The retro ticker displays the shared aggregate returned by a small Jetson backend. The implementation is staged and tested; public activation is pending tunnel ownership verification, secure user credential handoff, and approval for DNS, tunnel and boot changes. Until the verified endpoint is configured, the website displays unavailable. Test counts are never copied into production.

## What counts

Accepted loads of `/patch-vigilantes/` or `/patch-vigilantes/index.html` add one page view. Reloads in the same tab within 30 seconds reuse a random event ID and normally count once. A new tab or a later load can add another view. This is not unique people, unique devices, or verified human traffic. When session storage is unavailable, new random events still work, but reload suppression is less effective. Obvious bot/headless user agents and explicit internal test events are skipped; unknown bots can still count. Offline loads are not queued or counted later.

## Backend and privacy

`server/counter.py` uses the Jetson's Python 3.8+ standard library and SQLite, with no additional packages. It listens only on `127.0.0.1:4319`. SQLite transactions preserve the total across process restarts and serialize concurrent increments. Production begins at zero. Keep the private database outside the public site, in `counter-data/page-views.sqlite3`; do not replace it when updating source. The old Node adapter and its tests are retained for reference, but are not the deployed backend.

GET `/counter` reads the total without incrementing. An allowed browser origin also receives a signed challenge valid for 120 seconds. POST requires a JSON event, valid page path, random event ID and challenge. A used challenge cannot increment a different event. Duplicate retries return the total without adding another view. Host and path allowlists, body-size limits, request deadlines and 32 worker slots bound the local HTTP service.

Only the aggregate is durable analytics. SQLite also holds SHA-256 digests of random events for 30 seconds and consumed challenges for 120 seconds for duplicate/replay suppression. A cleanup task removes expired active rows every 15 seconds; startup also prunes them. Expired bytes are not guaranteed to be forensically erased from SQLite files. Raw IPs, user agents, referrers, cookies, browser characteristics and fingerprints are not saved. A random event value is stored only in tab session storage and replaced on the next load after its short window; it is not a person or device ID.

For rate limits, the local Cloudflare connector's `CF-Connecting-IP` header is immediately HMACed with a random in-memory key. The key and all buckets rotate each minute; raw IPs and these buckets never go to disk. Requests are limited to 60 per address per minute and accepted write attempts to 12; global ceilings are 1,200 requests and 240 write attempts per minute. Shared-network visitors may share a limit. Request/access logging is disabled in the application. Cloudflare's edge processing and any separately enabled edge logs are outside this application.

The only allowed browser origin is `https://t24085.github.io`. CORS does not authenticate visitors: a custom HTTP client can spoof Origin and obtain challenges. These controls deter accidental misuse, simple replay and cheap bursts; this is an approximate popularity counter, not a trusted billing or security metric. Different pages on the same GitHub account also share that origin.

## Frontend configuration

`site/counter.js` accepts an explicitly configured HTTPS `/counter` URL, sends no credentials, and uses a five-second deadline. It never manufactures or caches a popularity count. The HTML `counter-endpoint` meta value stays empty until an approved public endpoint has been verified. A counter failure leaves the six dashes visible and does not block navigation or page content.

The gold retro digits, accessible status text and whimsical workshop design are preserved. Larger totals fit within the counter width, including at 320 pixels. The label remains page views.

## Validation and activation

- `python test/counter_python.py`: ten backend test groups, including actual process restart, persistence, 40 concurrent unique events, 30 concurrent duplicate retries, HTTP routes/CORS, malformed/Unicode input, bot/test skipping, rate limits and expired-digest cleanup.
- `node test/counter.cjs`: ten original adapter assertions retained.
- `node test/counter_browser.cjs`: ten rendered fixture states using Playwright, with desktop/tablet/phone widths, reload suppression, expired event replacement, large counts, offline, malformed-response, disabled and timeout states. Set `PLAYWRIGHT_MODULE` and `CHROMIUM_EXECUTABLE` if using an existing local installation. The `.test` hostname exists only inside browser interception; it is never published or configured in HTML.

Browser screenshots and fixture databases stay under ignored `.preview`. See `deploy/ACTIVATION.md` for the staged layout, service template, approval requirements and publication gates.
