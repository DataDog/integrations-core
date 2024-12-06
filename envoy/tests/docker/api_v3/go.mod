module envoy-e2e

go 1.16

require (
	github.com/envoyproxy/go-control-plane v0.9.9
	github.com/golang/protobuf v1.4.3
	google.golang.org/grpc v1.36.0
)

replace github.com/envoyproxy/go-control-plane => github.com/envoyproxy/go-control-plane v0.9.9

replace github.com/golang/protobuf => github.com/golang/protobuf v1.4.3

replace google.golang.org/grpc => google.golang.org/grpc v1.36.0
