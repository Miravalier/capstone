#!/bin/bash

# Configuration parameters
DOMAIN="isometric.finance"

POSITIONALS=()
while [[ $# -gt 0 ]]; do
    ARG=$1; shift
    case $ARG in
        # Parameter arguments
        -d|--domain)
            DOMAIN="$1"; shift
        ;;
        # Boolean arguments
        -c|--create-database)
            CREATE_DATABASE=ON
        ;;
        -h|--help)
            echo "usage: $0 [-d <domain>] [-c] [-h]"
            echo -e "\t-d, --domain\t\tThe domain to host on. Use localhost for testing."
            echo -e "\t-c, --create-database\tWipe the database if it exists and create a new one if not."
            echo -e "\t-h, --help\t\tDisplay this message and exit."
            exit 0
        ;;
        # Unrecoginzed argument
        -*|--*)
            echo -e "\x1B[31merror\x1B[0m: unrecognized argument '$ARG'" 1>&2
            exit 1
        ;;
        # Positional
        *)
            POSITIONALS+=("$ARG")
        ;;
    esac
done
# Update positionals
set -- "${POSITIONALS[@]}"
# Check for unused arguments
if [[ $# -gt 0 ]]; then
    echo -e "\x1B[31merror\x1B[0m: unused arguments: $@" 1>&2
    exit 1
fi

# Functions
function install() {
    SRC="$1"
    if [[ -n $2 ]]; then
        DST="$2"
    else
        DST="$SRC"
    fi
    mkdir -p $(dirname "appdata/$DST")
    cp "src/$SRC" "appdata/$DST"
}

function install-page() {
    install $1.html
    install $1.css
    install $1.js
}

function install-directory() {
    SRC="$1"
    if [[ -n $2 ]]; then
        DST="$2"
    else
        DST="$SRC"
    fi
    mkdir -p $(dirname "appdata/$DST")
    rm -rf "appdata/$DST"
    cp -r "src/$SRC" "appdata/$DST"
}

function configure() {
    SRC="$1"
    if [[ -n $2 ]]; then
        DST="$2"
    else
        DST="$SRC"
    fi
    mkdir -p $(dirname "appdata/$DST")
    cp "src/$SRC" "appdata/$DST"
    sed -i "s/\\\$\\\$DOMAIN\\\$\\\$/$DOMAIN/g" "appdata/$DST"
}

echo "=== Bringing Containers Down ==="
docker-compose down

if [[ -n $CREATE_DATABASE ]]; then
    echo "=== Creating Database ==="
    sudo -u postgres dropdb isometric 2>/dev/null
    sudo -u postgres createdb -O $(whoami) isometric
fi

echo "=== Updating Configuration ==="
configure nginx/app.conf
install-page www/isometric/isometric
install-page www/isometric/login
install-page www/isometric/home
install-page www/isometric/budget
install-page www/isometric/dashboard
install-directory www/isometric/modules
install-directory www/isometric/resources
install-directory www/isometric/webfonts

echo "=== Bringing Containers Up ==="
docker-compose up --build -d
