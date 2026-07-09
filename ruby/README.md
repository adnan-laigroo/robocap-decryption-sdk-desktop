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
bundle exec exe/robocap-decryption-sdk import-rsa  --help
bundle exec exe/robocap-decryption-sdk delete-rsa  --help
bundle exec exe/robocap-decryption-sdk decrypt-cenc --help
```

## Ruby API

```ruby
require 'robocap/sdk'

RobocapCenc::SDK.decrypt_cenc_mp4(...)
```

## Changelog

### 2.0.0

BREAKING: Ruby namespace renamed `Robocap::SDK` -> `RobocapCenc::SDK` to avoid colliding with host apps that define a top-level `Robocap` constant. Gem name, require path, and CLI executable are unchanged. Ruby API consumers must update `Robocap::SDK::*` references to `RobocapCenc::SDK::*`.

## Verified against the Python SDK

This Ruby gem reads and writes the same on-disk vault and CENC MP4 format
as `python/`. To re-verify byte-compatibility, follow the manual checks
in [`../spec/cross-sdk-verification.md`](../spec/cross-sdk-verification.md).
