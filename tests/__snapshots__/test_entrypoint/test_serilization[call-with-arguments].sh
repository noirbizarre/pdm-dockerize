#!/usr/bin/env sh

set -eu

export PYTHONPATH=lib
export PATH=bin:$PATH

cmd=$1
shift

usage() {
    echo "Available commands"
    echo "=================="
    echo "test: my.app:main('dev', key='value')"
}

case $cmd in
    test)
        python -c "from my.app import main; main('dev', key='value')"
        ;;
    *)
        usage
        ;;
esac
