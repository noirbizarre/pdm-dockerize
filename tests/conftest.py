from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

import pytest
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
    _file_extension = "sh"
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
