from __future__ import annotations

from dataclasses import dataclass
from textwrap import dedent
from typing import TYPE_CHECKING, Any

import pytest
from pdm.cli.hooks import HookManager

from pdm_dockerize.entrypoint import ProjectEntrypoint

if TYPE_CHECKING:
    from pdm.project import Project
    from syrupy import SnapshotAssertion


def entrypoint_for(project: Project, hooks: HookManager | None = None) -> str:
    return str(ProjectEntrypoint(project, hooks or HookManager(project)))


CASES = {
    "no_script": {},
    "cmd-as-str": {"test": "pytest"},
    "cmd-as-dict": {"test": {"cmd": "pytest"}},
    "cmd-as-list": {"test": {"cmd": ["pytest", "--with", "--params"]}},
    "shell": {"test": {"shell": "pytest"}},
    "call": {"test": {"call": "my.app:main"}},
    "call-with-arguments": {"test": {"call": "my.app:main('dev', key='value')"}},
    "composite": {"test": {"composite": ["first", "second"]}},
    "composite-inline": {
        "_helper": "should be inlined",
        "command": {"composite": ["_helper something"]},
    },
    "env": {"test": {"cmd": "pytest", "env": {"WHATEVER": "42", "OTHER": "value"}}},
    "shared-env": {
        "_": {"env": {"WHATEVER": "42", "OTHER": "value"}},
        "test": {"cmd": "pytest", "env": {"OTHER": "new-value"}},
    },
    "env_file": {"test": {"cmd": "pytest", "env_file": ".env"}},
    "shared-env_file": {
        "_": {"env_file": ".env"},
        "test": {"cmd": "pytest"},
    },
    "env_file-override": {"test": {"cmd": "pytest", "env_file": {"override": ".env"}}},
    "env_file-precedance": {
        "test": {"cmd": "pytest", "env": {"WHATEVER": "42"}, "env_file": ".env"}
    },
    "env_file-override-precedance": {
        "test": {"cmd": "pytest", "env": {"WHATEVER": "42"}, "env_file": {"override": ".env"}}
    },
    "pre-post": {
        "pre_test": "pre",
        "test": "pytest",
        "post_test": "post",
    },
    "whitespaces": {
        "cmd": dedent(
            """\
            whitespaces
                are
                    ignored
            """
        ),
        "shell": {
            "shell": dedent(
                """\
                whitespaces
                    should be
                preserved
                """
            )
        },
        "composite": {
            "composite": [
                dedent(
                    """\
                    whitespaces
                        are
                            ignored
                    """
                )
            ]
        },
    },
    "args-placeholder": {
        "cmd": "cmd.before {args} cmd.after",
        "shell": {"shell": "shell.before {args} shell.after"},
        "composite": {"composite": ["cmd --something", "shell {args}"]},
    },
    "args-placeholder-with-defaults": {
        "cmd": "cmd.before {args:default value} cmd.after",
        "shell": {"shell": "shell.before {args:default value} shell.after"},
        "composite": {"composite": ["cmd --something", "shell {args:default value}"]},
    },
}


@pytest.mark.parametrize("scripts", [pytest.param(scripts, id=id) for id, scripts in CASES.items()])
def test_serilization(project: Project, snapshot: SnapshotAssertion, scripts: dict[str, Any]):
    project.pyproject.settings["dockerize"] = {"include": "*"}
    project.pyproject.settings["scripts"] = scripts
    assert entrypoint_for(project) == snapshot


@dataclass
class FilterCase:
    id: str
    include: str | list[str] | None = None
    exclude: str | list[str] | None = None


FILTER_CASES = (
    FilterCase("no-filter"),
    FilterCase("include-all", include="*"),
    FilterCase("include-list", include=["test", "ns:task1"]),
    FilterCase("exclude-all", include="*", exclude="*"),
    FilterCase("exclude-list", include="*", exclude=["test", "ns:task1"]),
    FilterCase("include-all-but-prefix", include="*", exclude="ns:*"),
    FilterCase("include-prefix-except", include="ns:*", exclude="ns:task1"),
)


@pytest.mark.parametrize("case", [pytest.param(case, id=case.id) for case in FILTER_CASES])
def test_filtering(project: Project, snapshot: SnapshotAssertion, case: FilterCase):
    project.pyproject.settings["scripts"] = {
        "test": "pytest",
        "test:something": "pytest something",
        "ns:task1": "ns:task1",
        "ns:task2": "ns:task2",
        "ns:task3": "ns:task3",
    }
    dockerize = {}
    if case.include is not None:
        dockerize["include"] = case.include
    if case.exclude is not None:
        dockerize["exclude"] = case.exclude
    project.pyproject.settings["dockerize"] = dockerize
    assert entrypoint_for(project) == snapshot


def test_pythonpath_explicit_src_layout(project: Project, snapshot: SnapshotAssertion):
    project.pyproject._data["build-system"] = {
        "requires": ["pdm-backend"],
        "build-backend": "pdm.backend",
    }
    project.pyproject.settings["build"] = {"package-dir": "src"}
    assert entrypoint_for(project) == snapshot


def test_pythonpath_implicit_src_layout(project: Project, snapshot: SnapshotAssertion):
    project.pyproject._data["build-system"] = {
        "requires": ["pdm-backend"],
        "build-backend": "pdm.backend",
    }
    pkg_dir = project.root / "src/pkg"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    pkg_init = pkg_dir / "__init__.py"
    pkg_init.write_text("")
    assert entrypoint_for(project) == snapshot
