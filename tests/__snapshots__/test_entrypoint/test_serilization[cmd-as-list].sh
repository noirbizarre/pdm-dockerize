#!/usr/bin/env sh

set -euo pipefail

export PYTHONPATH=./lib
export PATH=./bin:$PATH

cmd=$1
shift

usage() {
    echo "Available commands"
    echo "=================="
    echo "test: pytest --with --params"
}

case $cmd in
    test)
        pytest --with --params "$@"
        ;;
    *)
        usage
        ;;
esac
