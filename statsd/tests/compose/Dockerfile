ARG STATSD_VERSION
FROM statsd/statsd:${STATSD_VERSION}

# Start statsd redirecting output to a file
ENTRYPOINT ["/bin/sh", "-c", "node stats.js config.js 2>&1 | tee statsd.log"]