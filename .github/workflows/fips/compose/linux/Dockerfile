FROM golang:1.23

WORKDIR /app

# Copy all files
COPY . ./

ENV GO111MODULE=off

# Build the server
ARG BUILD_TARGET
RUN go build -o $BUILD_TARGET http-server.go

# Expose port 443
EXPOSE 443
