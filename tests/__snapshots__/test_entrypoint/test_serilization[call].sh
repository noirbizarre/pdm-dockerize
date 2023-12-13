#!/bin/sh

function usage() {
    echo "Available commands"
    echo -e "==================\n"
    echo "test: my.app:main"
}

case ${1} in
    test)
        python -c "from my.app import main; main()"
        ;;
    *)
        usage
        ;;
esac
