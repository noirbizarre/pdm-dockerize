from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

    from pdm.project import Project
    from pdm.pytest import PDMCallable

    from tests.conftest import AddMemberFixture


uv = pytest.mark.pdm_global_config(use_uv=True)
"""Run the same scenario through the `uv` based installer"""


def dockerize(pdm: PDMCallable, project: Project, args: str = "-v") -> Path:
    """Lock then dockerize a workspace, returning the output directory

    `cleanup=False` keeps the HTTP session alive between both calls:
    building the member wheels needs it to fetch their build requirements.
    """
    pdm("lock", obj=project, strict=True, cleanup=False)
    result = pdm(f"dockerize {args}", obj=project, strict=True)
    # Guard against silently falling back to the pip installer in `uv` runs
    assert "uv not found" not in result.output
    return project.root / "dist/docker"


@pytest.mark.parametrize("use_uv", [False, True], ids=["pip", "uv"])
def test_workspace_members_are_installed(
    workspace: Project, pdm: PDMCallable, use_uv: bool
) -> None:
    """Workspace members are implicit dependencies of the workspace root"""
    if use_uv:
        workspace.global_config["use_uv"] = True

    lib = dockerize(pdm, workspace) / "lib"

    assert (lib / "member_a").is_dir()
    assert not (lib / "member_a").is_symlink()
    assert (lib / "member_b").is_dir()
    # Transitive dependencies of a member are installed too
    assert (lib / "faker").is_dir()


@pytest.mark.parametrize("use_uv", [False, True], ids=["pip", "uv"])
def test_workspace_members_are_not_editable(
    workspace: Project, pdm: PDMCallable, use_uv: bool
) -> None:
    """Editable installs would point at build-time paths missing from the image"""
    if use_uv:
        workspace.global_config["use_uv"] = True

    lib = dockerize(pdm, workspace) / "lib"

    assert not list(lib.glob("*.pth"))
    assert not list(lib.glob("__editable__*"))
    assert not list(lib.glob("_member_a*.py"))


@pytest.mark.parametrize("use_uv", [False, True], ids=["pip", "uv"])
def test_workspace_member_scripts(workspace: Project, pdm: PDMCallable, use_uv: bool) -> None:
    """Member console scripts are exposed like any other dependency"""
    if use_uv:
        workspace.global_config["use_uv"] = True

    dist = dockerize(pdm, workspace)

    script = dist / "bin/member-a"
    assert script.is_file()
    assert os.access(script, os.X_OK)
    # No leftover lib/bin from `uv pip install --target`
    assert not (dist / "lib/bin").exists()


def test_workspace_member_bins_are_filtered(workspace: Project, pdm: PDMCallable) -> None:
    """Member scripts go through the same `include_bins`/`exclude_bins` filters"""
    workspace.pyproject.settings["dockerize"]["exclude_bins"] = ["member-a"]
    workspace.pyproject.write()

    bin = dockerize(pdm, workspace) / "bin"

    assert not (bin / "member-a").exists()
    assert (bin / "faker").is_file()


def test_explicit_member_dependency_is_not_duplicated(workspace: Project, pdm: PDMCallable) -> None:
    """A member also declared as a root dependency is installed once"""
    workspace.pyproject.metadata["dependencies"] = [
        "member-a @ file:///${PROJECT_ROOT}/packages/member-a"
    ]
    workspace.pyproject.write()

    lib = dockerize(pdm, workspace) / "lib"

    assert (lib / "member_a").is_dir()
    assert len(list(lib.glob("member_a-*.dist-info"))) == 1


def test_virtual_workspace_root(workspace: Project, pdm: PDMCallable) -> None:
    """A workspace root is usually a non-distribution aggregating project"""
    workspace.pyproject.settings["distribution"] = False
    # A stray `src` directory must not end up on `PYTHONPATH`
    (workspace.root / "src").mkdir(parents=True, exist_ok=True)
    workspace.pyproject.write()

    dist = dockerize(pdm, workspace)

    assert (dist / "lib/member_a").is_dir()
    assert (dist / "lib/member_b").is_dir()
    # No phantom `src` on PYTHONPATH: the root has no sources of its own
    assert '"$(pwd)/src"' not in (dist / "entrypoint").read_text()


def test_non_distribution_member_is_skipped(
    workspace: Project, pdm: PDMCallable, add_member: AddMemberFixture
) -> None:
    """Only distribution members can be installed"""
    add_member("member-c", distribution=False)

    lib = dockerize(pdm, workspace) / "lib"

    assert (lib / "member_a").is_dir()
    assert not (lib / "member_c").exists()


def test_no_default_excludes_members(workspace: Project, pdm: PDMCallable) -> None:
    """Members are `default` group dependencies"""
    workspace.pyproject.settings["dev-dependencies"] = {"dev": ["Faker"]}
    workspace.pyproject.write()

    lib = dockerize(pdm, workspace, "-v --no-default -d -G dev") / "lib"

    assert not (lib / "member_a").exists()
    assert not (lib / "member_b").exists()


def test_dockerize_from_a_member_targets_the_member(
    workspace: Project, pdm: PDMCallable
) -> None:
    """Running from a member builds that member image, not the workspace one"""
    pdm("lock", obj=workspace, strict=True, cleanup=False)
    member = workspace.core.create_project(workspace.root / "packages/member-a")

    pdm("dockerize -v", obj=member, strict=True)

    assert (member.root / "dist/docker/entrypoint").is_file()
    assert not (workspace.root / "dist/docker").exists()


def test_dockerize_outside_a_workspace_is_unaffected(
    project: Project, pdm: PDMCallable, add_member: AddMemberFixture
) -> None:
    """A nested project that is not a declared member is not a workspace member"""
    project.pyproject.settings["dockerize"] = {"include": "*"}
    project.pyproject.metadata["requires-python"] = ">=3.10"
    project.pyproject.metadata["dependencies"] = ["Faker"]
    project.pyproject.write()
    # A nested project, but no `[tool.pdm.workspace]` on the root
    add_member("nested")

    lib = dockerize(pdm, project) / "lib"

    assert (lib / "faker").is_dir()
    assert not (lib / "nested").exists()
