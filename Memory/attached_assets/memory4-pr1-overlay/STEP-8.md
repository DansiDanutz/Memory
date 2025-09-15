# STEP‑8 — Production Fix Pack (PR‑1) for Memory‑4

This patch delivers a **working Phase‑1 core** (WhatsApp‑only) that replaces placeholder modules (`...`) with production implementations, fixes **secret preview leaks**, and provides a clean webhook.

## What’s in this overlay

**New/Replacement files (drop into your repo root):**
- `app/webhook.py` — FastAPI `APIRouter` for **/webhook** (GET verify + POST inbound). Text + voice flow implemented.
- `app/main.py` — Minimal, production‑safe FastAPI app, mounts webhook + `/metrics` + `/admin/status`.
- `app/security/encryption.py` — Full **Fernet** encryption service with per‑user/per‑tier key derivation and `ENC::` wrapping.
- `app/security/session_store.py` — 10‑minute TTL verification store with optional **Redis** (`REDIS_URL`) fallback to in‑memory.
- `app/voice/azure_voice.py` — Minimal **STT** (`transcribe_wav`) and **TTS** (`synthesize_to_file`) using Azure Speech.
- `app/voice/whatsapp_media.py` — WhatsApp Cloud API media download/upload helpers + OGG/Opus → WAV conversion via ffmpeg.
- `app/memory/storage.py` — **Fixes secret preview leak** (`index.json` now stores no plaintext preview for secret tiers) and writes encrypted body to Markdown as `ENC::<token>` for `SECRET` and `ULTRA_SECRET`.
- `app/memory/search_v2.py` — Simple, reliable Markdown segment search with transparent decrypt for verified sessions (used by webhook). Does **not** rely on your existing `search.py` (which is incomplete).
- `requirements.txt` — Ensures runtime deps are present (FastAPI, Azure Speech, ffmpeg-python, cryptography, redis, etc.).
- `scripts/dev_run.sh` — One‑liner dev runner for Replit.

> This overlay **does not** delete or modify your other files; it simply **adds or replaces** the core modules so the bot runs end‑to‑end today.

## Env vars (set in Replit Secrets)

- `WEBHOOK_VERIFY_TOKEN` — exact string used in WhatsApp webhook config
- `WHATSAPP_ACCESS_TOKEN` — Meta Graph API access token
- `WHATSAPP_PHONE_NUMBER_ID` — Cloud API Phone Number ID
- `AZURE_SPEECH_KEY`, `AZURE_SPEECH_REGION` — Azure Speech
- `ENCRYPTION_MASTER_KEY` — **Fernet** base64 key (generate once)
- `REDIS_URL` — optional (e.g., `redis://localhost:6379/0`), otherwise in‑memory sessions

## Commands in WhatsApp (Phase‑1)

- `enroll: <passphrase>` — store hashed passphrase for your number
- `verify: <passphrase>` — 10‑minute unlock of `SECRET`/`ULTRA_SECRET`
- `search: <query>` — search your memories (allowed tiers)
- Text without `/`/`:` — store memory (auto‑classified)
- **Voice note** — STT → search → reply with **text + voice**

## Acceptance checks

- Secret tiers are **encrypted** in Markdown (`ENC::…`) and **no plaintext previews** are written to `index.json`.
- Without verification, secret tiers are **not** searched.
- Voice in → voice + text out works; webhook **never 5xx** (returns 200 on internal errors).

> After merging this overlay, run `bash scripts/dev_run.sh`, verify the webhook in Meta, and walk the acceptance tests.
