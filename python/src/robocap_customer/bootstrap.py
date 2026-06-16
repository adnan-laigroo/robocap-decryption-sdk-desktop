from __future__ import annotations

import logging


def init_customer_logging() -> None:
    logging.getLogger("robocap_decryption_sdk").setLevel(logging.CRITICAL)
