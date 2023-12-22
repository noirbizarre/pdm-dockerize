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
    echo "test: pytest"
    echo "ns:task1: ns:task1"
}

case $cmd in
    test)
        pytest "$@"
        ;;
    ns:task1)
        ns:task1 "$@"
        ;;
    *)
        usage
        ;;
esac
