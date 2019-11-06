package main

import (
	"context"
	"google.golang.org/grpc"
	"net"
	"time"

	api "github.com/envoyproxy/go-control-plane/envoy/api/v2"
	core "github.com/envoyproxy/go-control-plane/envoy/api/v2/core"
	endpoint "github.com/envoyproxy/go-control-plane/envoy/api/v2/endpoint"
	discovery "github.com/envoyproxy/go-control-plane/envoy/service/discovery/v2"
	"github.com/envoyproxy/go-control-plane/pkg/cache"
	xds "github.com/envoyproxy/go-control-plane/pkg/server"

	"github.com/golang/protobuf/ptypes"
)

func main() {
	snapshotCache := cache.NewSnapshotCache(false, cache.IDHash{}, nil)
	server := xds.NewServer(context.Background(), snapshotCache, nil)
	grpcServer := grpc.NewServer()
	lis, _ := net.Listen("tcp", ":8080")

	discovery.RegisterAggregatedDiscoveryServiceServer(grpcServer, server)
	api.RegisterEndpointDiscoveryServiceServer(grpcServer, server)
	api.RegisterClusterDiscoveryServiceServer(grpcServer, server)
	api.RegisterRouteDiscoveryServiceServer(grpcServer, server)
	api.RegisterListenerDiscoveryServiceServer(grpcServer, server)

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
	dummyLbEndpoint := endpoint.LbEndpoint{
		HostIdentifier: &endpoint.LbEndpoint_Endpoint{
			Endpoint: &endpoint.Endpoint{
				Address: dummyHost,
			},
		},
	}
	dummyLocalityLbEndpoint := endpoint.LocalityLbEndpoints{
		LbEndpoints: []*endpoint.LbEndpoint{&dummyLbEndpoint},
	}

	clusterResource := []cache.Resource{
		&api.Cluster{
			Name:                 "dummy_dynamic_cluster",
			ConnectTimeout:       ptypes.DurationProto(time.Second),
			ClusterDiscoveryType: &api.Cluster_Type{Type: api.Cluster_LOGICAL_DNS},
			LoadAssignment: &api.ClusterLoadAssignment{
				ClusterName: "dummy_dynamic_cluster",
				Endpoints:   []*endpoint.LocalityLbEndpoints{&dummyLocalityLbEndpoint},
			},
		},
	}

	for {
		for _, nodeId := range snapshotCache.GetStatusKeys() {
			// snapshot := cache.NewSnapshot("1", nil, clusterResource, nil, listenerResource, nil)
			snapshot := cache.NewSnapshot("1", nil, clusterResource, nil, nil, nil)
			snapshotCache.SetSnapshot(nodeId, snapshot)
		}

		time.Sleep(time.Second)
	}
}
