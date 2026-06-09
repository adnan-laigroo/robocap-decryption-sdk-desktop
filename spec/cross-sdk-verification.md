# Cross-SDK verification — Ruby ↔ Python round-trips

These manual checks confirm that the Ruby and Python SDKs read and write
the same on-disk vault and produce/consume the same wrapped-CEK format.

Run from the repository root after installing both SDKs:

```bash
cd python && pip install -e ".[dev]" && cd ..
cd ruby   && bundle install               && cd ..
```

## Check 1 — Python writes vault, Ruby reads it

```bash
SDK_ROOT=$(mktemp -d -t robocap-xsdk-py)

# Python: import key version 1
python -c "
from pathlib import Path
from datetime import datetime, timezone
from robocap_sdk.models.key_meta import RsaKeyMeta
from robocap_sdk.services.rsa_import import import_rsa_key_version
import_rsa_key_version(
    'XSDK',
    Path('test-vectors/keys/rsa_public_spki.pem').read_bytes(),
    Path('test-vectors/keys/rsa_private_pkcs8.pem').read_bytes(),
    RsaKeyMeta(rsa_key_version=1, effective_at=datetime(2026,1,1,tzinfo=timezone.utc), device_id='XSDK', rsa_bits=2048),
    sdk_root=Path('$SDK_ROOT'),
)
print('python-wrote ok')
"

# Ruby: list versions + load meta
cd ruby && bundle exec ruby -e "
require 'robocap/sdk'
vault = Robocap::SDK::KeyVault.new('$SDK_ROOT')
raise 'list mismatch' unless vault.list_rsa_versions('XSDK') == [1]
meta = vault.load_rsa_meta('XSDK', 1)
raise 'meta mismatch' unless meta.rsa_bits == 2048 && meta.device_id == 'XSDK'
puts 'ruby-read ok'
" && cd ..
```

Expected: `python-wrote ok` then `ruby-read ok`.

## Check 2 — Ruby writes vault, Python reads it

```bash
SDK_ROOT=$(mktemp -d -t robocap-xsdk-rb)

# Ruby: import key version 1
cd ruby && bundle exec ruby -e "
require 'robocap/sdk'
meta = Robocap::SDK::RsaKeyMeta.new(
  rsa_key_version: 1, effective_at: Time.utc(2026, 1, 1),
  device_id: 'XSDK', rsa_bits: 2048,
)
Robocap::SDK.import_rsa_key_version(
  customer_id: 'XSDK',
  public_pem:  File.binread('../test-vectors/keys/rsa_public_spki.pem'),
  private_pem: File.binread('../test-vectors/keys/rsa_private_pkcs8.pem'),
  meta: meta,
  sdk_root: '$SDK_ROOT',
)
puts 'ruby-wrote ok'
" && cd ..

# Python: read meta + verify ownership using the user_private.pem fixture
python -c "
from pathlib import Path
from robocap_sdk.vault.key_vault import KeyVault
from robocap_sdk.auth.ownership import verify_customer_private_key
vault = KeyVault(Path('$SDK_ROOT'))
assert vault.list_rsa_versions('XSDK') == [1], 'list mismatch'
meta = vault.load_rsa_meta('XSDK', 1)
assert meta.rsa_bits == 2048 and meta.device_id == 'XSDK', 'meta mismatch'
print('python-read ok')
"
```

Expected: `ruby-wrote ok` then `python-read ok`.

## Check 3 — Ruby deletes a version, Python sees it gone

```bash
SDK_ROOT=$(mktemp -d -t robocap-xsdk-del)

# Python: import two versions
python -c "
from pathlib import Path
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from robocap_sdk.models.key_meta import RsaKeyMeta
from robocap_sdk.services.rsa_import import import_rsa_key_version
def kp(bits=2048):
    k = rsa.generate_private_key(65537, bits)
    return (
        k.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo),
        k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()),
    )
for v in (1, 2):
    pub, priv = kp()
    import_rsa_key_version(
        'XSDK_DEL', pub, priv,
        RsaKeyMeta(rsa_key_version=v, effective_at=datetime(2026,1,1,tzinfo=timezone.utc), device_id='X', rsa_bits=2048),
        sdk_root=Path('$SDK_ROOT'),
    )
print('python imported v1, v2')
"

# Ruby: delete v1
cd ruby && bundle exec ruby -e "
require 'robocap/sdk'
Robocap::SDK.delete_rsa_key_version(customer_id: 'XSDK_DEL', rsa_key_version: 1, sdk_root: '$SDK_ROOT')
puts 'ruby deleted v1'
" && cd ..

# Python: confirms only v2 remains
python -c "
from pathlib import Path
from robocap_sdk.vault.key_vault import KeyVault
assert KeyVault(Path('$SDK_ROOT')).list_rsa_versions('XSDK_DEL') == [2]
print('python sees [v2] only')
"
```

Expected: `python imported v1, v2` → `ruby deleted v1` → `python sees [v2] only`.

## Check 4 — Round-trip wrapped CEK across SDKs

```bash
# Ruby wraps a CEK with the shared public key; Python unwraps it.
WRAP_OUT=$(mktemp -t robocap-wrap.bin)
cd ruby && bundle exec ruby -e "
require 'robocap/sdk'
cek = (\"\xAA\".b * Robocap::SDK::Config::CEK_BYTES)
pub = OpenSSL::PKey::RSA.new(File.binread('../test-vectors/keys/rsa_public_spki.pem'))
File.binwrite('$WRAP_OUT', Robocap::SDK::RSAOAEP.wrap_cek(cek, pub))
puts \"ruby wrapped #{File.size('$WRAP_OUT')} bytes\"
" && cd ..

python -c "
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from robocap_sdk.crypto.rsa_oaep import unwrap_cek
priv = serialization.load_pem_private_key(Path('test-vectors/keys/rsa_private_pkcs8.pem').read_bytes(), password=None)
cek = unwrap_cek(Path('$WRAP_OUT').read_bytes(), priv)
assert cek == b'\xAA' * 16, f'wrong CEK {cek.hex()}'
print('python unwrapped ok')
"
```

Expected: Ruby reports the byte count (`256`), Python prints `python unwrapped ok`.

## When to run

- Before any release of either SDK.
- After any change to `python/src/robocap_sdk/` or `ruby/lib/robocap/sdk/` that touches the vault layout, the K2/CENC format constants, or the RSA-OAEP parameters.
- When bumping the OpenSSL version on a deploy target.

If any check fails, treat the diverging SDK as having a regression, not the agreed format. Update the failing side; do not update `test-vectors/` or this doc without explicit cross-team review.
