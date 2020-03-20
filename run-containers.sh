#!/usr/bin/env bash
# Helper script that builds and launches the Docker containers.

# parse the command-line arguments
if [ -z "$1" ]; then
    echo "Usage: `basename "$0"` <db-conn> <external-docs> <aslrb-url>"
    echo "  Build and launch the \"asl-articles\" containers, using the specified database e.g."
    echo "    ~/asl-articles.db (path to a SQLite database)"
    echo "    postgresql://USER:PASS@host/dbname (database connection string)"
    echo "  Note that the database server address is relative to the container i.e. NOT \"localhost\"."
    echo
    echo "  If you want link articles to their original documents, specify a base directory for the documents."
    echo
    echo "  If you want to have links to an eASLRB, specify its base URL."
    echo
    echo "  The TAG env variable can also be set to specify which containers to run e.g."
    echo "    TAG=testing ./run.sh /tmp/asl-articles.db"
    exit 0
fi
if [ -f "$1" ]; then
    # connect to a SQLite database
    export SQLITE=$1
    export DBCONN=sqlite:////data/sqlite.db
else
    # pass the database connection string through to the container
    export SQLITE=/dev/null
    export DBCONN=$1
fi
if [ ! -z "$2" ]; then
    # set the base directory for external documents
    export EXTERNAL_DOCS_BASEDIR=$2
    if [ ! -d "$EXTERNAL_DOCS_BASEDIR" ]; then
        echo "Invalid document base directory: $EXTERNAL_DOCS_BASEDIR"
        exit 1
    fi
else
    # FUDGE! This needs to be set, even if it's not being used :-/
    export EXTERNAL_DOCS_BASEDIR=/dev/null
fi
if [ ! -z "$3" ]; then
    export ASLRB_BASE_URL=$3
fi

# initialize
if [ "$TAG" == "testing" ]; then
    echo "*** WARNING! Special test functionality is enabled."
    export ENABLE_TESTS=1
elif [ "$TAG" == "prod" ]; then
    export ENABLE_TESTS=
else
    export ENABLE_TESTS=
    export TAG=latest
fi

# build the containers
echo Building the \"$TAG\" containers...
docker-compose build --build-arg ENABLE_TESTS=$ENABLE_TESTS 2>&1 \
    | sed -e 's/^/  /'
if [ $? -ne 0 ]; then exit 10 ; fi
echo

# launch the containers
echo Launching the \"$TAG\" containers...
docker-compose up --detach 2>&1 \
    | sed -e 's/^/  /'
