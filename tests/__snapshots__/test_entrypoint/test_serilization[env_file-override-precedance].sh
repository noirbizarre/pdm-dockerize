#!/bin/sh

export PYTHONPATH=./lib
export PATH=./bin:$PATH

usage() {
    echo "Available commands"
    echo "=================="
    echo "test: pytest"
}

case ${1} in
    test)
        WHATEVER="42"
        set -o allexport
        source .env
        set +o allexport
        pytest
        ;;
    *)
        usage
        ;;
esac
