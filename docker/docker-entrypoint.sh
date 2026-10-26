#!/bin/sh
set -eu

if [ "$#" -eq 0 ] || [ "${1#-}" != "$1" ]; then
    set -- apache2-foreground "$@"
fi

if [ "$1" = apache2-foreground ]; then
    shift
    # Debian Apache needs the runtime paths/user from its environment file.
    export APACHE_CONFDIR="${APACHE_CONFDIR:-/etc/apache2}"
    . "$APACHE_CONFDIR/envvars"
    mkdir -p "$APACHE_RUN_DIR" "$APACHE_LOCK_DIR"
    rm -f "$APACHE_PID_FILE"
    exec apache2 -D FOREGROUND "$@"
fi

exec "$@"
