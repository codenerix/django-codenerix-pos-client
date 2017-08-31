#!/bin/bash


shutdown() {
    # Get our process group id
    PGID=$(ps -o pgid= $$ | grep -o [0-9]*)

    # Kill it in a new new process group
    setsid kill -- -$PGID
    exit 0
}

trap "shutdown" SIGINT SIGTERM

# Get local dir and make sure we are in it
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
    DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
cd $DIR

./posclient.py
