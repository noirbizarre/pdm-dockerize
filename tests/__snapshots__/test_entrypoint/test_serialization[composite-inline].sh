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
    echo "command: _helper something"
}

case $cmd in
    command)
        should be inlined something "$@"
        ;;
    *)
        usage
        ;;
esac
