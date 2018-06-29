#!/bin/sh

set -x
# Quit on error.
#set -e
# Treat undefined variables as errors.
#set -u
try to add permission to docker compose as well....
function main {
    local memcache_uid="${1:-}"
    local memcache_gid="${2:-}"

    apk add --no-cache --virtual shadow

    # Change the uid
    if [[ -n "${memcache_uid:-}" ]]; then
        usermod -u "${memcache_uid}" memcache
    fi
    # Change the gid
    groupmod -g 3456 dialout
    if [[ -n "${memcache_gid:-}" ]]; then
        groupmod -g "${memcache_gid}" memcache
    fi


    # Setup permissions on the tmp directory where the sockets will be
    # created, so we are sure the app will have the rights to create them.

    # Make sure the folder exists.
    mkdir /tmp
    # Set owner.
    chown root:memcache /tmp
    # Set permissions.
    chmod u=rwX,g=rwX,o=--- /tmp

    # Install packages
    apk add --no-cache --virtual .build-deps \
		ca-certificates \
		coreutils \
		cyrus-sasl-dev \
		dpkg-dev dpkg \
		gcc \
		libc-dev \
		libevent-dev \
		libressl \
		linux-headers \
		make \
		perl \
		perl-utils \
		tar \
	\
	&& wget -O memcached.tar.gz "https://memcached.org/files/memcached-$MEMCACHED_VERSION.tar.gz" \
	&& echo "$MEMCACHED_SHA1  memcached.tar.gz" | sha1sum -c - \
	&& mkdir -p /usr/src/memcached \
	&& tar -xzf memcached.tar.gz -C /usr/src/memcached --strip-components=1 \
	&& rm memcached.tar.gz \
	\
	&& cd /usr/src/memcached \
	\
	&& ./configure \
		--build="$(dpkg-architecture --query DEB_BUILD_GNU_TYPE)" \
		--enable-sasl \
		--enable-sasl-pwdb \
	&& make -j "$(nproc)" \
	\
	&& make test \
	&& make install \
	\
	&& cd / && rm -rf /usr/src/memcached \
	\
	&& runDeps="$( \
		scanelf --needed --nobanner --format '%n#p' --recursive /usr/local \
			| tr ',' '\n' \
			| sort -u \
			| awk 'system("[ -e /usr/local/lib/" $1 " ]") == 0 { next } { print "so:" $1 }' \
	)" \
	&& apk add --virtual .memcached-rundeps $runDeps \
	&& apk del .build-deps \
	\
	&& memcached -V

    # cp docker-entrypoint.sh /usr/local/bin/

    mkdir -p /etc/sasl2 \
    && chown memcache /etc/sasl2 \
	&& echo "mech_list: plain" > $SASL_CONF_PATH \
	&& chmod 777 /usr/local/bin/docker-entrypoint.sh \
	&& ln -s usr/local/bin/docker-entrypoint.sh /entrypoint.sh # backwards compat

	# --------

	apk add --update \
        python \
        python-dev \
        py-pip \
        build-base

    apk add --update netcat-openbsd && rm -rf /var/cache/apk/*

    pip install python-memcached
}

main "$@"