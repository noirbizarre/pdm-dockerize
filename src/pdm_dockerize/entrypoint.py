from __future__ import annotations

import io
import re
from typing import TYPE_CHECKING

from pdm.cli.commands.run import TaskRunner

from . import filters

if TYPE_CHECKING:
    from pdm.cli.commands.run import Task
    from pdm.cli.hooks import HookManager
    from pdm.project import Project

    from .config import DockerizeSettings


INDENT = 4 * " "
RE_CALL = re.compile(r"(?P<pkg>[\w\d_.]+):(?P<fn>[\w\d_]+)(?:\((?P<args>.*?)\))?")


def select_scripts(project: Project) -> list[list]:
    """
    List all scripts eligible to docker entryopint according filtering
    """
    settings: DockerizeSettings = project.pyproject.settings.get("dockerize", {})
    include = filters.parse(settings, "include")
    exclude = filters.parse(settings, "exclude")
    scripts = project.pyproject.settings.get("scripts", {}).keys()
    included = [script for script in scripts if filters.match(script, include)]
    return [script for script in included if not filters.match(script, exclude)]


def project_entrypoint(project: Project, hooks: HookManager) -> str:
    """Generate a `sh` entrypoint for a given project"""
    out = io.StringIO()
    runner = TaskRunner(project, hooks=hooks)

    out.write("#!/bin/sh\n\n")
    out.write(python_env())
    out.write("\n")
    out.write(usage(project, runner))
    out.write("\n")
    out.write("case ${1} in\n")

    for script in select_scripts(project):
        task = runner.get_task(script)
        out.write(case(task))

    out.write(f"{INDENT}*)\n")
    out.write(f"{2 * INDENT}usage\n")
    out.write(f"{2 * INDENT};;\n")
    out.write("esac\n")

    return out.getvalue()


def python_env() -> str:
    """Generate the environment variables statements"""
    out = io.StringIO()
    out.write("export PYTHONPATH=./lib\n")
    out.write("export PATH=./bin:$PATH\n")
    return out.getvalue()


def usage(project: Project, runner: TaskRunner) -> str:
    """Render the entrypoint usage/help"""
    out = io.StringIO()
    out.write("usage() {\n")
    out.write(f'{INDENT}echo "Available commands"\n')
    out.write(f'{INDENT}echo "=================="\n')

    for script in select_scripts(project):
        task = runner.get_task(script)
        if task is None:
            continue
        if task.kind == "cmd" and isinstance(task.args, list):
            out.write(f'{INDENT}echo "{script}: {" ".join(task.args)}"\n')
        else:
            out.write(f'{INDENT}echo "{script}: {task.short_description}"\n')
    out.write("}\n")
    return out.getvalue()


def case(task: Task) -> str:
    """Render a script case for a given task"""
    out = io.StringIO()
    out.write(f"{INDENT}{task.name})\n")

    if (envfile := task.options.get("env_file")) and isinstance(envfile, str):
        out.write(f"{2 * INDENT}set -o allexport\n")
        out.write(f"{2 * INDENT}source {envfile}\n")
        out.write(f"{2 * INDENT}set +o allexport\n")

    for var, value in task.options.get("env", {}).items():
        out.write(f'{2 * INDENT}{var}="{value}"\n')

    if isinstance(envfile, dict) and (override := envfile.get("override")):
        out.write(f"{2 * INDENT}set -o allexport\n")
        out.write(f"{2 * INDENT}source {override}\n")
        out.write(f"{2 * INDENT}set +o allexport\n")

    if task.kind == "call":
        if not (m := RE_CALL.match(task.args)):
            raise ValueError("Unparsable call task {tasks.name}: {tasks.args}")
        pkg = m.group("pkg")
        fn = m.group("fn")
        args = m.group("args") or ""
        out.write(f'{2 * INDENT}python -c "from {pkg} import {fn}; {fn}({args})"\n')
    elif task.kind == "cmd" and isinstance(task.args, list):
        out.write(f"{2 * INDENT}{' '.join(task.args)}\n")
    elif task.kind == "composite":
        for cmd in task.args:
            out.write(f"{2 * INDENT}{cmd}\n")
    else:
        out.write(f"{2 * INDENT}{task.args}\n")
    out.write(f"{2 * INDENT};;\n")
    return out.getvalue()
