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
    echo "ns:task2: ns:task2"
    echo "ns:task3: ns:task3"
}

case $cmd in
    ns:task2)
        ns:task2 "$@"
        ;;
    ns:task3)
        ns:task3 "$@"
        ;;
    *)
        usage
        ;;
esac
