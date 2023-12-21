#!/usr/bin/env sh

set -eu

export PYTHONPATH=lib
export PATH=bin:$PATH

cmd=$1
shift

usage() {
    echo "Available commands"
    echo "=================="
    echo "cmd: cmd.before {args} cmd.after"
    echo "shell: shell.before {args} shell.after"
    echo "composite: cmd --something ➤ shell {args}"
}

case $cmd in
    cmd)
        cmd.before "$@" cmd.after
        ;;
    shell)
        shell.before "$@" shell.after
        ;;
    composite)
        cmd.before "$@" cmd.after --something
        shell.before "$@" shell.after "$@"
        ;;
    *)
        usage
        ;;
esac
