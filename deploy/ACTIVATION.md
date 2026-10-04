# Counter Activation

The backend and frontend are implemented and tested. The Jetson counter is staged manually on loopback port 4319; no boot service, public tunnel route, DNS record, or Pages update has been activated. Public activation must wait for exact approval and a secure credential handoff by Taylor.

## Staged layout

Directory: `/home/taylor/patch-vigilantes-counter`. Source: `server/counter.py`. Private persistent data: `counter-data/page-views.sqlite3`. Tests use disposable databases and temporary listeners. `deploy/patch-vigilantes-counter.service` is a prepared system service template, not installed in `/etc/systemd/system`. `deploy/runtime.env.example` contains only a blank hostname setting, not credentials.

The manual launcher, `python3 deploy/staging.py`, checks port availability, launches only this backend and records `staging.pid`. `python3 deploy/staging.py --stop` verifies that PID belongs to this counter before stopping it and preserves its database. Manual staging survives an SSH disconnect but is not a boot service and will not survive a Jetson reboot.

## Tunnel decision and approval

Proposed hostname: `counter.novatec.casa`, with only `/counter` routed to `http://127.0.0.1:4319`. Other paths should return 404 at ingress. No router forwarding or public LAN listener is required.

The prior LLM tunnel proposal uses ID `1f2ac7aa-e364-485e-9a33-7a45e3417ec0`. Its inspected Windows YAML currently includes `novatec.casa` and `www.novatec.casa` pointing to local port 8000, plus a 404 catch-all. That file is evidence of local configuration, not proof of active Cloudflare ingress or connector ownership. Exact live configuration and connector locations remain unverified.

Do not add a Jetson replica of that shared tunnel until every existing route can be served correctly from every connector. Cloudflare sends traffic across the associated replicas, and remotely managed replicas use the same routes. A counter-only replica can therefore disrupt the existing 8000 routes. See [Cloudflare replica documentation](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/configure-tunnels/tunnel-availability/deploy-replicas/).

Recommended independent approval wording:

> Approve a dedicated `patch-vigilantes-counter` Cloudflare tunnel for `counter.novatec.casa`, routing only `/counter` to Jetson `127.0.0.1:4319`, its required DNS record, and counter/tunnel boot services. Keep the shared LLM tunnel and its existing routes unchanged.

This is a recommendation, not an approval already granted. If Taylor instead chooses the shared LLM tunnel, first verify its exact live ingress, connector owner, all existing origin targets, and a route-preserving migration plan. Then request approval for that exact plan. Do not reuse the old CNAME target for a new dedicated tunnel; use the actual new tunnel UUID confirmed by Taylor.

Taylor must provision or securely transfer the chosen tunnel's credential directly to the Jetson. The assistant must not retrieve, copy, print, or transmit tunnel secrets; do not put tokens in chat, screenshots, the repository, logs, or command-line arguments. Confirm credential presence/permissions and tunnel identity only, without reading its contents. Configuration management mode must be established before preparing the connector invocation.

## Counter boot service after approval

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
