# Build the grpc-test-server binary
FROM golang:latest as builder

WORKDIR /workspace
# Copy the Go Modules manifests
COPY go.mod go.mod
COPY go.sum go.sum
# cache deps before building and copying source so that we don't need to re-download as much
# and so that source changes don't invalidate our downloaded layer
RUN go mod download

# Copy the go source
COPY grpc_test_server.go grpc_test_server.go

# Build
RUN CGO_ENABLED=0 \
    GOOS=linux \
    GOARCH=amd64 \
    GO111MODULE=on \
    go build -a -o grpc-test-server grpc_test_server.go

# Copy the kubectl_fzf_server into a thin image
FROM alpine:latest
WORKDIR /
COPY --from=builder /workspace/grpc-test-server .

ENTRYPOINT ["/grpc-test-server"]
