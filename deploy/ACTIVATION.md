# Counter Activation

The approved counter and dedicated connector are active and enabled as boot services on the Jetson. The HTTPS endpoint `https://counter.novatec.casa/counter` passed read-only, CORS/preflight, rejection and non-counting test-event checks on October 5, 2026. Its production total was zero before Pages publication. The dedicated tunnel ID is `38ddc6da-6585-4b69-b7b4-a68e31663f0b`; credentials were entered only by Taylor in a private terminal. The origin service is **HTTP** `127.0.0.1:4319`; public TLS terminates at Cloudflare.

## Staged layout

Directory: `/home/taylor/patch-vigilantes-counter`. Source: `server/counter.py`. Private persistent data: `counter-data/page-views.sqlite3`. Tests use disposable databases and temporary listeners. `patch-vigilantes-counter.service` and `patch-vigilantes-counter-tunnel.service` are installed in `/etc/systemd/system` and enabled. Their templates remain in `deploy/`. `deploy/runtime.env.example` contains only a blank hostname setting, not credentials.

The manual launcher, `python3 deploy/staging.py`, checks port availability, launches only this backend and records `staging.pid`. `python3 deploy/staging.py --stop` verifies that PID belongs to this counter before stopping it and preserves its database. Manual staging survives an SSH disconnect but is not a boot service and will not survive a Jetson reboot.

## Tunnel decision and approval

Proposed hostname: `counter.novatec.casa`, with only `/counter` routed to `http://127.0.0.1:4319`. Other paths should return 404 at ingress. No router forwarding or public LAN listener is required.

The prior LLM tunnel proposal uses ID `1f2ac7aa-e364-485e-9a33-7a45e3417ec0`. Its inspected Windows YAML currently includes `novatec.casa` and `www.novatec.casa` pointing to local port 8000, plus a 404 catch-all. That file is evidence of local configuration, not proof of active Cloudflare ingress or connector ownership. Exact live configuration and connector locations remain unverified.

Do not add a Jetson replica of that shared tunnel until every existing route can be served correctly from every connector. Cloudflare sends traffic across the associated replicas, and remotely managed replicas use the same routes. A counter-only replica can therefore disrupt the existing 8000 routes. See [Cloudflare replica documentation](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/tunnel-availability/deploy-replicas/).

Approved dedicated tunnel scope:

> Approve a dedicated `patch-vigilantes-counter` Cloudflare tunnel for `counter.novatec.casa`, routing only `/counter` to Jetson `127.0.0.1:4319`, its required DNS record, and counter/tunnel boot services. Keep the shared LLM tunnel and its existing routes unchanged.

The dedicated route/DNS/boot scope and subsequent Pages publication were explicitly approved. The new tunnel is named `counter.novatec.casa` in Taylor's dashboard and uses its actual UUID above; the shared LLM tunnel was preserved. Any future move into the shared LLM tunnel needs a separate route-preserving plan and approval.

Taylor must provision or securely transfer the chosen tunnel's credential directly to the Jetson. The assistant must not retrieve, copy, print, or transmit tunnel secrets; do not put tokens in chat, screenshots, the repository, logs, or command-line arguments. Confirm credential presence/permissions and tunnel identity only, without reading its contents. Configuration management mode must be established before preparing the connector invocation.

## Counter boot service after approval

These steps are retained for recovery. `deploy/secure_setup.py` now waits up to 15 seconds for backend readiness before enabling the connector. Repeated setup runs reuse the stored credential and identical installed units and preserve the database. The credential receiver never reads or replaces an existing token. Existing active binaries are reused rather than overwritten. Sudo authentication happens only in Taylor's private terminal.

1. Confirm the final hostname and create `runtime.env` in the dedicated directory, containing `COUNTER_PUBLIC_HOST=counter.novatec.casa` only if that exact hostname was approved and configured. This file is nonsecret; keep mode 600 anyway.
2. Stop only the counter staging process using `deploy/staging.py --stop` and recheck 4319. Keep the database intact.
3. Install the prepared unit under `/etc/systemd/system/patch-vigilantes-counter.service`; reload systemd and enable/start this unit only. The unit runs as `taylor`, uses restricted filesystem permissions and 96 MiB memory/25% CPU limits. Persistent changes require prior approval.
4. Verify counter health and total, its systemd state, the exact loopback listener and data permissions. A reboot check is separate approval if it would interrupt other active work.
5. Configure/start only the chosen tunnel using the user-provisioned credential, approved ingress and its separately approved boot service. Do not alter existing tunnel services, nameservers, or unrelated DNS records.

Protected adjacent ports: ShazChat 8765, Icon 4173, migration fixtures 18765/18766 and PandaBrain 8792/8447. Their availability is owned by the migration task; never start, stop or repurpose them from this counter task.

## Public verification and Pages gate

Before any GitHub push or Pages publish, verify the approved hostname's DNS, tunnel ownership, TLS and the exact external `/counter` route. Check that GET is read-only, allowed CORS/preflight works, wrong origins/paths/methods are rejected, and bot/internal test requests do not add popularity. Use `X-Workshop-Test: 1` for non-counting direct POST probes; the allowed preflight intentionally does not grant that header to normal browsers. Keep unrelated routes working. Do not seed the production total with fixture data.

Only after those checks, set the frontend meta URL to the verified HTTPS endpoint. Render the actual Pages origin against the actual backend; one deliberate browser verification visit may add one real view, which must be reported honestly. Confirm repeat reload suppression, offline fallback, small screens and total persistence without resetting the count.

Publish the reviewed implementation to the repository and the site files to its existing site-only `gh-pages` branch. Verify the resulting Pages build and public content before declaring the counter live. The established website stays `https://t24085.github.io/patch-vigilantes/`.

Rollback: clear the frontend endpoint and republish the static site if needed; disable only the counter/tunnel units and remove only the newly created counter route/record as approved. Preserve the SQLite database. Do not remove shared LLM routes or stop shared connectors.
