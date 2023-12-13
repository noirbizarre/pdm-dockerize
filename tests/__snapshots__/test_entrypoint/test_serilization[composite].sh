#!/bin/sh

function usage() {
    echo "Available commands"
    echo -e "==================\n"
    echo "test: first ➤ second"
}

case ${1} in
    test)
        first
        second
        ;;
    *)
        usage
        ;;
esac
