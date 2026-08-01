from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest
import tomlkit

if TYPE_CHECKING:
    from pathlib import Path

    from pdm.project import Project
    from pdm.pytest import PDMCallable
    from syrupy import SnapshotAssertion

    from tests.conftest import AddMemberFixture, MemberFixture, ShellcheckFixture


backends = pytest.mark.parametrize("use_uv", [False, True], ids=["pip", "uv"])
"""Run the same scenario through both the pip based and the uv based installers"""


@pytest.fixture
def member_workspace(project: Project, add_member: AddMemberFixture) -> Project:
    """A workspace whose `member-a` has a sibling dependency and its own settings"""
    add_member(
        "member-a",
        dependencies=["Faker", "member-b"],
        scripts={"member-a": "member_a.cli:main"},
        pdm_scripts={"serve": "echo serving", "_private": "echo hidden"},
        dockerize={"include": "*", "include_bins": "*", "env": {"FROM_MEMBER": "1"}},
    )
    add_member("member-b")
    # A member `member-a` does not depend on
    add_member("member-z")
    project.pyproject.settings["workspace"] = {"members": ["packages/*"]}
    project.pyproject.settings["dockerize"] = {"include": "*", "env": {"FROM_ROOT": "1"}}
    project.pyproject.settings["scripts"] = {"root-only": "echo root"}
    project.pyproject.metadata["requires-python"] = ">=3.10"
    project.pyproject.metadata["dependencies"] = []
    project.pyproject.write()
    return project


def dockerize_member(
    pdm: PDMCallable, root: Project, member: Project, args: str = "-v"
) -> Path:
    """Lock at the workspace root, then dockerize a single member

    `cleanup=False` keeps the HTTP session alive between both calls:
    building the member wheels needs it to fetch their build requirements.
    """
    pdm("lock", obj=root, strict=True, cleanup=False)
    result = pdm(f"dockerize {args}", obj=member, strict=True)
    # Guard against silently falling back to the pip installer in `uv` runs
    assert "uv not found" not in result.output
    return member.root / "dist/docker"


def installed(lib: Path) -> set[str]:
    """The distribution names installed in a `lib` directory"""
    return {path.name for path in lib.iterdir() if not path.name.endswith(".dist-info")}


@backends
def test_member_dependencies_are_installed(
    member_workspace: Project, member: MemberFixture, pdm: PDMCallable, use_uv: bool
) -> None:
    """Only the member's own dependencies are installed"""
    if use_uv:
        member_workspace.global_config["use_uv"] = True

    lib = dockerize_member(pdm, member_workspace, member()) / "lib"

    assert (lib / "faker").is_dir()


@backends
def test_member_sibling_is_installed(
    member_workspace: Project, member: MemberFixture, pdm: PDMCallable, use_uv: bool
) -> None:
    """A sibling member depended upon by name is installed, non-editable"""
    if use_uv:
        member_workspace.global_config["use_uv"] = True

    lib = dockerize_member(pdm, member_workspace, member()) / "lib"

    assert (lib / "member_b").is_dir()
    assert not (lib / "member_b").is_symlink()
    assert not list(lib.glob("*.pth"))
    assert not list(lib.glob("__editable__*"))


@backends
def test_unrelated_member_is_not_installed(
    member_workspace: Project, member: MemberFixture, pdm: PDMCallable, use_uv: bool
) -> None:
    """Members the target does not depend on are left out"""
    if use_uv:
        member_workspace.global_config["use_uv"] = True

    lib = dockerize_member(pdm, member_workspace, member()) / "lib"

    assert "member_z" not in installed(lib)


@backends
def test_member_itself_is_not_installed(
    member_workspace: Project, member: MemberFixture, pdm: PDMCallable, use_uv: bool
) -> None:
    """The dockerized member is exposed through its sources, not installed"""
    if use_uv:
        member_workspace.global_config["use_uv"] = True

    lib = dockerize_member(pdm, member_workspace, member()) / "lib"

    assert "member_a" not in installed(lib)
    assert not list(lib.glob("member_a-*.dist-info"))


def test_transitive_sibling_is_installed(
    project: Project, add_member: AddMemberFixture, pdm: PDMCallable
) -> None:
    """Sibling members are resolved transitively"""
    add_member("member-a", dependencies=["member-b"])
    add_member("member-b", dependencies=["member-c"])
    add_member("member-c", dependencies=["Faker"])
    project.pyproject.settings["workspace"] = {"members": ["packages/*"]}
    project.pyproject.settings["dockerize"] = {"include": "*"}
    project.pyproject.metadata["requires-python"] = ">=3.10"
    project.pyproject.metadata["dependencies"] = []
    project.pyproject.write()
    target = project.core.create_project(project.root / "packages/member-a")

    lib = dockerize_member(pdm, project, target) / "lib"

    assert {"member_b", "member_c", "faker"} <= installed(lib)


def test_member_sources_are_on_pythonpath(
    member_workspace: Project, member: MemberFixture, pdm: PDMCallable
) -> None:
    """The member is not installed, so its sources are exposed instead"""
    dist = dockerize_member(pdm, member_workspace, member())

    entrypoint = (dist / "entrypoint").read_text()
    assert 'PYTHONPATH="$(pwd)/src":"$(pwd)/lib"' in entrypoint


def test_member_scripts_are_used(
    member_workspace: Project, member: MemberFixture, pdm: PDMCallable
) -> None:
    """Scripts come from the member, the workspace root ones are ignored"""
    dist = dockerize_member(pdm, member_workspace, member())

    entrypoint = (dist / "entrypoint").read_text()
    assert "serve)" in entrypoint
    assert "root-only" not in entrypoint
    assert "_private" not in entrypoint


def test_member_settings_are_used(
    member_workspace: Project, member: MemberFixture, pdm: PDMCallable
) -> None:
    """`tool.pdm.dockerize` comes from the member, the root one does not leak"""
    dist = dockerize_member(pdm, member_workspace, member())

    entrypoint = (dist / "entrypoint").read_text()
    assert "FROM_MEMBER" in entrypoint
    assert "FROM_ROOT" not in entrypoint


@backends
def test_member_bins_filters_are_used(
    member_workspace: Project,
    member: MemberFixture,
    pdm: PDMCallable,
    add_member: AddMemberFixture,
    use_uv: bool,
) -> None:
    """`include_bins`/`exclude_bins` are read from the member, not the root"""
    if use_uv:
        member_workspace.global_config["use_uv"] = True
    add_member(
        "member-a",
        dependencies=["Faker"],
        dockerize={"include": "*", "include_bins": "*", "exclude_bins": ["faker"]},
    )

    bin = dockerize_member(pdm, member_workspace, member()) / "bin"

    assert not (bin / "faker").exists()


@backends
def test_output_is_under_the_member(
    member_workspace: Project, member: MemberFixture, pdm: PDMCallable, use_uv: bool
) -> None:
    """The image content is generated in the member, not in the workspace root"""
    if use_uv:
        member_workspace.global_config["use_uv"] = True

    dist = dockerize_member(pdm, member_workspace, member())

    assert (dist / "entrypoint").is_file()
    assert os.access(dist / "entrypoint", os.X_OK)
    assert not (member_workspace.root / "dist/docker").exists()


def test_member_target_override(
    member_workspace: Project, member: MemberFixture, pdm: PDMCallable, tmp_path: Path
) -> None:
    """An explicit target wins over the member default output directory"""
    target = tmp_path / "target"

    dockerize_member(pdm, member_workspace, member(), f"-v {target}")

    assert (target / "entrypoint").is_file()
    assert (target / "lib/faker").is_dir()
    assert not (member().root / "dist/docker").exists()


@backends
def test_no_interpreter_is_resolved_in_the_member(
    member_workspace: Project, member: MemberFixture, pdm: PDMCallable, use_uv: bool
) -> None:
    """The interpreter comes from the workspace root

    `Project.python` is not workspace aware and would create a virtualenv
    and a `.pdm-python` file inside the member.
    """
    if use_uv:
        member_workspace.global_config["use_uv"] = True
    target = member()

    dockerize_member(pdm, member_workspace, target)

    assert not (target.root / ".venv").exists()
    assert not (target.root / ".pdm-python").exists()
    assert not (target.root / "__pypackages__").exists()


def test_non_distribution_member_warns(
    member_workspace: Project,
    member: MemberFixture,
    pdm: PDMCallable,
    add_member: AddMemberFixture,
) -> None:
    """A non distribution member is neither installed nor exposed"""
    # A non distribution member is not a workspace dependency, so its own
    # dependencies are not part of the workspace lock file either
    add_member("member-a", dockerize={"include": "*"}, distribution=False)
    pdm("lock", obj=member_workspace, strict=True, cleanup=False)
    target = member()

    result = pdm("dockerize -v", obj=target, strict=True)

    assert "is not a distribution" in result.output + result.stderr
    entrypoint = (target.root / "dist/docker/entrypoint").read_text()
    assert '"$(pwd)/src"' not in entrypoint


def test_member_entrypoint(
    member_workspace: Project,
    member: MemberFixture,
    pdm: PDMCallable,
    snapshot: SnapshotAssertion,
    shellcheck: ShellcheckFixture,
) -> None:
    """The generated entrypoint is a valid shell script"""
    dist = dockerize_member(pdm, member_workspace, member())

    entrypoint = (dist / "entrypoint").read_text()
    assert entrypoint == snapshot
    shellcheck(entrypoint)


def test_member_only_group_is_rejected(
    member_workspace: Project,
    member: MemberFixture,
    pdm: PDMCallable,
    add_member: AddMemberFixture,
) -> None:
    """The workspace lock file only knows about the workspace root groups"""
    member_dir = add_member("member-a", dependencies=["Faker"])
    pyproject = member_dir / "pyproject.toml"
    data = tomlkit.parse(pyproject.read_text())
    data["dependency-groups"] = {"extra": ["Faker"]}
    pyproject.write_text(tomlkit.dumps(data))
    pdm("lock", obj=member_workspace, strict=True, cleanup=False)

    result = pdm("dockerize -v -G extra", obj=member())

    assert result.exit_code != 0
    assert "Requested groups not in lockfile: extra" in result.stderr
