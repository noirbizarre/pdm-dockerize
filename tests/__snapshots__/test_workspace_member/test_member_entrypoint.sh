#!/usr/bin/env sh

set -eu

dirname=$(dirname "$0")
cmd=${1:-""}
[ "$cmd" ] && shift
cd "$dirname" > /dev/null

PYTHONPATH="$(pwd)/src":"$(pwd)/lib"
export PYTHONPATH
PATH="$(pwd)/bin":"$PATH"
export PATH
FROM_MEMBER="1"
export FROM_MEMBER

usage() {
    echo "Available commands"
    echo "=================="
    echo "serve: echo serving"
}

case $cmd in
    serve)
        echo serving "$@"
        ;;
    *)
        usage
        ;;
esac
