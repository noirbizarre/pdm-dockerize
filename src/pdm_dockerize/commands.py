from __future__ import annotations

import argparse
import collections
import contextlib
import dataclasses
import os
from pathlib import Path
from typing import TYPE_CHECKING, cast

from pdm.cli import actions
from pdm.cli.commands.base import BaseCommand
from pdm.cli.filters import GroupSelection
from pdm.cli.hooks import HookManager
from pdm.cli.options import Option, dry_run_option, groups_group, lockfile_option
from pdm.cli.utils import check_project_file
from pdm.environments import PythonLocalEnvironment
from pdm.exceptions import PdmUsageError
from pdm.models.requirements import parse_line
from pdm.project import Project

from .entrypoint import ProjectEntrypoint
from .installer import DockerizeSynchronizer, DockerizeUvSynchronizer

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pdm.models.repositories.lock import LockedRepository
    from pdm.models.requirements import Requirement


def _split_combined_extras(req: Requirement, package_keys: set[str]) -> list[Requirement] | None:
    """Split a combined-extras requirement into single-extra requirements.

    UV-generated lockfiles store each extra as a separate entry
    (e.g., ``pkg[a]`` and ``pkg[b]``), while resolvelib-generated lockfiles
    combine them into a single entry (``pkg[a,b]``).

    Returns the per-extra requirements when ``req`` has combined extras which
    are stored as separate entries in the lock file, ``None`` otherwise
    (nothing to adapt).
    """
    if not req.extras or len(req.extras) < 2:
        return None
    if req.identify() in package_keys:
        # Combined entry found: resolvelib-style lock file, nothing to do
        return None
    split = [dataclasses.replace(req, extras=(extra,)) for extra in sorted(req.extras)]
    if not all(r.identify() in package_keys for r in split):
        # Not all individual entries are present: leave it untouched (safety fallback)
        return None
    return split


def _adapt_requirements_for_lockfile(
    requirements: list[Requirement],
    project: Project,
) -> list[Requirement]:
    """Adapt the project requirements to match the lockfile's extras format.

    A combined-extras requirement like ``pkg[a,b]`` will fail to match a uv
    generated lock file because resolvelib's ``_matching_entries()`` does exact
    string comparison on the candidate identity.

    See :func:`_split_combined_extras`.
    """
    locked_repo = project.get_locked_repository()
    package_keys = {key[0] for key in locked_repo.packages}

    result: list[Requirement] = []
    for req in requirements:
        result.extend(_split_combined_extras(req, package_keys) or [req])
    return result


def _adapt_locked_dependencies(repo: LockedRepository) -> None:
    """Adapt the locked packages dependencies to match the lockfile's extras format.

    Combined extras are not only found in the project requirements:
    a locked package can require another one with multiple extras
    (``pkg[a,b]``), in which case resolvelib will fail to find the
    corresponding entry while walking the dependency tree.

    Dependencies are rewritten in place, so that transitive combined-extras
    requirements are split the same way the project ones are.

    See :func:`_split_combined_extras`.
    """
    package_keys = {key[0] for key in repo.packages}
    for package in repo.packages.values():
        if not package.dependencies:
            continue
        adapted: list[str] = []
        changed = False
        for line in package.dependencies:
            if split := _split_combined_extras(parse_line(line), package_keys):
                adapted.extend(req.as_line() for req in split)
                changed = True
            else:
                adapted.append(line)
        if changed:
            package.dependencies[:] = adapted


def _adapt_locked_members(repo: LockedRepository, members: dict[str, Requirement]) -> None:
    """Restore the local path of the workspace members in a locked repository.

    ``uv`` generated lock files store workspace members without their location
    (only a name, a version and the editable flag), so they are read back as
    named requirements, which can never be matched against the local path
    requirements the workspace root implicitly depends on.

    Members are given their path requirement back, and the packages are re-keyed
    accordingly, as the candidate identity depends on it.
    """
    if not members:
        return
    packages: dict = {}
    changed = False
    for key, package in repo.packages.items():
        candidate = package.candidate
        req = members.get(candidate.identify())
        if req is not None and candidate.req.is_named:
            package = dataclasses.replace(package, candidate=candidate.copy_with(req))
            changed = True
            key = repo._identify_candidate(package.candidate)
        packages[key] = package
    if changed:
        repo.packages = packages


@contextlib.contextmanager
def _adapted_locked_repository(project: Project) -> Iterator[None]:
    """Adapt every :class:`LockedRepository` built by ``project`` in this context.

    ``pdm`` builds a new locked repository on each
    :meth:`~pdm.project.Project.get_locked_repository` call, including deep
    inside the resolution, so the adaptation is injected at the source.
    """
    original = project.get_locked_repository
    members = {req.identify(): req for req in project.iter_workspace_dependencies()}

    def get_locked_repository(*args, **kwargs) -> LockedRepository:
        repo = original(*args, **kwargs)
        _adapt_locked_dependencies(repo)
        _adapt_locked_members(repo, members)
        return repo

    project.get_locked_repository = get_locked_repository  # type: ignore[method-assign]
    try:
        yield
    finally:
        del project.get_locked_repository  # type: ignore[method-assign]


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
        if (workspace := project.workspace_project) is not None:
            # Workspace members share the root lockfile and environment, so a
            # single image is built from the workspace root, like `pdm install`.
            raise PdmUsageError(
                f"`pdm dockerize` can only be run from the workspace root: {workspace.root}"
            )
        check_project_file(project)
        actions.check_lockfile(project)
        selection = GroupSelection.from_options(project, options)
        hooks = HookManager(project)
        env = DockerizeEnvironment(project, target=options.target)

        requirements = []
        selection.validate()
        for group in selection:
            requirements.extend(project.get_dependencies(group))
        if "default" in selection:
            # Workspace members are implicit `default` dependencies of the
            # workspace root: mirror `pdm.cli.actions.do_lock`.
            requirements = project.with_workspace_dependencies(requirements)
        # Always use the resolvelib resolver to read from pdm.lock,
        # even when uv is configured as the project resolver.
        # UvResolver would run `uv lock` (a full re-resolution) which is
        # inappropriate here — we only need to read existing locked candidates.
        config = cast(collections.ChainMap, project.config)
        config.maps.insert(0, {"use_uv": False})
        try:
            with _adapted_locked_repository(project):
                requirements = _adapt_requirements_for_lockfile(requirements, project)
                candidates = actions.resolve_candidates_from_lockfile(project, requirements)
        finally:
            config.maps.pop(0)

        use_uv = project.config.get("use_uv", False)
        if use_uv:
            try:
                project.core.uv_cmd  # noqa: B018 — verify uv is available
                synchronizer = DockerizeUvSynchronizer(
                    project,
                    env,
                    candidates,
                    dry_run=options.dry_run,
                )
            except PdmUsageError:
                project.core.ui.echo("[warning]uv not found, falling back to pip-based installer")
                use_uv = False

        if not use_uv:
            synchronizer = DockerizeSynchronizer(
                env,
                candidates,
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

        script = ProjectEntrypoint(project, hooks).as_script()

        if options.dry_run:
            project.core.ui.echo("Dry run: would write the following entrypoint script:")
            project.core.ui.echo(script)
            return

        entrypoint = env.packages_path / "entrypoint"
        entrypoint.write_text(script)
        os.chmod(entrypoint, 0o555)
