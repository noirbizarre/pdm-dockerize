#!/bin/sh

export PYTHONPATH=./lib
export PATH=./bin:$PATH

function usage() {
    echo "Available commands"
    echo -e "==================\n"
    echo "test: pytest"
}

case ${1} in
    test)
        set -o allexport
        source .env
        set +o allexport
        pytest
        ;;
    *)
        usage
        ;;
esac
