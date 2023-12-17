#!/usr/bin/env sh

export PYTHONPATH=./lib
export PATH=./bin:$PATH

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
        [[ -f .env ]] && . .env
        set +o allexport
        pytest "$@"
        ;;
    *)
        usage
        ;;
esac
