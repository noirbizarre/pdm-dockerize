#!/bin/sh

export PYTHONPATH=./lib
export PATH=./bin:$PATH

function usage() {
    echo "Available commands"
    echo -e "==================\n"
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
