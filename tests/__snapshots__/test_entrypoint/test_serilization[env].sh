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
        OTHER="value"
        pytest
        ;;
    *)
        usage
        ;;
esac
