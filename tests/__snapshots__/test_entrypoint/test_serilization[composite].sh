#!/usr/bin/env sh

set -eu

export PYTHONPATH=lib
export PATH=bin:$PATH

cmd=$1
shift

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
