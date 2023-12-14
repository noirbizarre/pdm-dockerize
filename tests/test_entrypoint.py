from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import pytest
from pdm.cli.hooks import HookManager

from pdm_dockerize.entrypoint import project_entrypoint

if TYPE_CHECKING:
    from pdm.project import Project
    from syrupy import SnapshotAssertion


def entrypoint_for(project: Project, hooks: HookManager | None = None) -> str:
    return project_entrypoint(project, hooks or HookManager(project))


CASES = {
    "no_script": {},
    "cmd-as-str": {"test": "pytest"},
    "cmd-as-dict": {"test": {"cmd": "pytest"}},
    "cmd-as-list": {"test": {"cmd": ["pytest", "--with", "--params"]}},
    "shell": {"test": {"shell": "pytest"}},
    "call": {"test": {"call": "my.app:main"}},
    "call-with-arguments": {"test": {"call": "my.app:main('dev', key='value')"}},
    "composite": {"test": {"composite": ["first", "second"]}},
    "env": {"test": {"cmd": "pytest", "env": {"WHATEVER": "42", "OTHER": "value"}}},
    "env_file": {"test": {"cmd": "pytest", "env_file": ".env"}},
    "env_file-override": {"test": {"cmd": "pytest", "env_file": {"override": ".env"}}},
    "env_file-precedance": {
        "test": {"cmd": "pytest", "env": {"WHATEVER": "42"}, "env_file": ".env"}
    },
    "env_file-override-precedance": {
        "test": {"cmd": "pytest", "env": {"WHATEVER": "42"}, "env_file": {"override": ".env"}}
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
