ARG IMPALA_VERSION=4.0.0
FROM apache/impala:${IMPALA_VERSION}-impala_quickstart_client

COPY --chown=impala ./entrypoint.sh /data-load-entrypoint.sh
RUN chmod +x /data-load-entrypoint.sh

# Add the entrypoint.
ENTRYPOINT ["/data-load-entrypoint.sh"]