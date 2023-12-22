#!/usr/bin/env sh

set -eu

dirname=$(dirname $0)
cmd=${1:-""}
[ $cmd ] && shift
cd $dirname > /dev/null

export PYTHONPATH=$(pwd)/lib
export PATH=$(pwd)/bin:$PATH

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
