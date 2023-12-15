#!/bin/sh

export PYTHONPATH=./lib
export PATH=./bin:$PATH

usage() {
    echo "Available commands"
    echo "=================="
    echo "test: pytest"
    echo "test:something: pytest something"
}

case ${1} in
    test)
        pytest
        ;;
    test:something)
        pytest something
        ;;
    *)
        usage
        ;;
esac
