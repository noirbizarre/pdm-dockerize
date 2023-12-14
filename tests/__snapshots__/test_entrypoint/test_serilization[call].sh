#!/bin/sh

export PYTHONPATH=./lib
export PATH=./bin:$PATH

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
