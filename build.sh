#!/bin/bash

# Configuration parameters
DOMAIN="isometric.finance"

# Functions
function install() {
    SRC="$1"
    if [[ -n $2 ]]; then
        DST="$2"
    else
        DST="$SRC"
    fi
    mkdir -p $(dirname "data/$DST")
    cp "src/$SRC" "data/$DST"
}

function install-directory() {
    SRC="$1"
    if [[ -n $2 ]]; then
        DST="$2"
    else
        DST="$SRC"
    fi
    mkdir -p $(dirname "data/$DST")
    rm -rf "data/$DST"
    cp -r "src/$SRC" "data/$DST"
}

function configure() {
    SRC="$1"
    if [[ -n $2 ]]; then
        DST="$2"
    else
        DST="$SRC"
    fi
    mkdir -p $(dirname "data/$DST")
    cp "src/$SRC" "data/$DST"
    sed -i "s/\\\$\\\$DOMAIN\\\$\\\$/$DOMAIN/g" "data/$DST"
}

echo "=== Bringing Containers Down ==="
docker-compose down

echo "=== Updating Configuration ==="
# Install configuration files
configure nginx/app.conf
install www/isometric/isometric.html
install www/isometric/isometric.js
install www/isometric/isometric.css
install-directory www/isometric/resources

echo "=== Bringing Containers Up ==="
docker-compose up --build --force-recreate -d
