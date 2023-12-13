from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

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
