#!/bin/sh
set -e

echo "$USERNAME@`hostname`:$PASSWORD" > $MEMCACHED_SASL_PWDB

# first arg is `-f` or `--some-option`
if [ "${1#-}" != "$1" ]; then
	set -- memcached "$@"
fi

exec "$@"
