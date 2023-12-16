#!/usr/bin/env sh

export PYTHONPATH=./lib
export PATH=./bin:$PATH

cmd=$1
shift

usage() {
    echo "Available commands"
    echo "=================="
}

case $cmd in
    *)
        usage
        ;;
esac
