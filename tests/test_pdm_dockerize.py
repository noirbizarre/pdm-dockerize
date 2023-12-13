from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pdm.project import Project
    from pdm.pytest import PDMCallable
    from syrupy import SnapshotAssertion


@pytest.fixture
def project(project: Project, pdm: PDMCallable) -> Project:
    project.pyproject.settings["dockerize"] = {"include": "*"}
    project.pyproject.metadata["requires-python"] = ">=3.8"
    project.pyproject.metadata["dependencies"] = ["Faker"]
    project.pyproject.settings["scripts"] = {"test": "pytest"}
    project.pyproject.write()
    pdm("lock", obj=project, strict=True)
    return project


def test_expose_version():
    import pdm_dockerize

    assert pdm_dockerize.__version__


def test_generate_docker_dist(project: Project, pdm: PDMCallable, snapshot: SnapshotAssertion):
    result = pdm("dockerize", obj=project, strict=True)

    if result.exception:
        raise result.exception
    assert result.exit_code == 0

    dist = project.root / "dist/docker"
    assert dist.is_dir()

    entrypoint = dist / "entrypoint"
    assert entrypoint.exists()
    assert entrypoint.read_text() == snapshot

    lib = dist / "lib"
    assert lib.is_dir()
    assert (lib / "faker").is_dir()
    assert not (lib / "faker").is_symlink()

    bin = dist / "bin"
    assert bin.is_dir()
    assert (bin / "faker").is_file()


def test_generate_docker_dist_to_target(
    project: Project, pdm: PDMCallable, snapshot: SnapshotAssertion, tmp_path: Path
):
    target = tmp_path / "target"
    result = pdm(f"dockerize {target}", obj=project, strict=True)

    if result.exception:
        raise result.exception
    assert result.exit_code == 0

    dist = project.root / "dist/docker"
    assert not dist.exists()

    entrypoint = target / "entrypoint"
    assert entrypoint.exists()
    assert entrypoint.read_text() == snapshot

    lib = target / "lib"
    assert lib.is_dir()
    assert (lib / "faker").is_dir()
    assert not (lib / "faker").is_symlink()

    bin = target / "bin"
    assert bin.is_dir()
    assert (bin / "faker").is_file()
