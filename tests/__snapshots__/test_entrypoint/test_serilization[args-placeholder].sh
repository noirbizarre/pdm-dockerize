#!/usr/bin/env sh

set -eu

dirname=$(dirname "$0")
cmd=${1:-""}
[ "$cmd" ] && shift
cd "$dirname" > /dev/null

PYTHONPATH="$(pwd)/lib"
export PYTHONPATH
PATH="$(pwd)/bin":"$PATH"
export PATH

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
