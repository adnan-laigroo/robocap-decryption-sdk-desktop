# Robocap CENC — Format Specification

Language-agnostic source of truth for the on-disk and on-wire formats every
Robocap SDK implements. When the format changes, this directory and the
fixtures under `../test-vectors/` move in the same PR as the SDK
implementations.

## Documents

- `cenc-format.md` — CENC-encrypted MP4 binary layout, RSA-OAEP parameters,
  AES-CTR scheme, and CEK wrapping rules. *(TODO — extract from current Python
  implementation.)*
- `vault-layout.md` — on-disk vault structure: directory tree, file naming,
  metadata schema. *(TODO.)*
- `error-codes.md` — shared error taxonomy each SDK must surface to callers.
  *(TODO.)*

Until each spec document is written, the authoritative reference is the
Python implementation under `../python/src/robocap_decryption_sdk/`.
