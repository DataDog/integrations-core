# coredns/coredns ships as a bare static binary on scratch, with no shell or
# HTTP client, so a compose healthcheck can't exec into it. Repackage the same
# binary (unmodified) onto Alpine purely so `wget` is available to probe the
# health plugin's endpoint.
ARG COREDNS_VERSION=1.8.5
FROM coredns/coredns:${COREDNS_VERSION} AS coredns
FROM alpine:3.20
COPY --from=coredns /coredns /coredns
ENTRYPOINT ["/coredns"]
