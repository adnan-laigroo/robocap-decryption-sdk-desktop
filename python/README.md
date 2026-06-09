# Robocap CENC Decrypt SDK

Offline tools to import 2048-bit keys into a local **vault**, optionally remove one vault version, and batch-decrypt **CENC MP4** files. All customer commands use **English** interactive prompts.

---

## Install

```bash
cd ~/robocap_sdk
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Requires **Python 3.10+** and **ffmpeg / ffprobe** on your PATH.

---

## Before you start

| Concept | Meaning |
|---------|---------|
| **Vault path** | Any folder you choose (e.g. `~/robocap-vault`). Same path for import, delete, and decrypt. Created automatically on first **import** if missing. |
| **Key bundle** | A folder with `rsa_public_spki.pem` + `rsa_private_pkcs8.pem` (optional `user_private.pem`). Usually under `~/keys/`. |
| **Vault version (v1, v2, …)** | A copy of a key bundle already **imported** into `{vault}/vault/keys/{customer_id}/rsa/vN/`. Assigned automatically on import. |

Settings are saved in `{vault}/customer_config.json` (vault path, customer ID, user private key path).

---

## Typical flow

```text
1. robocap-customer-import     → load keys into vault (once per new key bundle)
2. robocap-customer-decrypt    → decrypt session folders
3. robocap-customer-delete     → optional; remove a mistaken vault version only
```

---

## 1. Import keys — `robocap-customer-import`

```bash
robocap-customer-import
```

| Prompt | What to enter |
|--------|----------------|
| Vault path | e.g. `~/robocap-vault` (any name you prefer) |
| Customer ID | e.g. `frodobot_123` |
| Key bundle directory | See rules below |
| User private key PEM path | **Skipped** if the bundle contains `user_private.pem` |

**Key bundle directory — how the tool resolves your path**

1. **Folder does not exist** → create it → ask to generate keys (`Y/n`).
2. **Folder itself contains both PEM files** → import from that folder directly.
3. **Otherwise** → scan **immediate subfolders** only (not deeper levels):
   - **0** valid subfolders → ask to generate keys in this folder.
   - **1** valid subfolder → use it automatically (`Using key bundle: …`).
   - **2+** valid subfolders → numbered menu (`Select bundle [1]:`).

A valid subfolder must contain `rsa_public_spki.pem` and `rsa_private_pkcs8.pem`.  
If `~/keys/` has PEM files at the **root**, the tool treats `~/keys` as one bundle and **will not** scan subfolders — use a specific subfolder path (e.g. `~/keys/frodobot_123_v7`) or a parent folder without root PEMs.

Each successful import adds the next vault version automatically (v1, then v2, …).

---

## 2. Delete one vault version — `robocap-customer-delete`

Removes **one** key folder under `{vault}/vault/keys/{customer_id}/rsa/`. Vault must already exist.

```bash
robocap-customer-delete
```

| Prompt | What to enter |
|--------|----------------|
| Vault path | Same as import |
| Customer ID | e.g. `frodobot_123` |
| Key version folders found | e.g. `frodobot_123/rsa/v1`, `frodobot_123/rsa/v2` |
| Select folder to delete `[1]` | Pick by number |
| Type yes to delete `{customer}/rsa/{folder}` | `yes` to confirm |

Folders listed must contain vault `public.pem` and `private.pem` (any folder name, not only `v1`, `v2`). Does not scan `~/keys/`.

**Do not delete** older vault folders still needed to decrypt OTA videos. Use delete only for mistaken imports or test cleanup.

---

## 3. Decrypt videos — `robocap-customer-decrypt`

Batch-decrypts CENC MP4 files under a folder (recursive scan, preflight on first file).

```bash
robocap-customer-decrypt
```

| Prompt | What to enter |
|--------|----------------|
| Vault path | Same as import |
| User private key PEM path | e.g. `~/keys/.../user_private.pem` (default from config if saved) |
| Encrypted input directory | Folder with encrypted MP4s |
| Decrypted output directory | e.g. `~/out/session3` (created if needed) |

Customer ID is read from each MP4 automatically — you do not type it here.

After all MP4s decrypt successfully, plain `.db` files from the input session (excluding `*.db.enc`) are copied into the output directory with the same folder layout. Output conflicts use the same Skip/Overwrite menu as MP4s.

Play output: `ffplay ~/out/session3/clip.mp4` — use a **file** path, not the folder alone.

---

## Quick reference

| Command | Purpose |
|---------|---------|
| `robocap-customer-import` | Keys → vault (auto version, optional generate / bundle pick) |
| `robocap-customer-decrypt` | Encrypted MP4 folder → plain MP4 folder |
| `robocap-customer-delete` | Remove one `vN` from vault (confirm with `yes`) |

Use the **same vault path** for all three commands.

---

## M1 Web MVP (local)

Browser UI for import, delete, and decrypt on the same machine. Requires **Node.js 18+** for the frontend.

**完整本地配置、启动、路径与排错说明见：** [docs/local-web-readme.md](docs/local-web-readme.md)

### Quick start (Windows CMD)

**Terminal 1 — backend:**

```cmd
cd C:\Users\Administrator\Desktop\robocap加密sdk
.venv\Scripts\activate.bat
set DEV_MODE=true
set ROBOCAP_WEB_MODE=local
pip install -e ".[web]"
uvicorn robocap_web.main:app --reload --port 8000
```

**Terminal 2 — frontend:**

```cmd
cd web
npm install
npm run dev
```

Open **`http://localhost:5173/`** (prefer `localhost` over `127.0.0.1` on Windows).

| Setting | M1 default |
|---------|------------|
| `DEV_MODE=true` | Auto-login as `dev`; local path browse enabled |
| `ROBOCAP_WEB_MODE=local` | Vault/bundle paths on local disk |
| `ROBOCAP_DATA_ROOT` | Task JSON store (default `./data`) |

Decrypt runs asynchronously with SSE progress. Import and delete are synchronous API calls equivalent to the CLI commands above.
