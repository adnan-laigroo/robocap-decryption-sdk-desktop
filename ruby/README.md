# Robocap Decryption SDK — Ruby

Offline import of RSA keys and decryption of CENC-encrypted MP4 files.

This is the Ruby implementation. The shared format spec and test fixtures
live one directory up at the monorepo root — see [`../README.md`](../README.md).

## Requirements

- Ruby 3.2+
- OpenSSL 3.x (system or brewed) — required for RSA-OAEP-SHA256
- `ffmpeg` and `ffprobe` on `PATH` (for `decrypt-cenc`)

## Install (from git checkout)

```bash
cd ruby
bundle install
```

## Tests

```bash
bundle exec rake test
```

## CLI

```bash
bundle exec exe/robocap-sdk import-rsa  --help
bundle exec exe/robocap-sdk delete-rsa  --help
bundle exec exe/robocap-sdk decrypt-cenc --help
```

## Verified against the Python SDK

This Ruby gem reads and writes the same on-disk vault and CENC MP4 format
as `python/`. To re-verify byte-compatibility, follow the manual checks
in [`../spec/cross-sdk-verification.md`](../spec/cross-sdk-verification.md).
