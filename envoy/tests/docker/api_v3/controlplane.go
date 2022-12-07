package main

import (
	"context"
	"flag"
	"net"
	"time"

	clusterconfig "github.com/envoyproxy/go-control-plane/envoy/config/cluster/v3"
	core "github.com/envoyproxy/go-control-plane/envoy/config/core/v3"
	endpointconfig "github.com/envoyproxy/go-control-plane/envoy/config/endpoint/v3"
	clusterservice "github.com/envoyproxy/go-control-plane/envoy/service/cluster/v3"
	discoveryservice "github.com/envoyproxy/go-control-plane/envoy/service/discovery/v3"
	endpointservice "github.com/envoyproxy/go-control-plane/envoy/service/endpoint/v3"
	listenerservice "github.com/envoyproxy/go-control-plane/envoy/service/listener/v3"
	routeservice "github.com/envoyproxy/go-control-plane/envoy/service/route/v3"
	"github.com/envoyproxy/go-control-plane/pkg/cache/types"
	"github.com/envoyproxy/go-control-plane/pkg/cache/v3"
	xds "github.com/envoyproxy/go-control-plane/pkg/server/v3"
	"github.com/golang/protobuf/ptypes"
	"google.golang.org/grpc"
)

func main() {
	flag.Parse()

	snapshotCache := cache.NewSnapshotCache(false, cache.IDHash{}, nil)
	server := xds.NewServer(context.Background(), snapshotCache, nil)
	grpcServer := grpc.NewServer()
	lis, _ := net.Listen("tcp", ":8080")

	discoveryservice.RegisterAggregatedDiscoveryServiceServer(grpcServer, server)
	endpointservice.RegisterEndpointDiscoveryServiceServer(grpcServer, server)
	clusterservice.RegisterClusterDiscoveryServiceServer(grpcServer, server)
	routeservice.RegisterRouteDiscoveryServiceServer(grpcServer, server)
	listenerservice.RegisterListenerDiscoveryServiceServer(grpcServer, server)

	go grpcServer.Serve(lis)

	dummyHost := &core.Address{
		Address: &core.Address_SocketAddress{
			SocketAddress: &core.SocketAddress{
				Address:  "localhost",
				Protocol: core.SocketAddress_TCP,
				PortSpecifier: &core.SocketAddress_PortValue{
					PortValue: uint32(8000),
				},
			},
		},
	}
	dummyLbEndpoint := endpointconfig.LbEndpoint{
		HostIdentifier: &endpointconfig.LbEndpoint_Endpoint{
			Endpoint: &endpointconfig.Endpoint{
				Address: dummyHost,
			},
		},
	}
	dummyLocalityLbEndpoint := endpointconfig.LocalityLbEndpoints{
		LbEndpoints: []*endpointconfig.LbEndpoint{&dummyLbEndpoint},
	}

	clusterResource := []types.Resource{
		&clusterconfig.Cluster{
			Name:                 "dummy_dynamic_cluster",
			ConnectTimeout:       ptypes.DurationProto(time.Second),
			ClusterDiscoveryType: &clusterconfig.Cluster_Type{Type: clusterconfig.Cluster_LOGICAL_DNS},
			LoadAssignment: &endpointconfig.ClusterLoadAssignment{
				ClusterName: "dummy_dynamic_cluster",
				Endpoints:   []*endpointconfig.LocalityLbEndpoints{&dummyLocalityLbEndpoint},
			},
			OutlierDetection: &clusterconfig.OutlierDetection{},
		},
	}

	for {
		for _, nodeId := range snapshotCache.GetStatusKeys() {
			// snapshot := cache.NewSnapshot("1", nil, clusterResource, nil, nil, nil)
			snapshot := cache.NewSnapshot("1", []types.Resource{}, clusterResource, nil, nil, []types.Resource{}, []types.Resource{})
			snapshotCache.SetSnapshot(nodeId, snapshot)
		}

		time.Sleep(time.Second)
	}
}
