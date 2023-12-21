#!/usr/bin/env sh

set -eu

export PYTHONPATH=lib
export PATH=bin:$PATH

cmd=$1
shift

usage() {
    echo "Available commands"
    echo "=================="
    echo "test:something: pytest something"
    echo "ns:task2: ns:task2"
    echo "ns:task3: ns:task3"
}

case $cmd in
    test:something)
        pytest something "$@"
        ;;
    ns:task2)
        ns:task2 "$@"
        ;;
    ns:task3)
        ns:task3 "$@"
        ;;
    *)
        usage
        ;;
esac
