# GHED HTTP pilot

Status: prepared for local testing on 2026-09-15. No hosted endpoint is live.
This module is unreleased source, not part of the published 0.6.1 package.

The default `ghed-mcp` command remains a local stdio server with 35 tools.
The optional hosted module exposes 34 read-only tools, the existing resources
and prompt over Streamable HTTP at `/mcp`. `refresh_cache` is neither advertised
nor callable remotely. This pilot has no login: anyone who can reach its URL
can query the public WHO data. Do not use an obscure URL as access control.
Invitation-only use requires a separate compatible OAuth implementation.

## Try locally

From a checkout of `codex/ghed-hosted-pilot`, use a project virtual environment:

```bash
python -m venv .venv
.venv/bin/python -m pip install -e '.[dev,hosted]'
GHED_MCP_CACHE_DIR=/absolute/path/to/pilot-cache \
  .venv/bin/python -m ghed_mcp.hosted --public \
  --public-url http://127.0.0.1:8000
```

Use a separate cache directory to preserve an existing desktop installation's
snapshot. The server prepares the workbook and SQLite database at startup;
it accepts traffic only after that succeeds. Allow several minutes for a cold
start. A restart reuses the cache. Stop the local process with Ctrl+C.

Connect an MCP HTTP client to `http://127.0.0.1:8000/mcp`. A cloud chat client
cannot reach this loopback address. `GET /healthz` returns readiness after
startup. Run `pytest -q` for the synthetic regression suite.

## Pilot limits

- One instance, one web worker and one dedicated query thread. SQLite stays
  on its owning thread; queries run sequentially while HTTP stays responsive.
- At most four running/queued tool or resource queries in total. Capacity stays
  occupied until work finishes, including after client cancellation or timeout.
- A tool waits at most 45 seconds, including queue time. Timeout does not kill
  its underlying computation. Startup preparation allows 15 minutes.
- At most 120 MCP POST requests per minute across all users, including protocol
  discovery. HTTP 429 includes `Retry-After: 60`. This is a shared pilot limit,
  not a per-person allowance or protection against every denial-of-service attack.
- Request bodies: 64 KiB and 10 seconds to arrive. Tool responses: 8 MiB before
  MCP serialization. Queries with `top` accept at most 10,000; larger local
  defaults become 10,000 in hosted schemas. Existing truncation flags apply.
- Streamable HTTP uses stateless JSON responses. GET streams are disabled;
  there are no persistent sessions or unsolicited server notifications.
- Host and Origin allowlists use the configured public origin. No wildcard
  origins or forwarded-IP trust. Cloud clients generally omit Origin headers.
- Responses omit local workbook/database paths, including the export README;
  source URLs, vintage, observation years and dataset signatures remain.
- Application HTTP access logging is disabled. The application does not store
  chat histories or query arguments. Hosting and AI providers apply their own
  logging and retention policies. Do not send confidential text in tool inputs.

These limits are for a small public pilot. Scale and access restrictions must
be designed separately before treating this as a broadly available service.

## Proposed Render deployment

Review billing and public access before creating resources. `render.yaml` is
the concrete deployment recipe: a Python web service in Oregon, `1c-2g` compute
(1 CPU, 2 GB RAM), one instance and a 2 GB disk mounted at `/var/data/ghed`.
The current public workbook and database together occupy roughly 350 MB;
the disk leaves space for rebuilding and a previous snapshot.

Pricing checked 2026-09-15: $25/month compute plus $0.50/month storage, or
**$25.50/month base** on the $0 Hobby workspace plan. Taxes and usage beyond
included bandwidth/build allowances are additional. Confirm the checkout
quote before activation. The 2 GB memory selection is conservative and still
requires measurement on the actual host. [Render pricing](https://render.com/pricing)

1. Sign in to Render and create a Blueprint from this repository and the
   `codex/ghed-hosted-pilot` branch. Inspect the resource and billing summary.
2. Use the supplied configuration. It installs the hosted extra from source,
   uses the persistent cache path and starts the public HTTP mode. The canonical
   origin comes from Render's `RENDER_EXTERNAL_HOSTNAME` environment variable.
3. Approve creation only when ready to start billing and expose the public data
   tools. Wait for startup and a successful `/healthz` response.
4. Record the deployed Git commit, actual HTTPS URL, instance type, observed
   startup memory/time and workbook version. Compare research results against
   the already validated local snapshot.
5. Connect ChatGPT and Claude using the resulting HTTPS URL plus `/mcp`.
   Verify discovery, one comparison, one export and an invalid request in each
   actual client. Account/workspace permissions may require administrator action.
6. Share the URL and quickstart only after those checks pass. Do not claim
   browser-client validation based only on an SDK HTTP test.

Automatic deploys are disabled. A Git push alone does not activate a new
version. Do not add a custom domain until the initial service works. Later,
set `GHED_PUBLIC_URL` to the canonical HTTPS origin and configure that domain
on Render; the MCP path remains `/mcp`.

Persistent disks are available only at runtime, so cache preparation belongs
in startup, not the build command. Disk-backed services run as one instance
and briefly stop during redeployment. This pilot has no high-availability SLA.
[Render disk constraints](https://render.com/docs/disks)

## Data updates and recovery

`check_for_updates` reports whether WHO advertises a different source workbook;
it does not refresh data. The pilot serves its recorded snapshot until an
operator explicitly updates it. No refresh schedule is installed.

For an operator-controlled update, use the Render service shell with its
persistent cache environment. Keep a copy of the current workbook and source
manifest first. Run the existing local `refresh_cache` Python function and
check `version` and a known query afterward. Existing cached downloads and
SQLite rebuilds use file locks and atomic replacement; reads during a rebuild
may wait and time out. Schedule this maintenance outside the pilot session.
Restart the service after validation so it serves the new snapshot consistently.

If an update fails, preserve the failed files for diagnosis. Restore the saved
workbook and matching source manifest, rebuild its derived SQLite cache while
the service is stopped, then restart and verify the version and known values.
For code rollback, manually deploy the previously recorded working Git commit.
Do not delete the persistent disk as part of a code rollback.

## Evidence before sharing

Keep a dated record of local tests, actual MCP HTTP round trips, resource usage,
independent review, deployed commit and both browser-client checks. Public
deployment, billing approval and browser-client checks remain separate from
the local preparation described here.
