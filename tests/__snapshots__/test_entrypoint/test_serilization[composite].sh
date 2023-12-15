#!/bin/sh

export PYTHONPATH=./lib
export PATH=./bin:$PATH

usage() {
    echo "Available commands"
    echo "=================="
    echo "test: first ➤ second"
}

case ${1} in
    test)
        first
        second
        ;;
    *)
        usage
        ;;
esac
