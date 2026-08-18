# Build the info-proxy binary, then ship it on a redis image so the compose
# healthcheck can use redis-cli against the proxy port.
FROM golang:1.23-alpine AS build
WORKDIR /src
# Stdlib-only module: copying sources is enough, no module download step.
COPY . .
RUN CGO_ENABLED=0 go build -o /usr/local/bin/info-proxy .

FROM redis:7-alpine
COPY --from=build /usr/local/bin/info-proxy /usr/local/bin/info-proxy
EXPOSE 6379
ENTRYPOINT ["/usr/local/bin/info-proxy"]
