#!/bin/sh

function usage() {
    echo "Available commands"
    echo -e "==================\n"
    echo "test: pytest"
    echo "ns:task1: ns:task1"
}

case ${1} in
    test)
        pytest
        ;;
    ns:task1)
        ns:task1
        ;;
    *)
        usage
        ;;
esac
