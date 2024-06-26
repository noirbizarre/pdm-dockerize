from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable

from installer.destinations import Scheme
from installer.records import RecordEntry
from pdm.compat import Distribution
from pdm.installers import Synchronizer
from pdm.installers.installers import InstallDestination, WheelFile, install
from pdm.installers.manager import InstallManager

from . import filters

if TYPE_CHECKING:
    from installer.scripts import ScriptSection
    from pdm.environments import BaseEnvironment
    from pdm.installers.installers import LinkMethod
    from pdm.models.candidates import Candidate

    from .config import DockerizeSettings


class DockerizeInstallManager(InstallManager):
    """An `InstallManager` filtering installed binaries"""

    def __init__(
        self,
        environment: BaseEnvironment,
        *,
        use_install_cache: bool = False,
        rename_pth: bool = False,
    ) -> None:
        super().__init__(environment, use_install_cache=use_install_cache, rename_pth=rename_pth)
        settings: DockerizeSettings = self.environment.project.pyproject.settings.get(
            "dockerize", {}
        )
        self.include = filters.parse(settings, "include_bins")
        self.exclude = filters.parse(settings, "exclude_bins")

    def install(self, candidate: Candidate) -> Distribution:
        """Install a candidate into the environment, return the distribution"""
        prepared = candidate.prepare(self.environment)
        additional_metadata = None
        if (direct_url := prepared.direct_url()) is not None:
            additional_metadata = {"direct_url.json": json.dumps(direct_url, indent=2).encode()}
        destination = FilteringDestination(
            scheme_dict=self.environment.get_paths(),
            interpreter=str(self.environment.interpreter.executable),
            script_kind=self.environment.script_kind,
            include=self.include,
            exclude=self.exclude,
        )

        with WheelFile.open(prepared.build()) as source:
            dist_info = install(source, destination, additional_metadata)
        return Distribution.at(dist_info)


class DockerizeSynchronizer(Synchronizer):
    """A `Synchronizer` using the `DockerizeInstallManager`"""

    def get_manager(self, rename_pth: bool = False) -> InstallManager:
        return DockerizeInstallManager(
            self.environment,
            use_install_cache=self.use_install_cache,
            rename_pth=rename_pth,
        )


class FilteringDestination(InstallDestination):
    """An `InstallDestination` filtering installed binaries"""

    def __init__(
        self,
        *args: Any,
        link_method: LinkMethod = "copy",
        include: list[str] | None = None,
        exclude: list[str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            *args,
            link_method=link_method,
            **kwargs,
        )

        self.include = include or []
        self.exclude = exclude or []

    def write_script(
        self, name: str, module: str, attr: str, section: ScriptSection
    ) -> RecordEntry:
        if filters.match(name, self.include) and not filters.match(name, self.exclude):
            return super().write_script(name, module, attr, section)
        return RecordEntry("", None, None)

    def finalize_installation(
        self,
        scheme: Scheme,
        record_file_path: str | Path,
        records: Iterable[tuple[Scheme, RecordEntry]],
    ) -> None:
        records = [(scheme, record) for scheme, record in records if record.path]
        return super().finalize_installation(scheme, record_file_path, records)
