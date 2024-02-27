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
    echo "test: pytest"
    echo "ns:task1: ns:task1"
}

case $cmd in
    test)
        pytest "$@"
        ;;
    ns:task1)
        ns:task1 "$@"
        ;;
    *)
        usage
        ;;
esac
