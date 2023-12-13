#!/bin/sh

function usage() {
    echo "Available commands"
    echo -e "==================\n"
    echo "test: pytest"
}

case ${1} in
    test)
        set -o allexport
        source .env
        set +o allexport
        WHATEVER="42"
        pytest
        ;;
    *)
        usage
        ;;
esac
