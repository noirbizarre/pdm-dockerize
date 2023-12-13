#!/bin/sh

function usage() {
    echo "Available commands"
    echo -e "==================\n"
    echo "test: pytest"
    echo "test:something: pytest something"
    echo "ns:task1: ns:task1"
    echo "ns:task2: ns:task2"
    echo "ns:task3: ns:task3"
}

case ${1} in
    test)
        pytest
        ;;
    test:something)
        pytest something
        ;;
    ns:task1)
        ns:task1
        ;;
    ns:task2)
        ns:task2
        ;;
    ns:task3)
        ns:task3
        ;;
    *)
        usage
        ;;
esac
