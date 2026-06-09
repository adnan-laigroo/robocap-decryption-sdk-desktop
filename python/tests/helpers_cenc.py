from __future__ import annotations

import base64
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import serialization

from robocap_sdk.config import CEK_BYTES
from robocap_sdk.crypto.rsa_oaep import wrap_key
from robocap_sdk.models.key_meta import RsaKeyMeta
from robocap_sdk.services.rsa_import import import_rsa_key_version

EMBEDDED_CENC_PUBLIC_PEM = b"""-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0VO2bntFtlrbEmP84IJ4
qQ6FubUCe1NLVg4WSD5NAYB4EwNDqMzjCiPOUBhCC7axzy7Vpufp310KMmpLldD6
tbPQqPO9aMtYfMIdYXnOMe84QVBs5DUEO/ExUCTxqjjCh5pwswZK6qoAXKAlQ3jo
maEFxvEsBidmgfxt35idbzKje3Uhv1t233SEP/xmYys/mJZfM40S9+E6XM6KK84e
KJXiQf0dbNdQhL9AJfDF+2BZu/JMrQT5OQPDy6X3GNgpDvoHHstDC4gDCy2B8uFZ
opvO4FCmIUNfWwSVZcdE4JGKa3Y0F1JptHoSz1evYJ4JYaAnaUWP8SzqY2yOfFdT
3wIDAQAB
-----END PUBLIC KEY-----
"""

EMBEDDED_CENC_PRIVATE_PEM = b"""-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDRU7Zue0W2WtsS
Y/zggnipDoW5tQJ7U0tWDhZIPk0BgHgTA0OozOMKI85QGEILtrHPLtWm5+nfXQoy
akuV0Pq1s9Co871oy1h8wh1hec4x7zhBUGzkNQQ78TFQJPGqOMKHmnCzBkrqqgBc
oCVDeOiZoQXG8SwGJ2aB/G3fmJ1vMqN7dSG/W3bfdIQ//GZjKz+Yll8zjRL34Tpc
zoorzh4oleJB/R1s11CEv0Al8MX7YFm78kytBPk5A8PLpfcY2CkO+gcey0MLiAML
LYHy4Vmim87gUKYhQ19bBJVlx0TgkYprdjQXUmm0ehLPV69gnglhoCdpRY/xLOpj
bI58V1PfAgMBAAECggEAFVIXTvR7sBcGoOkR7NTNMRGbbu6wCdtSMo8tF376UptW
X5Vhsv6UvMfTL+xF7zHUtYYPLo4I5P5x10W6siU+y/q8gjY6m225cxJFx35ju/P3
gQuN3nFEn6MG7fioAWRWR//j17rd2ZNRhchX/fcsNdhP9tNCCSnCh/Mr8RjMfEf3
EceuRxS3v4M7s0FfB1wWmztaiQ7PotLJRTXtevAKjMDfgp+DxhgGLRwPPMeEKewx
8gLQMpx8AV+iDz2MPQqAVvojwWp3Ysoygg0ke7mxDg+ym2gQMMvs9MDNIZG6gUNP
Aw2oTn4CdZ4Zix4YgNkykbv5XzGp+HOzwy7AU4XzqQKBgQDy3DKCq6i9nKrmMo7G
BY2w1LXZp1vz37dwe3vPKpcQ228b3MwhB8zECj9Ra859gt0YchacrvSNUeNTE14W
KyR/gRKIY6N4cEfH7T68SXYOtybS4ZUYHTPoiBZ+HlrngkJ9wqutQkqK2KILi9cG
HaIXoYhmWzd6YGtT7mrbz12vFwKBgQDcpw4ajrWgMIogGFe/v0jrCDHVvkCZ+pw8
ywBqUbaThNi7sGc+cAEsoKmu/mVCUvqSBBz3QG4devO+ooz+mJkQYyF8W4mh+FNq
CvFxTQMGQVQD30jbDKcqP8X8i/56xW+HV+o5DOVrmjkM7MdtVxdznb9qKFsp5Ltq
8h0hpZg+eQKBgQCJ5miz8/77s6MC1UBmxq5+8zlTHonC/4wszaEusDNZOhBsFMLA
Gqq1wk/TztBQSmd6wwV98IYiXJYlDQFGuzadQ9AfK9ydvbu0lU0jIt9rWaos4jSD
nclkxylmcZwSis9wk4Jh/htPndTdk4kECv2IR4uo+zCUR32KCf4ZVDUQ/wKBgEeg
SunADaFUYGIOxN1PoMH6xQKXYa0aNwFc/GOG5vd4FkrG9pzECv2LoclWd1RST1h6
0VRJq/UR5nGpno8+xeEV7NbLeCAF1j4EE2AuGZ88MaOYJbRFpTYHwaM7Zn4//PY4
SaX/U7HcPEy/x/TsYoZ7XJl/RCiTQWtz8JTthkAxAoGBAOunl5ArkBEeqPshtNP+
Ix/7NgxFat/lOTWcw2TaXMIMDcMchIvpEGJMggCuCuTat3ogUKO3pGBXvTzEj5bb
KoI0GRqzrN4lhSQBy9YDhs262xnseE+uz2tLqQlwqOqhUZFxOpvJ4VIRxAOzXCzl
Crtz8iuJ9NCC3lz3SVR7z/8H
-----END PRIVATE KEY-----
"""


def build_cenc_tag_payload(
    public_pem: bytes,
    private_pem: bytes,
    *,
    customer_id: str = "CENC_CUST",
) -> dict[str, str]:
    public_key = serialization.load_pem_public_key(public_pem)
    cek = b"\x01" * CEK_BYTES
    wrapped = wrap_key(cek, public_key, plain_len=CEK_BYTES)
    return {
        "cenc_customer_id": customer_id,
        "cenc_cek_wrapped_b64": base64.b64encode(wrapped).decode("ascii"),
        "cenc_kid_hex": "00" * 32,
    }


def import_cenc_rsa_vN(
    sdk_root: Path,
    customer_id: str,
    public_pem: bytes,
    private_pem: bytes,
    version: int,
    *,
    rsa_bits: int = 2048,
) -> None:
    import_rsa_key_version(
        customer_id,
        public_pem,
        private_pem,
        RsaKeyMeta(
            rsa_key_version=version,
            effective_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            device_id=customer_id,
            rsa_bits=rsa_bits,
        ),
        sdk_root=sdk_root,
    )


def import_cenc_rsa_v1(
    sdk_root: Path,
    customer_id: str,
    public_pem: bytes,
    private_pem: bytes,
) -> None:
    import_cenc_rsa_vN(sdk_root, customer_id, public_pem, private_pem, 1)
