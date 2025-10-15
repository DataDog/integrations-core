FROM alpine:3.19.1

RUN apk add --no-cache tinyproxy curl
HEALTHCHECK --timeout=10s --interval=5s --retries=4 CMD curl -H 'Host: tinyproxy.stats' http://localhost:8008
EXPOSE 8008

COPY --chmod=555 src/ /

USER tinyproxy

ENTRYPOINT ["/usr/bin/tinyproxy"]
CMD ["-d"]
