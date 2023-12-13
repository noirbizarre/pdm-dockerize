#!/bin/sh

function usage() {
    echo "Available commands"
    echo -e "==================\n"
    echo "test: pytest --with --params"
}

case ${1} in
    test)
        pytest --with --params
        ;;
    *)
        usage
        ;;
esac
