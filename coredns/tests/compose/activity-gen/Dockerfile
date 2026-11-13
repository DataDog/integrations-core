# Installs dig at build time so activity-gen starts (and restarts) offline,
# instead of running `apk add` on every container start.
FROM alpine:3.20.10
RUN apk add --no-cache bind-tools
