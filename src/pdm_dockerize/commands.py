from __future__ import annotations

import argparse
import os
from pathlib import Path

from pdm.cli import actions
from pdm.cli.commands.base import BaseCommand
from pdm.cli.filters import GroupSelection
from pdm.cli.hooks import HookManager
from pdm.cli.options import Option, dry_run_option, groups_group, lockfile_option
from pdm.cli.utils import check_project_file
from pdm.environments import PythonLocalEnvironment
from pdm.project import Project

from .entrypoint import ProjectEntrypoint
from .installer import DockerizeSynchronizer


class DockerizeEnvironment(PythonLocalEnvironment):
    """An environment installaing into the dist/docker directory"""

    def __init__(
        self, project: Project, *, target: str | None = None, python: str | None = None
    ) -> None:
        super().__init__(project, python=python)
        self.target = Path(target) if target else None

    @property
    def packages_path(self) -> Path:
        return self.target or self.project.root / "dist/docker"


class DockerizeCommand(BaseCommand):
    """Generate content for a Docker image"""

    arguments = (
        Option(
            "target",
            nargs="?",
            help="The target into which the docker assets will be generated (default: dist/docker)",
        ),
        *BaseCommand.arguments,
        groups_group,
        dry_run_option,
        lockfile_option,
    )

    def handle(self, project: Project, options: argparse.Namespace) -> None:
        check_project_file(project)
        actions.check_lockfile(project)
        selection = GroupSelection.from_options(project, options)
        hooks = HookManager(project)
        env = DockerizeEnvironment(project, target=options.target)

        requirements = []
        selection.validate()
        for group in selection:
            requirements.extend(project.get_dependencies(group).values())
        candidates = actions.resolve_candidates_from_lockfile(project, requirements)
        synchronizer = DockerizeSynchronizer(
            candidates,
            env,
            dry_run=options.dry_run,
            clean=False,
            no_editable=True,
            reinstall=False,
            only_keep=False,
            install_self=False,
            fail_fast=True,
            use_install_cache=False,
        )
        synchronizer.synchronize()

        entrypoint = env.packages_path / "entrypoint"
        entrypoint.write_text(ProjectEntrypoint(project, hooks).as_script())
        os.chmod(entrypoint, 0o555)
