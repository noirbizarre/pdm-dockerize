#!/usr/bin/env sh

set -eu

export PYTHONPATH=lib
export PATH=bin:$PATH

cmd=$1
shift

usage() {
    echo "Available commands"
    echo "=================="
    echo "cmd: cmd.before {args:default value} cmd.after"
    echo "shell: shell.before {args:default value} shell.after"
    echo "composite: cmd --something ➤ shell {args:default value}"
}

case $cmd in
    cmd)
        cmd.before "${@:-default value}" cmd.after
        ;;
    shell)
        shell.before "${@:-default value}" shell.after
        ;;
    composite)
        cmd.before "${@:-default value}" cmd.after --something
        shell.before "${@:-default value}" shell.after "${@:-default value}"
        ;;
    *)
        usage
        ;;
esac
