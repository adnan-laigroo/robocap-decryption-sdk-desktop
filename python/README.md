# Robocap Decryption SDK - Python

Python implementation of the Robocap customer-side decryption SDK. It provides:

- A core SDK package for RSA key vault operations and CENC MP4 decryption.
- Customer-facing interactive commands for import, decrypt, and delete flows.
- A FastAPI backend for local/web clients that need the same operations over HTTP.

The shared vault layout, CENC metadata format, and cross-language expectations live in the repository-level [`../spec/`](../spec) directory.

## Requirements

- Python 3.10+
- `ffmpeg` and `ffprobe` on `PATH` for CENC MP4 decrypt operations

## Install

From this repository checkout:

```bash
cd python
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

For development and the full test suite, install both optional extras:

```bash
pip install -e ".[dev,web]"
```

Install only the web dependencies when running the FastAPI backend:

```bash
pip install -e ".[web]"
```

## Package Layout

```text
src/robocap_sdk/       Core SDK: vault layout, RSA import/delete, CENC decrypt
src/robocap_customer/  Interactive customer CLI workflows and batch decrypt
src/robocap_web/       FastAPI app, auth middleware, task store, SSE progress
scripts/               Utility scripts for key generation/import/diagnostics
tests/                 Unit tests for SDK, customer flows, and web endpoints
```

## Core SDK CLI

The `robocap-sdk` command is the lower-level JSON-emitting CLI. It is useful for automation and tests.

```bash
robocap-sdk import-rsa \
  --customer-id frodobot_123 \
  --public-key /path/to/rsa_public_spki.pem \
  --private-key /path/to/rsa_private_pkcs8.pem \
  --rsa-key-version 1

robocap-sdk decrypt-cenc \
  --mp4-path /path/to/encrypted.mp4 \
  --private-key /path/to/user_private.pem \
  --output-dir /path/to/output

robocap-sdk delete-rsa \
  --customer-id frodobot_123 \
  --rsa-key-version 1
```

By default, the core SDK stores its vault under `~/.robocap-sdk`. Override that with `ROBOCAP_SDK_ROOT` or pass `--sdk-root` to the CLI commands.

## Customer Interactive CLIs

These commands are the higher-level customer workflow. They prompt for paths, save customer settings in `{vault}/customer_config.json`, and operate against the vault path you provide.

```text
robocap-customer-import   Import or generate RSA key bundles into a vault
robocap-customer-decrypt  Batch decrypt CENC MP4 files from a session folder
robocap-customer-delete   Delete one imported RSA key version from a vault
```

Use the same vault path for all three commands.

### Key Bundles

A key bundle contains:

```text
rsa_public_spki.pem
rsa_private_pkcs8.pem
user_private.pem          optional; prompted separately when absent
```

`robocap-customer-import` accepts either a directory that directly contains the two RSA PEM files or a parent directory with valid immediate child bundle directories. If no bundle exists, the import flow can generate keys for you.

### Batch Decrypt Behavior

`robocap-customer-decrypt` recursively scans an input directory for encrypted MP4 files, preflights each file, decrypts to the selected output directory, and copies plain `.db` files after all MP4 decrypts succeed. Existing output files are handled through the same skip/overwrite conflict flow used by the API.

## Python API

The public SDK functions are exported from `robocap_sdk`:

```python
from pathlib import Path

from robocap_sdk import decrypt_cenc_mp4, delete_rsa_key_version, import_rsa_key_version
from robocap_sdk.models.key_meta import RsaKeyMeta
```

Main operations:

- `import_rsa_key_version(...)`
- `delete_rsa_key_version(...)`
- `delete_rsa_key_dir(...)`
- `decrypt_cenc_mp4(...)`
- `verify_customer_private_key(...)`

SDK errors are raised as `RobocapError` and include structured error codes for CLI/API callers.

## FastAPI Backend

The `robocap_web` package exposes the same customer workflows over HTTP.

```bash
DEV_MODE=true ROBOCAP_WEB_MODE=local robocap-web
```

Equivalent explicit command:

```bash
DEV_MODE=true ROBOCAP_WEB_MODE=local \
  uvicorn robocap_web.main:app --reload --port 8000
```

Important settings:

| Environment variable | Purpose |
|----------------------|---------|
| `DEV_MODE` | Enables local development behavior, including local browse endpoints |
| `ROBOCAP_WEB_MODE` | `local` by default; non-local mode rejects insecure default secrets |
| `ROBOCAP_DATA_ROOT` | Directory for task JSON state; defaults to `./data` |
| `ROBOCAP_WEB_USER` | Web username; defaults to `frodobot` |
| `ROBOCAP_WEB_PASSWORD` | Web password; default allowed only in local/dev use |
| `ROBOCAP_SESSION_SECRET` | Session signing secret; must be changed outside local/dev use |
| `ROBOCAP_BROWSE_ROOTS` | Semicolon-separated allowed roots for local browsing |

Primary API groups:

```text
GET  /api/health
/api/auth
/api/customers
/api/import
/api/delete
/api/decrypt
/api/local
```

Decrypt tasks run asynchronously and expose task status plus SSE events under `/api/decrypt/tasks/{task_id}`.

This repository does not include a bundled frontend under `python/`; the web package is the backend/API layer.

## Tests

Run the full Python test suite from the `python/` directory:

```bash
pip install -e ".[dev,web]"
pytest
```

The tests cover the core SDK, customer interactive workflows, batch decrypt logic, and FastAPI endpoints.

## Utility Scripts

The `scripts/` directory contains standalone helpers for diagnostics and fixture workflows:

```text
generate_cenc_rsa_2048.py
import_cenc_keys.py
diagnose_cek_unwrap.py
robocap_customer_decrypt.py
```

Prefer the installed console scripts for normal use; keep these scripts for manual verification and troubleshooting.
