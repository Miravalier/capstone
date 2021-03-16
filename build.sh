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
configure www/isometric/index.html

echo "=== Bringing Containers Up ==="
docker-compose up --force-recreate -d
