#!/bin/sh

function usage() {
    echo "Available commands"
    echo -e "==================\n"
    echo "ns:task2: ns:task2"
    echo "ns:task3: ns:task3"
}

case ${1} in
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
