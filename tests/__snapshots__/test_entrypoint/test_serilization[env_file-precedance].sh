#!/usr/bin/env sh

set -eu

dirname=$(dirname $0)
cmd=${1:-""}
[ $cmd ] && shift
cd $dirname > /dev/null

export PYTHONPATH=$(pwd)/lib
export PATH=$(pwd)/bin:$PATH

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
