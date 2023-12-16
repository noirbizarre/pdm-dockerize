from __future__ import annotations

import io
import re
import shlex
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING

from pdm.cli.commands.run import TaskRunner, exec_opts

from . import filters

if TYPE_CHECKING:
    from pdm.cli.commands.run import Task
    from pdm.cli.hooks import HookManager
    from pdm.project import Project

    from .config import DockerizeSettings


INDENT = 4 * " "
RE_CALL = re.compile(r"(?P<pkg>[\w\d_.]+):(?P<fn>[\w\d_]+)(?:\((?P<args>.*?)\))?")


@dataclass
class ProjectEntrypoint:
    project: Project
    hooks: HookManager

    @cached_property
    def settings(self) -> DockerizeSettings:
        return self.project.pyproject.settings.get("dockerize", {})

    @cached_property
    def runner(self) -> TaskRunner:
        return TaskRunner(self.project, hooks=self.hooks)

    def select_scripts(self) -> list[str]:
        """
        List all scripts eligible to docker entrypoint according filtering
        """
        include = filters.parse(self.settings, "include")
        exclude = filters.parse(self.settings, "exclude")
        scripts = self.project.pyproject.settings.get("scripts", {}).keys()
        scripts = [script for script in scripts if not script.startswith("_")]
        included = [script for script in scripts if filters.match(script, include)]
        return [script for script in included if not filters.match(script, exclude)]

    def __str__(self) -> str:
        return self.as_script()

    def as_script(self) -> str:
        """Render the `sh` entrypoint"""
        out = io.StringIO()

        out.write("#!/bin/sh\n\n")
        out.write(self.python_env())
        out.write("\n")
        out.write(self.usage())
        out.write("\n")
        out.write("case ${1} in\n")

        for script in self.select_scripts():
            out.write(self.case(script))

        out.write(f"{INDENT}*)\n")
        out.write(f"{2 * INDENT}usage\n")
        out.write(f"{2 * INDENT};;\n")
        out.write("esac\n")

        return out.getvalue()

    def python_env(self) -> str:
        """Generate the environment variables statements"""
        out = io.StringIO()
        out.write("export PYTHONPATH=./lib\n")
        out.write("export PATH=./bin:$PATH\n")
        return out.getvalue()

    def usage(self) -> str:
        """Render the entrypoint usage/help"""
        out = io.StringIO()
        out.write("usage() {\n")
        out.write(f'{INDENT}echo "Available commands"\n')
        out.write(f'{INDENT}echo "=================="\n')

        for script in self.select_scripts():
            task = self.runner.get_task(script)
            if task is None:
                continue
            if task.kind == "cmd" and isinstance(task.args, list):
                description = " ".join(task.args)
            else:
                description = task.short_description
            if "\n" in description:
                description = f"{description.splitlines()[0]}…"
            out.write(f'{INDENT}echo "{script}: {description}"\n')
        out.write("}\n")
        return out.getvalue()

    def case(self, script: str) -> str:
        """Render a script case for a given task"""
        task = self.runner.get_task(script)
        out = io.StringIO()
        out.write(f"{INDENT}{task.name})\n")

        if pre := self.runner.get_task(f"pre_{script}"):
            out.write(self.script_for(pre))

        out.write(self.script_for(task))

        if post := self.runner.get_task(f"post_{script}"):
            out.write(self.script_for(post))

        out.write(f"{2 * INDENT};;\n")
        return out.getvalue()

    def script_for(self, task: Task, args: str = "") -> str:
        """Render the script part for a single task"""
        out = io.StringIO()
        opts = exec_opts(self.runner.global_options, task.options)
        if (envfile := opts.get("env_file")) and isinstance(envfile, str):
            out.write(self.source_env(envfile))

        for var, value in opts.get("env", {}).items():
            out.write(f'{2 * INDENT}{var}="{value}"\n')

        if isinstance(envfile, dict) and (override := envfile.get("override")):
            out.write(self.source_env(override))

        if task.kind == "call":
            out.write(self.call_script(task))
        elif task.kind == "cmd":
            out.write(self.cmd_script(task))
        elif task.kind == "composite":
            out.write(self.composite_script(task))
        else:
            out.write(self.shell_script(task))
        return out.getvalue()

    def source_env(self, envfile: str) -> str:
        out = io.StringIO()
        out.write(f"{2 * INDENT}set -o allexport\n")
        out.write(f"{2 * INDENT}source {envfile}\n")
        out.write(f"{2 * INDENT}set +o allexport\n")
        return out.getvalue()

    def cmd_script(self, task: Task) -> str:
        args = task.args if isinstance(task.args, list) else shlex.split(task.args)
        return f"{2 * INDENT}{' '.join(args)}\n"

    def call_script(self, task: Task) -> str:
        if not (m := RE_CALL.match(task.args)):
            raise ValueError("Unparsable call task {tasks.name}: {tasks.args}")
        pkg = m.group("pkg")
        fn = m.group("fn")
        args = m.group("args") or ""
        return f'{2 * INDENT}python -c "from {pkg} import {fn}; {fn}({args})"\n'

    def shell_script(self, task: Task) -> str:
        out = io.StringIO()
        for line in task.args.splitlines():
            out.write(f"{2 * INDENT}{line}\n")
        return out.getvalue()

    def composite_script(self, task: Task) -> str:
        out = io.StringIO()
        for cmd in task.args:
            args = shlex.split(cmd)
            normalized = " ".join(args)
            out.write(f"{2 * INDENT}{normalized}\n")
        return out.getvalue()
