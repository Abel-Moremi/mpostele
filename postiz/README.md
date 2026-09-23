# Postiz (local, self-hosted)

A lightweight, 3-container Postiz stack (app + Postgres + Redis), pinned to
**v2.11.3** — the last release before Postiz made Temporal + Elasticsearch a
hard dependency. See
[docs-mpostele/03 Workflow/05 Platform Adaptation & Export.md](../docs-mpostele/03%20Workflow/05%20Platform%20Adaptation%20%26%20Export.md)
for why.

Meant to be left running in the background (like `ollama serve`), not
started/stopped around each post — Postiz's own scheduler needs to be alive
continuously to fire posts at their scheduled time.

## First-time setup

1. Copy the env template and fill in a secret:

   ```bash
   cp .env.example .env
   # then edit .env: set POSTIZ_JWT_SECRET to a random string, e.g.
   openssl rand -hex 32
   ```

2. Start the stack (from this directory):

   ```bash
   docker compose up -d
   ```

3. Open http://localhost:4007, create your account, and connect the social
   accounts you want to post to (TikTok/Instagram/X/LinkedIn). Connecting an
   account needs its own developer app credentials in `.env` first — see
   the comments in `.env.example` for where to register each one.

4. Generate a Public API key from Postiz's own settings/API page.

5. List your connected accounts to get their integration IDs:

   ```bash
   curl -H "Authorization: <your API key>" http://localhost:4007/api/public/v1/integrations
   ```

6. Set these in mpostele's own environment (see `app/config/settings.py`),
   not here:

   - `POSTIZ_API_URL=http://localhost:4007/api/public/v1`
   - `POSTIZ_API_KEY=<the key from step 4>`
   - `POSTIZ_INTEGRATION_TIKTOK` / `_INSTAGRAM` / `_X` / `_LINKEDIN` = the
     matching integration IDs from step 5

## Day to day

- `docker compose up -d` — start (idempotent; safe to leave running)
- `docker compose down` — stop
- `docker compose logs -f postiz` — tail logs
- `docker compose down` then edit `.env` then `docker compose up -d` —
  required after changing any environment variable

## Why v2.11.3, not `:latest`

`ghcr.io/gitroomhq/postiz-app:latest` today pulls in Temporal (a workflow
engine) and, underneath it, Elasticsearch — 8 containers total, commonly
2-4GB+ RAM just to idle. v2.11.3 is the last tag before that, at 3
containers, and was documented as tested on a 2GB RAM / 2 vCPU VM. The
Public API endpoints `publish_engine.py` calls (`/upload`, `/posts`,
`/integrations`) already existed at this version — confirmed directly
against the v2.11.3 source, not just the current docs (which describe the
newer release).
