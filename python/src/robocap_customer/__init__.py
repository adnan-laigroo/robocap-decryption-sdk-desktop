"""Robocap customer-side simplified batch decrypt layer."""

from __future__ import annotations

__version__ = "2.0.0"

from robocap_customer.bootstrap import init_customer_logging
from robocap_customer.delete_prompts import delete_main
from robocap_customer.import_prompts import import_main
from robocap_customer.prompts import interactive_main

__all__ = [
    "__version__",
    "delete_main",
    "import_main",
    "init_customer_logging",
    "interactive_main",
]
