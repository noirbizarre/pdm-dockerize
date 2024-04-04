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
VAR="42"
export VAR
LAST="value"
export LAST

usage() {
    echo "Available commands"
    echo "=================="
    echo "hello: echo 'Hello'"
}

case $cmd in
    hello)
        echo 'Hello' "$@"
        ;;
    *)
        usage
        ;;
esac
