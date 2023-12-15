from __future__ import annotations

from typing import TypedDict


class DockerizeSettings(TypedDict):
    include: str | list[str] | None
    """List of command patterns to include"""

    exclude: str | list[str] | None
    """List of command patterns to exclude"""

    include_bins: str | list[str] | None
    """List of binaries patterns to include"""

    exclude_bins: str | list[str] | None
    """List of binanries patterns to exclude"""
