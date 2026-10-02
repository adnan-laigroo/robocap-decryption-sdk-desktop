# Robocap Decryptor

[![CI](https://github.com/frodobots-org/robocap-decryption-sdk/actions/workflows/ci.yml/badge.svg)](https://github.com/frodobots-org/robocap-decryption-sdk/actions/workflows/ci.yml)

The desktop GUI is the easiest way to bulk-decrypt Robocap MP4 files. This repository includes the GUI, its build workflow, and the SDK it uses underneath.

Start with the [desktop app guide](./python/UI/README.md) for downloads, build commands, and step-by-step instructions.

## Quick start: bulk decrypt in the GUI

1. Download the macOS or Windows build from the **Build Robocap Decryptor** workflow artifact. If no artifact is available yet, run that workflow from the Actions tab or follow the local build commands in the app guide.
2. Open the app and select the folder containing your device key pairs. Keep each public and private PEM pair together.
3. Click **Import Keys**.
4. Select the folder containing your MP4 files.
5. Select a separate output folder **outside** the input folder.
6. Choose the worker count and click **Start Decryption**. Follow progress and the final summary in the app log.

The app reads device and key-version information from each MP4's tags and uses the matching SDK vault key. You do not need to use a terminal or run SDK commands. Your private keys are not bundled with the app; the GUI imports them into the local SDK vault.

The [desktop app guide](./python/UI/README.md) includes install/use steps and exact commands to create the macOS `.dmg` and Windows `.exe`.

## SDK source

The desktop app packages the Python SDK as its decryption engine. The repository also contains a Ruby implementation. The wire format, vault layout, and error codes live in [`spec/`](./spec) and are the shared source of truth.

## Implementations

| Language | Location | Status |
|----------|----------|--------|
| Python   | [`python/`](./python) | Stable — see [`python/README.md`](./python/README.md) |
| Ruby     | [`ruby/`](./ruby) | Ready — see [`ruby/README.md`](./ruby/README.md) |

## Repository layout

```
spec/             Format spec & error taxonomy — language-agnostic source of truth
test-vectors/     Shared fixtures: sample RSA keys, encrypted samples, expected outputs
python/           Python SDK (pyproject.toml, src/, tests/, scripts/)
ruby/             Ruby SDK (gemspec, lib/, test/)
robocap-vault/    Sample on-disk vault (language-agnostic runtime artifact)
```

Every SDK is expected to pass against the same fixtures under
[`test-vectors/`](./test-vectors). A change to the binary format requires
updating `spec/` and both SDKs in the same PR.

## Working in a single SDK

```bash
# Python
cd python && pip install -e ".[dev,web]" && pytest

# Ruby
cd ruby && bundle install && bundle exec rake test
```

## Security note

The keys under `test-vectors/` and `robocap-vault/` are **test fixtures only**.
Never use them in production.
