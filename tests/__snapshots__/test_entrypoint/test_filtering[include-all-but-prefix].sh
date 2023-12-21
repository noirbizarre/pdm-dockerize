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
    echo "test:something: pytest something"
}

case $cmd in
    test)
        pytest "$@"
        ;;
    test:something)
        pytest something "$@"
        ;;
    *)
        usage
        ;;
esac
