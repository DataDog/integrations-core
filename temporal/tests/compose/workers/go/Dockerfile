FROM golang:1.19.5

WORKDIR /app

COPY . ./
RUN go mod download

ENTRYPOINT ["go", "run", "/app/worker/main.go"]
