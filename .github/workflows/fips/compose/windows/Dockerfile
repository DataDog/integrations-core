FROM golang:1.23

WORKDIR /app

# Copy all files
COPY . ./

ENV GO111MODULE=off

# Build the server
RUN go build -o http-server.exe http-server.go

# Expose port 443
EXPOSE 443
