from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

import pytest
import tomlkit
from syrupy.extensions.single_file import SingleFileSnapshotExtension, WriteMode

if TYPE_CHECKING:
    from pdm.project import Project
    from syrupy import SnapshotAssertion


ROOT = Path(__file__).parent / "tests"

pytest_plugins = [
    "pdm.pytest",
]


@pytest.fixture
def project(project: Project, request: pytest.FixtureRequest) -> Project:
    if marker := request.node.get_closest_marker("pdm_global_config"):
        for key, value in marker.kwargs.items():
            project.global_config[key] = value
    if marker := request.node.get_closest_marker("pdm_local_config"):
        for key, value in marker.kwargs.items():
            project.project_config[key] = value
    return project


class ScriptExtension(SingleFileSnapshotExtension):
    file_extension = "sh"
    _write_mode = WriteMode.TEXT


@pytest.fixture
def snapshot(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    return snapshot.use_extension(ScriptExtension)


class ShellcheckFixture(Protocol):
    def __call__(self, script: str): ...


class ShellcheckError(AssertionError):
    pass


@pytest.fixture
def shellcheck(tmp_path_factory: pytest.TempPathFactory) -> ShellcheckFixture:
    def fixture(script: str):
        file = tmp_path_factory.mktemp("shellcheck", True) / "script.sh"
        file.write_text(script)
        result = subprocess.run(["shellcheck", str(file)], capture_output=True)
        file.unlink()
        if result.returncode != 0:
            raise ShellcheckError(result.stdout.decode())

    return fixture


class AddMemberFixture(Protocol):
    def __call__(
        self,
        name: str,
        *,
        path: str | None = None,
        dependencies: list[str] | None = None,
        scripts: dict[str, str] | None = None,
        pdm_scripts: dict[str, Any] | None = None,
        dockerize: dict[str, Any] | None = None,
        distribution: bool = True,
    ) -> Path: ...


@pytest.fixture
def add_member(project: Project) -> AddMemberFixture:
    """Create a real workspace member on disk, under the project root.

    Members must exist on disk: `Project.iter_members()` filters on the presence
    of a `pyproject.toml` and `iter_workspace_dependencies()` requires the member
    to be a named distribution.

    `scripts` are `[project.scripts]` console entry points, while `pdm_scripts`
    and `dockerize` are the member's `[tool.pdm.scripts]` and
    `[tool.pdm.dockerize]` sections.
    """

    def factory(
        name: str,
        *,
        path: str | None = None,
        dependencies: list[str] | None = None,
        scripts: dict[str, str] | None = None,
        pdm_scripts: dict[str, Any] | None = None,
        dockerize: dict[str, Any] | None = None,
        distribution: bool = True,
    ) -> Path:
        module = name.replace("-", "_")
        member_dir = project.root / (path or f"packages/{name}")
        pkg_dir = member_dir / "src" / module
        pkg_dir.mkdir(parents=True, exist_ok=True)
        (pkg_dir / "__init__.py").write_text('__version__ = "0.1.0"\n')
        (pkg_dir / "cli.py").write_text(f"def main():\n    print('hello from {name}')\n")

        metadata: dict = {
            "name": name,
            "version": "0.1.0",
            "description": "",
            "authors": [],
            "requires-python": ">=3.10",
            "dependencies": dependencies or [],
        }
        if scripts:
            metadata["scripts"] = scripts
        data: dict = {
            "project": metadata,
            "build-system": {"requires": ["pdm-backend"], "build-backend": "pdm.backend"},
        }
        tool_pdm: dict = {}
        if not distribution:
            tool_pdm["distribution"] = False
        if pdm_scripts:
            tool_pdm["scripts"] = pdm_scripts
        if dockerize is not None:
            tool_pdm["dockerize"] = dockerize
        if tool_pdm:
            data["tool"] = {"pdm": tool_pdm}
        (member_dir / "pyproject.toml").write_text(tomlkit.dumps(data))
        return member_dir

    return factory


@pytest.fixture
def workspace(project: Project, add_member: AddMemberFixture) -> Project:
    """A workspace root with two members.

    Members are written before any `Project` is built for them, as both
    `Project.pyproject` and `Project.workspace_project` are cached properties.
    """
    add_member("member-a", dependencies=["Faker"], scripts={"member-a": "member_a.cli:main"})
    add_member("member-b")
    project.pyproject.settings["workspace"] = {"members": ["packages/*"]}
    project.pyproject.settings["dockerize"] = {"include": "*", "include_bins": "*"}
    project.pyproject.settings["scripts"] = {"test": "pytest"}
    project.pyproject.metadata["requires-python"] = ">=3.10"
    project.pyproject.metadata["dependencies"] = []
    project.pyproject.write()
    return project


class MemberFixture(Protocol):
    def __call__(self, name: str = ...) -> Project: ...


@pytest.fixture
def member(project: Project) -> MemberFixture:
    """Build a `Project` for a member of the current workspace.

    The factory is called from the test body, once the workspace
    `pyproject.toml` has been written: `Project.pyproject` and
    `Project.workspace_project` are both cached properties.
    """

    def factory(name: str = "member-a") -> Project:
        member_project = project.core.create_project(project.root / "packages" / name)
        # Guard against a fixture ordering regression silently degrading
        # the tests to the plain, non-workspace code path
        assert member_project.workspace_project is not None
        return member_project

    return factory
