#!/bin/sh

export PYTHONPATH=./lib
export PATH=./bin:$PATH

usage() {
    echo "Available commands"
    echo "=================="
    echo "pre_test: pre"
    echo "test: pytest"
    echo "post_test: post"
}

case ${1} in
    pre_test)
        pre
        ;;
    test)
        pre
        pytest
        post
        ;;
    post_test)
        post
        ;;
    *)
        usage
        ;;
esac
