# Robocap Decryption SDK

[![CI](https://github.com/frodobots-org/robocap-decryption-sdk/actions/workflows/ci.yml/badge.svg)](https://github.com/frodobots-org/robocap-decryption-sdk/actions/workflows/ci.yml)

Offline SDKs for importing RSA keys into a local vault and decrypting **CENC-encrypted MP4** files.

This repository hosts multiple language ports of the same SDK. The wire format,
vault layout, and error codes live in [`spec/`](./spec) and are the source of
truth for every implementation.

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
