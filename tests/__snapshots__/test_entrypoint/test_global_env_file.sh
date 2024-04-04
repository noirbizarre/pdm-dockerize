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
set -o allexport
# shellcheck source=/dev/null
[ -f docker.env ] && . docker.env || echo 'docker.env is ignored as it does not exist.'
set +o allexport

usage() {
    echo "Available commands"
    echo "=================="
    echo "hello: echo 'Hello'"
}

case $cmd in
    hello)
        echo 'Hello' "$@"
        ;;
    *)
        usage
        ;;
esac
