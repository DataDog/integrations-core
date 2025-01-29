FROM golang:1.23

# Copy all files
COPY . ./

RUN go build -o server http-server.go

# Expose port 443
EXPOSE 443
