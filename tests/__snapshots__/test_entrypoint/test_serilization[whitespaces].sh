#!/usr/bin/env sh

set -eu

export PYTHONPATH=lib
export PATH=bin:$PATH

cmd=$1
shift

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
