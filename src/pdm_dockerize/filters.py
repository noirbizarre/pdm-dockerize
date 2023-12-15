from __future__ import annotations

from fnmatch import fnmatch
from typing import Mapping


def parse(data: Mapping, key: str) -> list[str]:
    """Parse a filter key"""
    filters = data.get(key) or []
    if isinstance(filters, str):
        filters = [filters]
    if any(not isinstance(filter, str) for filter in filters):
        raise TypeError("Filters should be fnmatch patterns as string")
    return filters


def match(value: str, patterns: list[str]) -> bool:
    """Check whether a value match any of the patterns"""
    return any(fnmatch(value, pattern) for pattern in patterns)
