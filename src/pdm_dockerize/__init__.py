from __future__ import annotations

import importlib.metadata as importlib_metadata

from pdm.core import Core

__version__ = importlib_metadata.version("pdm-dockerize")


def plugin(core: Core):
    from .commands import DockerizeCommand

    # Register commands
    core.register_command(DockerizeCommand, "dockerize")
