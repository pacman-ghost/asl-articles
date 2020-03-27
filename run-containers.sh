#!/usr/bin/env bash
# Helper script that builds and launches the Docker containers.

# ---------------------------------------------------------------------

function print_help {
    echo "`basename "$0"` {options}"
    echo "  Build and launch the \"asl-articles\" containers."
    echo
    echo "    -t  --tag             Docker container tag e.g. \"testing\" or \"latest\"."
    echo "    -d  --dbconn          Database connection string e.g."
    echo "                            ~/asl-articles.db (path to a SQLite database)"
    echo "                            postgresql://USER:PASS@host/dbname (database connection string)"
    echo "                          Note that the database server address is relative to the container i.e. NOT \"localhost\"."
    echo "        --web-portno      Webapp port number."
    echo "        --flask-portno    Flask backend server port number."
    echo "    -e  --extdocs         Base directory for external documents (to allow articles to link to them)."
    echo "    -u  --user-files      Base directory for user files."
    echo "    -r  --aslrb           Base URL for an eASLRB."
    echo "    -a  --author-aliases  Author aliases config file (see config/author-aliases.cfg.example)."
    echo "        --no-build        Launch the containers as they are (i.e. without rebuilding them first)."
}

# ---------------------------------------------------------------------

# initialize
cd `dirname "$0"`
export TAG=
export DBCONN=
export SQLITE=
export WEB_PORTNO=3002
export FLASK_PORTNO=5002
export EXTERNAL_DOCS_BASEDIR=
export USER_FILES_BASEDIR=
export ASLRB_BASE_URL=
export AUTHOR_ALIASES=
export ENABLE_TESTS=
NO_BUILD=

# parse the command-line arguments
if [ $# -eq 0 ]; then
    print_help
    exit 0
fi
params="$(getopt -o t:d:e:u:r:a:h -l tag:,dbconn:,web-portno:,flask-portno:,extdocs:,user-files:,aslrb:,author-aliases:,no-build,help --name "$0" -- "$@")"
if [ $? -ne 0 ]; then exit 1; fi
eval set -- "$params"
while true; do
    case "$1" in
        -t | --tag )
            TAG=$2
            shift 2 ;;
        -d | --dbconn )
            DBCONN=$2
            shift 2 ;;
        --web-portno )
            WEB_PORTNO=$2
            shift 2 ;;
        --flask-portno )
            FLASK_PORTNO=$2
            shift 2 ;;
        -e | --extdocs )
            EXTERNAL_DOCS_BASEDIR=$2
            shift 2 ;;
        -u | --user-files )
            USER_FILES_BASEDIR=$2
            shift 2 ;;
        -r | --aslrb )
            ASLRB_BASE_URL=$2
            shift 2 ;;
        -a | --author-aliases )
            AUTHOR_ALIASES=$2
            shift 2 ;;
        --no-build )
            NO_BUILD=1
            shift 1 ;;
        -h | --help )
            print_help
            exit 0 ;;
        -- ) shift ; break ;;
        * )
            echo "Unknown option: $1" >&2
            exit 1 ;;
    esac
done

# prepare the database connection string
if [ -z "$DBCONN" ]; then
    echo "No database was specified."
    exit 3
fi
if [ -f "$DBCONN" ]; then
    # connect to a SQLite database
    SQLITE=$DBCONN
    DBCONN=sqlite:////data/sqlite.db
else
    # FUDGE! We pass the database connection string (DBCONN) through to the container,
    # but this needs to be set, even if it's not being used :-/
    SQLITE=/dev/null
fi

# initialize for testing
if [ "$TAG" == "testing" ]; then
    echo -e "*** WARNING! Test mode is enabled! ***\n"
    ENABLE_TESTS=1
else
    if [ -z "$TAG" ]; then
        TAG=latest
    fi
fi

# check the external documents directory
if [ -n "$EXTERNAL_DOCS_BASEDIR" ]; then
    if [ ! -d "$EXTERNAL_DOCS_BASEDIR" ]; then
        echo "Can't find the external documents base directory: $EXTERNAL_DOCS_BASEDIR"
        exit 1
    fi
else
    # FUDGE! This needs to be set, even if it's not being used :-/
    EXTERNAL_DOCS_BASEDIR=/dev/null
fi

# check the user files directory
if [ -n "$USER_FILES_BASEDIR" ]; then
    if [ ! -d "$USER_FILES_BASEDIR" ]; then
        echo "Can't find the user files base directory: $USER_FILES_BASEDIR"
        exit 1
    fi
else
    # FUDGE! This needs to be set, even if it's not being used :-/
    USER_FILES_BASEDIR=/dev/null
fi

# check the author aliases
if [ -n "$AUTHOR_ALIASES" ]; then
    if [ ! -f "$AUTHOR_ALIASES" ]; then
        echo "Can't find the author aliases config file: $AUTHOR_ALIASES"
        exit 1
    fi
else
    # FUDGE! This needs to be set, even if it's not being used :-/
    AUTHOR_ALIASES=/dev/null
fi

# build the containers
if [ -z "$NO_BUILD" ]; then
    echo Building the \"$TAG\" containers...
    docker-compose build --build-arg ENABLE_TESTS=$ENABLE_TESTS 2>&1 \
        | sed -e 's/^/  /'
    if [ ${PIPESTATUS[0]} -ne 0 ]; then exit 10 ; fi
    echo
fi

# launch the containers
echo Launching the \"$TAG\" containers...
if [ -n "$ENABLE_TESTS" ]; then
    echo "  *** TEST MODE ***"
fi
docker-compose up --detach 2>&1 \
    | sed -e 's/^/  /'
exit ${PIPESTATUS[0]}
