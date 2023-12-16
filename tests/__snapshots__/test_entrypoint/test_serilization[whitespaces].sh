#!/bin/sh

export PYTHONPATH=./lib
export PATH=./bin:$PATH

usage() {
    echo "Available commands"
    echo "=================="
    echo "cmd: whitespaces…"
    echo "shell: whitespaces…"
    echo "composite: whitespaces…"
}

case ${1} in
    cmd)
        whitespaces are ignored
        ;;
    shell)
        whitespaces
            should be
        preserved
        ;;
    composite)
        whitespaces are ignored
        ;;
    *)
        usage
        ;;
esac
