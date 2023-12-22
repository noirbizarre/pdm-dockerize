#!/usr/bin/env sh

set -eu

dirname=$(dirname $0)
cmd=${1:-""}
[ $cmd ] && shift
cd $dirname > /dev/null

export PYTHONPATH=$(pwd)/src:$(pwd)/lib
export PATH=$(pwd)/bin:$PATH

usage() {
    echo "Available commands"
    echo "=================="
}

case $cmd in
    *)
        usage
        ;;
esac
