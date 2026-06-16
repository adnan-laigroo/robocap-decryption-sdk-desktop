from __future__ import annotations

import json
import logging
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from robocap_decryption_sdk.config import (
    CEK_BYTES,
    RSA_2048_CIPHERTEXT_BYTES,
    RSA_BITS_ALLOWED,
    keys_vault_root,
    validate_customer_id,
)
from robocap_decryption_sdk.crypto import unwrap_key
from robocap_decryption_sdk.errors import ErrorCode, RobocapError
from robocap_decryption_sdk.models.key_meta import RsaKeyMeta
from robocap_decryption_sdk.vault.layout import atomic_write_bytes, atomic_write_text, ensure_private_dir

logger = logging.getLogger(__name__)

_RSA_VERSION_DIR = re.compile(r"^v(\d+)$")


@dataclass(frozen=True)
class CekTrialUnwrapResult:
    cek: bytes
    rsa_key_version: int


class KeyVault:
    def __init__(self, sdk_root: Path) -> None:
        self._sdk_root = sdk_root
        self._keys_root = keys_vault_root(sdk_root)

    @property
    def sdk_root(self) -> Path:
        return self._sdk_root

    def customer_root(self, customer_id: str) -> Path:
        validate_customer_id(customer_id)
        return self._keys_root / customer_id

    def rsa_version_dir(self, customer_id: str, version: int) -> Path:
        return self.customer_root(customer_id) / "rsa" / f"v{version}"

    def public_pem(self, customer_id: str, version: int) -> Path:
        return self.rsa_version_dir(customer_id, version) / "public.pem"

    def private_pem(self, customer_id: str, version: int) -> Path:
        return self.rsa_version_dir(customer_id, version) / "private.pem"

    def rsa_meta_path(self, customer_id: str, version: int) -> Path:
        return self.rsa_version_dir(customer_id, version) / "meta.json"

    def exists_customer(self, customer_id: str) -> bool:
        return self.customer_root(customer_id).is_dir()

    def list_rsa_versions(self, customer_id: str) -> list[int]:
        rsa_dir = self.customer_root(customer_id) / "rsa"
        if not rsa_dir.is_dir():
            return []
        versions: list[int] = []
        for child in rsa_dir.iterdir():
            if not child.is_dir():
                continue
            m = _RSA_VERSION_DIR.match(child.name)
            if m:
                versions.append(int(m.group(1)))
        return sorted(versions)

    def get_latest_rsa_version(self, customer_id: str) -> int:
        versions = self.list_rsa_versions(customer_id)
        if not versions:
            raise RobocapError(
                ErrorCode.ERR_RSA_NOT_IMPORTED,
                f"No RSA keys imported for customer {customer_id}",
            )
        return max(versions)

    def _load_public_key_from_path(self, path: Path) -> rsa.RSAPublicKey:
        data = path.read_bytes()
        key = serialization.load_pem_public_key(data)
        if not isinstance(key, rsa.RSAPublicKey):
            raise RobocapError(
                ErrorCode.ERR_RSA_IMPORT_INVALID,
                "PEM is not an RSA public key",
            )
        return key

    def _load_private_key_from_path(self, path: Path) -> rsa.RSAPrivateKey:
        data = path.read_bytes()
        key = serialization.load_pem_private_key(data, password=None)
        if not isinstance(key, rsa.RSAPrivateKey):
            raise RobocapError(
                ErrorCode.ERR_RSA_IMPORT_INVALID,
                "PEM is not an RSA private key",
            )
        return key

    def get_public_key(self, customer_id: str, version: int) -> rsa.RSAPublicKey:
        path = self.public_pem(customer_id, version)
        if not path.is_file():
            raise RobocapError(
                ErrorCode.ERR_RSA_VERSION_MISSING,
                f"RSA public key v{version} not found for {customer_id}",
            )
        return self._load_public_key_from_path(path)

    def get_private_key(self, customer_id: str, version: int) -> rsa.RSAPrivateKey:
        path = self.private_pem(customer_id, version)
        if not path.is_file():
            raise RobocapError(
                ErrorCode.ERR_RSA_VERSION_MISSING,
                f"RSA private key v{version} not found for {customer_id}",
            )
        return self._load_private_key_from_path(path)

    def get_latest_public_key(self, customer_id: str) -> rsa.RSAPublicKey:
        version = self.get_latest_rsa_version(customer_id)
        return self.get_public_key(customer_id, version)

    def load_rsa_meta(self, customer_id: str, version: int) -> RsaKeyMeta:
        path = self.rsa_meta_path(customer_id, version)
        if not path.is_file():
            raise RobocapError(
                ErrorCode.ERR_RSA_VERSION_MISSING,
                f"RSA meta v{version} not found for {customer_id}",
            )
        return RsaKeyMeta.model_validate_json(path.read_text(encoding="utf-8"))

    def import_rsa_version(
        self,
        customer_id: str,
        public_pem: bytes,
        private_pem: bytes,
        meta: RsaKeyMeta,
    ) -> int:
        validate_customer_id(customer_id)
        version = meta.rsa_key_version
        pub_key = serialization.load_pem_public_key(public_pem)
        priv_key = serialization.load_pem_private_key(private_pem, password=None)
        if not isinstance(pub_key, rsa.RSAPublicKey) or not isinstance(
            priv_key, rsa.RSAPrivateKey
        ):
            raise RobocapError(
                ErrorCode.ERR_RSA_IMPORT_INVALID,
                "Invalid RSA key pair PEM",
            )
        expected_bits = meta.rsa_bits
        if expected_bits not in RSA_BITS_ALLOWED:
            raise RobocapError(
                ErrorCode.ERR_INVALID_RSA_BITS,
                f"RSA rsa_bits must be one of {RSA_BITS_ALLOWED}",
            )
        if pub_key.key_size != expected_bits or priv_key.key_size != expected_bits:
            raise RobocapError(
                ErrorCode.ERR_INVALID_RSA_BITS,
                f"RSA keys must be {expected_bits} bits",
            )
        pub_numbers = pub_key.public_numbers()
        priv_pub = priv_key.public_key().public_numbers()
        if (
            pub_numbers.n != priv_pub.n
            or pub_numbers.e != priv_pub.e
        ):
            raise RobocapError(
                ErrorCode.ERR_RSA_IMPORT_INVALID,
                "Public and private key do not match",
            )

        version_dir = self.rsa_version_dir(customer_id, version)
        if version_dir.exists():
            raise RobocapError(
                ErrorCode.ERR_CUSTOMER_ALREADY_EXISTS,
                f"RSA version v{version} already exists for {customer_id}",
            )
        ensure_private_dir(version_dir)
        atomic_write_bytes(self.public_pem(customer_id, version), public_pem)
        atomic_write_bytes(self.private_pem(customer_id, version), private_pem)
        atomic_write_text(
            self.rsa_meta_path(customer_id, version),
            meta.model_dump_json(indent=2),
        )
        ensure_private_dir(self.customer_root(customer_id))
        return version

    def delete_rsa_version(self, customer_id: str, version: int) -> None:
        validate_customer_id(customer_id)
        if not self.exists_customer(customer_id):
            raise RobocapError(
                ErrorCode.ERR_CUSTOMER_NOT_FOUND,
                f"Customer not found: {customer_id}",
            )
        version_dir = self.rsa_version_dir(customer_id, version)
        if not version_dir.is_dir():
            raise RobocapError(
                ErrorCode.ERR_RSA_VERSION_MISSING,
                f"RSA version v{version} not found for {customer_id}",
            )
        try:
            shutil.rmtree(version_dir)
        except OSError as exc:
            raise RobocapError(
                ErrorCode.ERR_VAULT_IO,
                f"Failed to delete RSA version v{version}: {exc}",
            ) from exc

    def _is_valid_rsa_key_dir(self, path: Path) -> bool:
        return (
            path.is_dir()
            and self.public_pem_path_for_dir(path).is_file()
            and self.private_pem_path_for_dir(path).is_file()
        )

    @staticmethod
    def public_pem_path_for_dir(key_dir: Path) -> Path:
        return key_dir / "public.pem"

    @staticmethod
    def private_pem_path_for_dir(key_dir: Path) -> Path:
        return key_dir / "private.pem"

    def rsa_dir(self, customer_id: str) -> Path:
        return self.customer_root(customer_id) / "rsa"

    def list_rsa_key_dirs(self, customer_id: str) -> list[Path]:
        validate_customer_id(customer_id)
        rsa_dir = self.rsa_dir(customer_id)
        if not rsa_dir.is_dir():
            return []
        key_dirs: list[Path] = []
        for child in sorted(rsa_dir.iterdir(), key=lambda p: p.name.lower()):
            if child.is_dir() and self._is_valid_rsa_key_dir(child):
                key_dirs.append(child.resolve())
        return key_dirs

    def delete_rsa_key_dir(self, customer_id: str, key_dir: Path) -> None:
        validate_customer_id(customer_id)
        if not self.exists_customer(customer_id):
            raise RobocapError(
                ErrorCode.ERR_CUSTOMER_NOT_FOUND,
                f"Customer not found: {customer_id}",
            )
        rsa_dir = self.rsa_dir(customer_id).resolve()
        resolved = key_dir.expanduser().resolve()
        if resolved.parent != rsa_dir:
            raise RobocapError(
                ErrorCode.ERR_RSA_VERSION_MISSING,
                f"Key folder is not under rsa/ for {customer_id}",
            )
        if not self._is_valid_rsa_key_dir(resolved):
            raise RobocapError(
                ErrorCode.ERR_RSA_VERSION_MISSING,
                f"Key folder missing public.pem or private.pem: {resolved.name}",
            )
        try:
            shutil.rmtree(resolved)
        except OSError as exc:
            raise RobocapError(
                ErrorCode.ERR_VAULT_IO,
                f"Failed to delete key folder {resolved.name}: {exc}",
            ) from exc

    def trial_unwrap_cek(
        self,
        customer_id: str,
        cek_wrapped: bytes,
    ) -> CekTrialUnwrapResult:
        """Try each 2048-bit RSA version in ascending order to unwrap the CEK."""
        validate_customer_id(customer_id)
        if len(cek_wrapped) != RSA_2048_CIPHERTEXT_BYTES:
            raise RobocapError(
                ErrorCode.ERR_CENC_CEKA_WRAP,
                f"Wrapped CEK must be {RSA_2048_CIPHERTEXT_BYTES} bytes",
            )

        eligible: list[tuple[int, rsa.RSAPrivateKey]] = []
        for version in self.list_rsa_versions(customer_id):
            meta = self.load_rsa_meta(customer_id, version)
            if meta.rsa_bits != 2048:
                continue
            private_key = self.get_private_key(customer_id, version)
            if private_key.key_size != 2048:
                continue
            eligible.append((version, private_key))

        if not eligible:
            raise RobocapError(
                ErrorCode.ERR_CENC_CEKA_TRIAL_FAILED,
                f"No 2048-bit RSA keys available for trial unwrap: {customer_id}",
            )

        first_success: CekTrialUnwrapResult | None = None
        for version, private_key in eligible:
            try:
                cek = unwrap_key(
                    cek_wrapped,
                    private_key,
                    plain_len=CEK_BYTES,
                    cipher_len=RSA_2048_CIPHERTEXT_BYTES,
                    decode_error=ErrorCode.ERR_CENC_CEKA_WRAP,
                    length_error=ErrorCode.ERR_CENC_CEKA_LENGTH,
                )
            except RobocapError:
                continue
            if first_success is not None:
                logger.warning(
                    "Multiple RSA versions decrypted same CEK; using first success v%s",
                    first_success.rsa_key_version,
                )
                return first_success
            first_success = CekTrialUnwrapResult(cek=cek, rsa_key_version=version)

        if first_success is None:
            raise RobocapError(
                ErrorCode.ERR_CENC_CEKA_TRIAL_FAILED,
                f"CEK trial unwrap failed for all vault versions: {customer_id}",
            )
        return first_success
