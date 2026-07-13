"""RFC 8785 canonical JSON helpers shared by provider contracts and fixtures."""

from __future__ import annotations

import hashlib
from typing import Any

import rfc8785


def canonicalize(value: Any) -> bytes:
    return rfc8785.dumps(value)


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonicalize(value)).hexdigest()

