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
    echo "cmd: whitespaces…"
    echo "shell: whitespaces…"
    echo "composite: whitespaces…"
}

case $cmd in
    cmd)
        whitespaces are ignored "$@"
        ;;
    shell)
        whitespaces
            should be
        preserved "$@"
        ;;
    composite)
        whitespaces are ignored "$@"
        ;;
    *)
        usage
        ;;
esac
