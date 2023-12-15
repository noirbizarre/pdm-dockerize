#!/bin/sh

export PYTHONPATH=./lib
export PATH=./bin:$PATH

usage() {
    echo "Available commands"
    echo "=================="
    echo "test: my.app:main('dev', key='value')"
}

case ${1} in
    test)
        python -c "from my.app import main; main('dev', key='value')"
        ;;
    *)
        usage
        ;;
esac
