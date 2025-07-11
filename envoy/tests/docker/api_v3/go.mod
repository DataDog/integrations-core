module envoy-e2e

go 1.24.4

require (
	github.com/envoyproxy/go-control-plane v0.9.9
	github.com/golang/protobuf v1.4.3
	google.golang.org/grpc v1.36.0
)

require (
	github.com/census-instrumentation/opencensus-proto v0.2.1 // indirect
	github.com/cncf/xds/go v0.0.0-20210312221358-fbca930ec8ed // indirect
	github.com/envoyproxy/protoc-gen-validate v0.1.0 // indirect
	golang.org/x/net v0.0.0-20200822124328-c89045814202 // indirect
	golang.org/x/sys v0.0.0-20200323222414-85ca7c5b95cd // indirect
	golang.org/x/text v0.3.0 // indirect
	google.golang.org/genproto v0.0.0-20200526211855-cb27e3aa2013 // indirect
	google.golang.org/protobuf v1.25.0 // indirect
)

replace github.com/envoyproxy/go-control-plane => github.com/envoyproxy/go-control-plane v0.9.9

replace github.com/golang/protobuf => github.com/golang/protobuf v1.4.3

replace google.golang.org/grpc => google.golang.org/grpc v1.36.0
