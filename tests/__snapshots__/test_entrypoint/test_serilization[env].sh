#!/bin/sh

function usage() {
    echo "Available commands"
    echo -e "==================\n"
    echo "test: pytest"
}

case ${1} in
    test)
        WHATEVER="42"
        OTHER="value"
        pytest
        ;;
    *)
        usage
        ;;
esac
