#!/bin/sh

export PYTHONPATH=./lib
export PATH=./bin:$PATH

usage() {
    echo "Available commands"
    echo "=================="
    echo "test: pytest"
    echo "ns:task1: ns:task1"
}

case ${1} in
    test)
        pytest
        ;;
    ns:task1)
        ns:task1
        ;;
    *)
        usage
        ;;
esac
