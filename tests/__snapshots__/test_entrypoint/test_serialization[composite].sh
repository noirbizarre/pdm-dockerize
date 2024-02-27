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
    echo "test: first ➤ second"
}

case $cmd in
    test)
        first "$@"
        second "$@"
        ;;
    *)
        usage
        ;;
esac
