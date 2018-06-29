FROM alpine:3.7

# Define the variables available.
ARG memcache_uid
ARG memcache_gid

# add our user and group first to make sure their IDs get assigned consistently, regardless of whatever dependencies get added
RUN adduser -D memcache -u ${memcache_uid} -g ${memcache_gid}

# Copy the script.
COPY setup.sh /

ENV MEMCACHED_VERSION 1.5.7
ENV MEMCACHED_SHA1 31d6f6b80668025e4616aa2ad5c7a45f24ed9665

ENV SASL_CONF_PATH /etc/sasl2/memecached.conf
ENV MEMCACHED_SASL_PWDB /etc/sasl2/memcached-sasl-db

ADD docker-entrypoint.sh /usr/local/bin/

# Launch setup.sh
RUN /bin/sh /setup.sh "${memcache_uid}" "${memcache_gid}"

ENTRYPOINT ["docker-entrypoint.sh"]

USER memcache
EXPOSE 11211
CMD ["memcached"]
