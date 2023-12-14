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
        WHATEVER="42"
        OTHER="value"
        pytest
        ;;
    *)
        usage
        ;;
esac
