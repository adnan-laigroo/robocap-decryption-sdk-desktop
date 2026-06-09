from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from robocap_sdk.config import validate_customer_id

from robocap_customer.error_mapper import (
    MSG_BUNDLE_MISSING,
    MSG_INVALID_CUSTOMER_ID,
    MSG_INVALID_KEY,
    CustomerFacingError,
)

PUBLIC_PEM_NAME = "rsa_public_spki.pem"
PRIVATE_PEM_NAME = "rsa_private_pkcs8.pem"
USER_PRIVATE_PEM_NAME = "user_private.pem"
CENC_RSA_BITS = 2048
GENERATED_FILE_NAMES = (
    PUBLIC_PEM_NAME,
    PRIVATE_PEM_NAME,
    USER_PRIVATE_PEM_NAME,
)


@dataclass(frozen=True)
class KeyBundleFiles:
    bundle_dir: Path
    public_pem_path: Path
    private_pem_path: Path
    public_pem: bytes
    private_pem: bytes


def is_valid_bundle_dir(path: Path) -> bool:
    root = path.expanduser().resolve()
    if not root.is_dir():
        return False
    return (root / PUBLIC_PEM_NAME).is_file() and (root / PRIVATE_PEM_NAME).is_file()


def discover_child_bundles(parent: Path) -> list[Path]:
    root = parent.expanduser().resolve()
    if not root.is_dir():
        return []
    bundles: list[Path] = []
    for child in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if child.is_dir() and is_valid_bundle_dir(child):
            bundles.append(child.resolve())
    return bundles


class BundlePathKind(Enum):
    DIRECT = "direct"
    SINGLE_CHILD = "single_child"
    MULTIPLE_CHILDREN = "multiple_children"
    EMPTY = "empty"


@dataclass(frozen=True)
class BundlePathAnalysis:
    kind: BundlePathKind
    path: Path
    candidates: tuple[Path, ...] = ()


def analyze_bundle_path(path: Path) -> BundlePathAnalysis:
    expanded = path.expanduser()
    if not expanded.exists():
        return BundlePathAnalysis(BundlePathKind.EMPTY, expanded)
    resolved = expanded.resolve()
    if is_valid_bundle_dir(resolved):
        return BundlePathAnalysis(BundlePathKind.DIRECT, resolved)
    children = discover_child_bundles(resolved)
    if len(children) == 1:
        return BundlePathAnalysis(BundlePathKind.SINGLE_CHILD, children[0])
    if len(children) > 1:
        return BundlePathAnalysis(
            BundlePathKind.MULTIPLE_CHILDREN,
            resolved,
            tuple(children),
        )
    return BundlePathAnalysis(BundlePathKind.EMPTY, resolved)


def next_version_subdir_name(parent: Path, *, prefix: str = "v") -> str:
    """Return the next unused vN folder name under parent (e.g. v1, v2)."""
    root = parent.expanduser().resolve()
    max_n = 0
    if root.is_dir():
        for child in root.iterdir():
            if not child.is_dir():
                continue
            name = child.name
            if name.startswith(prefix) and name[len(prefix) :].isdigit():
                max_n = max(max_n, int(name[len(prefix) :]))
    return f"{prefix}{max_n + 1}"


def resolve_key_generate_dir(parent: Path, layout: str) -> Path:
    """Resolve output directory for key generation."""
    root = parent.expanduser().resolve()
    if layout == "direct":
        return root
    if layout == "subfolder":
        target = root / next_version_subdir_name(root)
        target.mkdir(parents=True, exist_ok=False)
        return target.resolve()
    raise ValueError(f"Unknown layout: {layout}")


def default_user_private_path(bundle_dir: Path) -> Path | None:
    candidate = bundle_dir / USER_PRIVATE_PEM_NAME
    if candidate.is_file():
        return candidate.resolve()
    return None


def validate_customer_id_input(customer_id: str) -> None:
    normalized = customer_id.strip()
    try:
        validate_customer_id(normalized)
    except ValueError as exc:
        raise CustomerFacingError(MSG_INVALID_CUSTOMER_ID) from exc


def load_key_bundle(bundle_dir: Path) -> KeyBundleFiles:
    root = bundle_dir.expanduser().resolve()
    if not root.is_dir():
        raise CustomerFacingError(MSG_BUNDLE_MISSING)

    public_path = root / PUBLIC_PEM_NAME
    private_path = root / PRIVATE_PEM_NAME
    if not public_path.is_file() or not private_path.is_file():
        raise CustomerFacingError(MSG_BUNDLE_MISSING)

    try:
        public_pem = public_path.read_bytes()
        private_pem = private_path.read_bytes()
    except OSError as exc:
        raise CustomerFacingError(MSG_BUNDLE_MISSING) from exc

    _validate_rsa_pair(public_pem, private_pem)
    return KeyBundleFiles(
        bundle_dir=root,
        public_pem_path=public_path,
        private_pem_path=private_path,
        public_pem=public_pem,
        private_pem=private_pem,
    )


def _validate_rsa_pair(public_pem: bytes, private_pem: bytes) -> None:
    try:
        pub_key = serialization.load_pem_public_key(public_pem)
        priv_key = serialization.load_pem_private_key(private_pem, password=None)
    except (ValueError, TypeError) as exc:
        raise CustomerFacingError(MSG_INVALID_KEY) from exc

    if not isinstance(pub_key, rsa.RSAPublicKey) or not isinstance(
        priv_key, rsa.RSAPrivateKey
    ):
        raise CustomerFacingError(MSG_INVALID_KEY)

    if pub_key.key_size != CENC_RSA_BITS or priv_key.key_size != CENC_RSA_BITS:
        raise CustomerFacingError(MSG_INVALID_KEY)

    pub_numbers = pub_key.public_numbers()
    priv_pub = priv_key.public_key().public_numbers()
    if pub_numbers.n != priv_pub.n or pub_numbers.e != priv_pub.e:
        raise CustomerFacingError(MSG_INVALID_KEY)
