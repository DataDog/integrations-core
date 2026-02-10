# Use Go 1.21+ for multi-arch (arm64/amd64). Go 1.6 panics under QEMU emulation (lfstackpush).
FROM golang:1.21-alpine
RUN mkdir /test_go
ADD test_expvar.go /test_go
EXPOSE 8079
ENTRYPOINT ["go", "run", "/test_go/test_expvar.go"]
