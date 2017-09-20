#!/bin/bash

shutdown() {
    echo "Shutdown by external call!" 
    kill -TERM "$child" 2>/dev/null
}
trap shutdown SIGINT SIGTERM

# Get local dir and make sure we are in it
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
    DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
    SOURCE="$(readlink "$SOURCE")"
    [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done
DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
cd $DIR

# Start POSClient
./posclient.py &
child=$!

wait "$child"
