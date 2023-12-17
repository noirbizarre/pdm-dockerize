from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pdm.project import Project
    from pdm.pytest import PDMCallable
    from syrupy import SnapshotAssertion


@pytest.fixture
def project(project: Project) -> Project:
    project.pyproject.settings["dockerize"] = {"include": "*"}
    project.pyproject.metadata["requires-python"] = ">=3.8"
    project.pyproject.metadata["dependencies"] = ["Faker"]
    project.pyproject.settings["scripts"] = {"test": "pytest"}
    return project


def test_expose_version():
    import pdm_dockerize

    assert pdm_dockerize.__version__


def test_generate_docker_dist(project: Project, pdm: PDMCallable, snapshot: SnapshotAssertion):
    project.pyproject.settings["dockerize"]["include_bins"] = "*"
    project.pyproject.write()
    pdm("lock", obj=project, strict=True)

    pdm("dockerize", obj=project, strict=True)

    dist = project.root / "dist/docker"
    assert dist.is_dir()

    entrypoint = dist / "entrypoint"
    assert entrypoint.exists()
    assert os.access(entrypoint, os.X_OK)
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
    project.pyproject.settings["dockerize"]["include_bins"] = "*"
    project.pyproject.write()
    pdm("lock", obj=project, strict=True)

    target = tmp_path / "target"

    pdm(f"dockerize {target}", obj=project, strict=True)

    dist = project.root / "dist/docker"
    assert not dist.exists()

    entrypoint = target / "entrypoint"
    assert entrypoint.exists()
    assert os.access(entrypoint, os.X_OK)
    assert entrypoint.read_text() == snapshot

    lib = target / "lib"
    assert lib.is_dir()
    assert (lib / "faker").is_dir()
    assert not (lib / "faker").is_symlink()

    bin = target / "bin"
    assert bin.is_dir()
    assert (bin / "faker").is_file()


@dataclass
class BinFilterCase:
    id: str
    include: str | list[str] | None = None
    exclude: str | list[str] | None = None
    expected: list[str] = field(default_factory=list)


BIN_FILTER_CASES = (
    BinFilterCase("no-filter"),
    BinFilterCase(
        "include-all", include="*", expected=["black", "blackd", "faker", "pytest", "py.test"]
    ),
    BinFilterCase("include-list", include=["faker", "black"], expected=["faker", "black"]),
    BinFilterCase("exclude-all", include="*", exclude="*"),
    BinFilterCase(
        "exclude-list",
        include="*",
        exclude=["any", "blackd"],
        expected=["black", "pytest", "py.test", "faker"],
    ),
    BinFilterCase(
        "include-all-but-prefix", include="*", exclude="py*", expected=["black", "blackd", "faker"]
    ),
    BinFilterCase(
        "include-prefix-except",
        include="py*",
        exclude="py",
        expected=["pytest", "py.test"],
    ),
)


@pytest.mark.parametrize("case", [pytest.param(case, id=case.id) for case in BIN_FILTER_CASES])
def test_binaries_filtering(project: Project, pdm: PDMCallable, case: BinFilterCase):
    project.pyproject.metadata["dependencies"] = ["Faker", "pytest", "black"]
    if case.include:
        project.pyproject.settings["dockerize"]["include_bins"] = case.include
    if case.exclude:
        project.pyproject.settings["dockerize"]["exclude_bins"] = case.exclude
    project.pyproject.write()

    pdm("lock", obj=project, strict=True)
    pdm("dockerize", obj=project, strict=True)

    bindir = project.root / "dist/docker/bin"
    if bindir.exists():
        bins = [bin.name for bin in bindir.iterdir() if bin.is_file() and os.access(bin, os.X_OK)]
    else:
        bins = []

    assert set(bins) == set(case.expected)
