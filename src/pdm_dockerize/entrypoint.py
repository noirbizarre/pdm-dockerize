from __future__ import annotations

import io
import re
import shlex
from dataclasses import dataclass
from functools import cached_property
from typing import TYPE_CHECKING

from pdm.cli.commands.run import RE_ARGS_PLACEHOLDER, TaskRunner, exec_opts

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

        out.write("#!/usr/bin/env sh\n\n")
        out.write("set -eu\n\n")
        out.write('dirname=$(dirname "$0")\n')
        out.write('cmd=${1:-""}\n')
        out.write('[ "$cmd" ] && shift\n')
        out.write('cd "$dirname" > /dev/null\n')
        out.write("\n")
        out.write(self.export_env())
        out.write("\n")
        out.write(self.usage())
        out.write("\n")
        out.write("case $cmd in\n")

        for script in self.select_scripts():
            out.write(self.case(script))

        out.write(f"{INDENT}*)\n")
        out.write(f"{2 * INDENT}usage\n")
        out.write(f"{2 * INDENT};;\n")
        out.write("esac\n")

        return out.getvalue()

    def export_env(self) -> str:
        """Export the environment variables"""
        out = io.StringIO()
        path = ["$(pwd)/bin", "$PATH"]
        pythonpath = ["$(pwd)/lib"]
        if package_dir := self.get_package_dir():
            pythonpath.insert(0, package_dir)
        out.write(self.export_var("PYTHONPATH", ":".join(f'"{p}"' for p in pythonpath)))
        out.write(self.export_var("PATH", ":".join(f'"{p}"' for p in path)))
        if env := self.settings.get("env"):
            for name, value in env.items():
                out.write(self.export_var(name, str(value)))
        if env_file := self.settings.get("env_file"):
            out.write(self.source_env(env_file))
        return out.getvalue()

    def export_var(self, name: str, value: str, indent: int = 0) -> str:
        prefix = INDENT * indent
        out = io.StringIO()
        if not value.startswith('"') or not value.endswith('"'):
            value = f'"{value}"'
        out.write(f"{prefix}{name}={value}\n")
        out.write(f"{prefix}export {name}\n")
        return out.getvalue()

    def get_package_dir(self) -> str | None:
        """An optional directory containing the project sources"""
        # TODO: find a better way to identify package-dir
        build_system = self.project.backend.build_system()
        if not build_system.get("build-backend") == "pdm.backend":
            return None
        default = "src" if self.project.root.joinpath("src").exists() else None
        pkgdir = self.project.pyproject.settings.get("build", {}).get("package-dir", default)
        return f"$(pwd)/{pkgdir}" if pkgdir else None

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

    def script_for(self, task: Task, params: str | None = None) -> str:
        """Render the script part for a single task"""
        out = io.StringIO()
        opts = exec_opts(self.runner.global_options, task.options)
        if (envfile := opts.get("env_file")) and isinstance(envfile, str):
            out.write(self.source_env(envfile, indent=2))

        for var, value in (opts.get("env") or {}).items():
            out.write(self.export_var(var, value, indent=2))

        if isinstance(envfile, dict) and (override := envfile.get("override")):
            out.write(self.source_env(override, indent=2))

        if task.kind == "call":
            out.write(self.call_script(task))
        elif task.kind == "cmd":
            out.write(self.cmd_script(task, params))
        elif task.kind == "composite":
            out.write(self.composite_script(task, params))
        else:
            out.write(self.shell_script(task, params))
        return out.getvalue()

    def source_env(self, envfile: str, indent: int = 0) -> str:
        out = io.StringIO()
        prefix = indent * INDENT
        out.write(f"{prefix}set -o allexport\n")
        out.write(f"{prefix}# shellcheck source=/dev/null\n")
        out.write(f"{prefix}[ -f {envfile} ] && . {envfile} ")
        out.write(f"|| echo '{envfile} is ignored as it does not exist.'\n")
        out.write(f"{prefix}set +o allexport\n")
        return out.getvalue()

    def cmd_script(self, task: Task, params: str | None = None) -> str:
        if isinstance(task.args, str):
            script, interpolated = self.interpolate(task.args)
            script = " ".join(shlex.split(script, posix=False))
        else:
            script, interpolated = self.interpolate(shlex.join(task.args))
        if not (params or interpolated):
            params = '"$@"'
        if params:
            script += f" {params}"
        return f"{2 * INDENT}{script}\n"

    def call_script(self, task: Task) -> str:
        if not (m := RE_CALL.match(task.args)):
            raise ValueError("Unparsable call task {tasks.name}: {tasks.args}")
        pkg = m.group("pkg")
        fn = m.group("fn")
        args = m.group("args") or ""
        return f'{2 * INDENT}python -c "from {pkg} import {fn}; {fn}({args})"\n'

    def shell_script(self, task: Task, params: str | None = None) -> str:
        out = io.StringIO()
        args, interpolated = self.interpolate(task.args)
        lines = args.splitlines()
        for idx, line in enumerate(lines, 1):
            out.write(f"{2 * INDENT}{line}")
            if idx == len(lines):
                if params:
                    out.write(f" {params}")
                if not interpolated:
                    out.write(' "$@"')
            out.write("\n")
        return out.getvalue()

    def composite_script(self, task: Task, params: str | None = None) -> str:
        out = io.StringIO()
        cmds, interpolated = zip(*(self.interpolate(cmd) for cmd in task.args))
        if not params and not any(interpolated):
            params = '"$@"'
        for cmd in cmds:
            args = shlex.split(cmd, posix=False)
            if inline := self.runner.get_task(args[0]):
                args = args[1:]
                script = " ".join(args)
                if params:
                    script += f" {params}"
                out.write(self.script_for(inline, script))
            else:
                out.write(f"{2 * INDENT}{' '.join(args)} {params or ''}\n")
        return out.getvalue()

    def interpolate(self, script: str) -> tuple[str, bool]:
        """Interpolate the `{args:[defaults]} placeholder in a string"""

        def replace(m: re.Match[str]) -> str:
            if default := m.group("default"):
                return f'"${{@:-{default}}}"'
            return '"$@"'

        interpolated, count = RE_ARGS_PLACEHOLDER.subn(replace, script)
        return interpolated, count > 0
