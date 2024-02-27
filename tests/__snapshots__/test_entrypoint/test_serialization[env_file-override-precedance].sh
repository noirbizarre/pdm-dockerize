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
}

case $cmd in
    test)
        WHATEVER="42"
        export WHATEVER
        set -o allexport
        # shellcheck source=/dev/null
        [ -f .env ] && . .env || echo '.env is ignored as it does not exist.'
        set +o allexport
        pytest "$@"
        ;;
    *)
        usage
        ;;
esac
