from __future__ import annotations

import json
import shutil
import subprocess
from collections.abc import Iterable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from installer.destinations import Scheme
from installer.records import RecordEntry
from pdm import termui
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
    from pdm.project import Project

    from .commands import DockerizeEnvironment
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


class DockerizeUvSynchronizer:
    """Install packages using ``uv pip install --target`` for dockerize output.

    This bypasses PDM's Synchronizer/InstallManager pipeline entirely
    and invokes ``uv`` as a subprocess. After installation, scripts are
    moved from ``lib/bin/`` to ``bin/`` with include/exclude filtering applied.
    """

    def __init__(
        self,
        project: Project,
        environment: DockerizeEnvironment,
        candidates: dict[str, Candidate],
        *,
        dry_run: bool = False,
    ) -> None:
        self.project = project
        self.environment = environment
        self.candidates = candidates
        self.dry_run = dry_run
        settings: DockerizeSettings = project.pyproject.settings.get("dockerize", {})
        self.include_bins = filters.parse(settings, "include_bins")
        self.exclude_bins = filters.parse(settings, "exclude_bins")

    def _build_package_specs(self) -> list[str]:
        """Convert resolved candidates to pinned pip-installable specs."""
        specs: list[str] = []
        for key, candidate in self.candidates.items():
            req = candidate.req
            if req.is_named:
                # Registry package: pin to exact version
                pinned = req.as_pinned_version(candidate.version)
                specs.append(pinned.as_line())
            else:
                # File/VCS/URL requirement: use as-is
                specs.append(req.as_line())
        return specs

    def _build_command(self, target: str) -> list[str]:
        """Build the ``uv pip install --target`` command."""
        uv_cmd = self.project.core.uv_cmd
        cmd: list[str] = [
            *uv_cmd,
            "pip",
            "install",
            "--target",
            target,
            "-p",
            str(self.environment.interpreter.executable),
            "--reinstall",
        ]
        # Pass index sources
        first_index = True
        for source in self.project.sources:
            url = source.url_with_credentials
            url_str = url.secret if hasattr(url, "secret") else str(url)
            if source.type == "find_links":
                cmd.extend(["--find-links", url_str])
            elif first_index:
                cmd.extend(["--index-url", url_str])
                first_index = False
            else:
                cmd.extend(["--extra-index-url", url_str])
        # Add package specs
        cmd.extend(self._build_package_specs())
        return cmd

    def _process_scripts(self, lib_path: Path, bin_path: Path) -> None:
        """Move scripts from lib/bin/ to bin/ with filtering applied."""
        src_bin = lib_path / "bin"
        if not src_bin.is_dir():
            return

        for script_file in src_bin.iterdir():
            if not script_file.is_file():
                continue
            name = script_file.name
            if filters.match(name, self.include_bins) and not filters.match(
                name, self.exclude_bins
            ):
                bin_path.mkdir(parents=True, exist_ok=True)
                dest = bin_path / name
                shutil.move(str(script_file), str(dest))
                termui.logger.debug("Installed script: %s", name)
            else:
                termui.logger.debug("Filtered out script: %s", name)

        # Clean up the lib/bin/ directory
        shutil.rmtree(src_bin, ignore_errors=True)

    def synchronize(self) -> None:
        """Install packages using uv and post-process scripts."""
        ui = self.project.core.ui

        if not self.candidates:
            ui.echo("No packages to install.")
            return

        packages_path = self.environment.packages_path
        lib_path = packages_path / "lib"
        bin_path = packages_path / "bin"

        if self.dry_run:
            specs = self._build_package_specs()
            ui.echo("Dry run: would install the following packages with uv:")
            for spec in specs:
                ui.echo(f"  {spec}")
            return

        lib_path.mkdir(parents=True, exist_ok=True)

        cmd = self._build_command(str(lib_path))
        termui.logger.debug("Running uv command: %s", " ".join(cmd))
        subprocess.run(cmd, check=True, cwd=str(self.project.root))

        # Post-process: move scripts from lib/bin/ to bin/ with filtering
        self._process_scripts(lib_path, bin_path)
