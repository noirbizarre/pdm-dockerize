#!/usr/bin/env sh

set -eu

export PYTHONPATH=lib
export PATH=bin:$PATH

cmd=$1
shift

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
