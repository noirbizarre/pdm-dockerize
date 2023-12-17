#!/usr/bin/env sh

set -euo pipefail

export PYTHONPATH=./lib
export PATH=./bin:$PATH

cmd=$1
shift

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
