#!/usr/bin/env sh

set -eu

export PYTHONPATH=lib
export PATH=bin:$PATH

cmd=$1
shift

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
