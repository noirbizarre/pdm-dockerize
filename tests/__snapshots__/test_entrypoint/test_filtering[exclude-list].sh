#!/bin/sh

export PYTHONPATH=./lib
export PATH=./bin:$PATH

usage() {
    echo "Available commands"
    echo "=================="
    echo "test:something: pytest something"
    echo "ns:task2: ns:task2"
    echo "ns:task3: ns:task3"
}

case ${1} in
    test:something)
        pytest something
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
