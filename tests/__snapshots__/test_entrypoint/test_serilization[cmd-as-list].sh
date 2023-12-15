#!/bin/sh

export PYTHONPATH=./lib
export PATH=./bin:$PATH

usage() {
    echo "Available commands"
    echo "=================="
    echo "test: pytest --with --params"
}

case ${1} in
    test)
        pytest --with --params
        ;;
    *)
        usage
        ;;
esac
