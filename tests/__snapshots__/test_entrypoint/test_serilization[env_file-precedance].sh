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
        set -o allexport
        [ -f .env ] && . .env || echo '.env is ignored as it does not exist.'
        set +o allexport
        WHATEVER="42"
        pytest "$@"
        ;;
    *)
        usage
        ;;
esac
