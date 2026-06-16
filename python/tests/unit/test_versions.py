from importlib.metadata import version

import robocap_customer
import robocap_decryption_sdk


def test_public_versions_match_package_metadata() -> None:
    package_version = version("robocap-decryption-sdk")

    assert robocap_decryption_sdk.__version__ == package_version
    assert robocap_customer.__version__ == package_version
