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
}

case $cmd in
    test)
        WHATEVER="42"
        OTHER="new-value"
        pytest "$@"
        ;;
    *)
        usage
        ;;
esac
