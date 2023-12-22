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
    echo "pre_test: pre"
    echo "test: pytest"
    echo "post_test: post"
}

case $cmd in
    pre_test)
        pre "$@"
        ;;
    test)
        pre "$@"
        pytest "$@"
        post "$@"
        ;;
    post_test)
        post "$@"
        ;;
    *)
        usage
        ;;
esac
