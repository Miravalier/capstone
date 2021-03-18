sudo -u postgres dropdb isometric 2>/dev/null
sudo -u postgres createdb -O $(whoami) isometric
