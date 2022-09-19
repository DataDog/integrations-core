package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"math/rand"

	"google.golang.org/grpc"
	channelzgrpc "google.golang.org/grpc/channelz/grpc_channelz_v1"
	"google.golang.org/grpc/channelz/service"
	"google.golang.org/grpc/credentials/insecure"
	pb "google.golang.org/grpc/examples/helloworld/helloworld"
	"google.golang.org/grpc/reflection"
)

var (
	listenAddress           string
	httpListenAddress       string
	queryRate               int
	numberOkClients         int
	numberBadAddressClients int
	queryRandomTime         time.Duration
)

func setCliFlags() {
	flag.StringVar(&listenAddress, "address", ":8080", "Address for listener")
	flag.StringVar(&httpListenAddress, "http-listend-address", ":8081", "Http listener address")
	flag.IntVar(&numberOkClients, "ok-clients", 2, "Number of clients connecting with ok clients")
	flag.IntVar(&numberBadAddressClients, "bad-address-clients", 4, "Number of clients connecting with bad address")
	flag.IntVar(&queryRate, "query-rate", 0, "Query rate for test clients")
	flag.DurationVar(&queryRandomTime, "query-random-time", time.Second, "Random time added to query")
}

func handleSignals(cancel context.CancelFunc) {
	sigIn := make(chan os.Signal, 100)
	signal.Notify(sigIn)
	for sig := range sigIn {
		switch sig {
		case syscall.SIGINT, syscall.SIGTERM:
			log.Fatalf("Caught signal %s, terminating.", sig.String())
			cancel()
		}
	}
}

func waitForServer(ctx context.Context, targetAddress string) (err error) {
	for i := 0; i < 10; i++ {
		conn, err := net.DialTimeout("tcp", targetAddress, time.Second)
		if err == nil {
			conn.Close()
			return nil
		}
	}
	return err
}

func queryClient(ctx context.Context, dialTarget string, ignoreErr bool, queryRate int, queryRandomTime time.Duration) {
	log.Printf("Starting test client on %s", dialTarget)
	conn, err := grpc.Dial(dialTarget,
		grpc.WithDefaultServiceConfig(`{"loadBalancingConfig": [{"round_robin":{}}]}`),
		grpc.WithTransportCredentials(insecure.NewCredentials()),
	)
	if err != nil && !ignoreErr {
		log.Fatalf("Error opening test clients: %s", err)
	}
	defer conn.Close()

	if queryRate == 0 {
		<-ctx.Done()
		log.Print("Context done, existing")
		return
	}

	for {
		select {
		case <-ctx.Done():
			log.Print("Context done, existing")
			return
		default:
			randomDuration := time.Second * 0
			if queryRandomTime > 0 {
				randomDuration = time.Duration(rand.Int63n(queryRandomTime.Nanoseconds()))
			}
			time.Sleep(time.Second + randomDuration)
			channelzClient := channelzgrpc.NewChannelzClient(conn)
			req := &channelzgrpc.GetServersRequest{StartServerId: 0}
			channelzClient.GetServers(ctx, req)
		}
	}
}

func startTestClients(ctx context.Context, targetAddress string) error {
	for i := 0; i < numberOkClients; i++ {
		go queryClient(ctx, targetAddress, false, queryRate, queryRandomTime)
	}

	for i := 0; i < numberBadAddressClients; i++ {
		go queryClient(ctx, "wrong_address:8083", true, queryRate, queryRandomTime)
	}

	for {
		select {
		case <-ctx.Done():
			log.Print("Context done, existing")
			return nil
		}
	}
}

type server struct {
	pb.UnimplementedGreeterServer
}

func (s *server) SayHello(ctx context.Context, in *pb.HelloRequest) (*pb.HelloReply, error) {
	return &pb.HelloReply{Message: "Hello " + in.Name}, nil
}

func startTestServer(ctx context.Context, listenAddress string) error {
	listener, err := net.Listen("tcp", listenAddress)
	if err != nil {
		log.Fatalf("Failed to listen %s: %s", listenAddress, err)
		return err
	}
	defer listener.Close()
	s := grpc.NewServer()
	service.RegisterChannelzServiceToServer(s)
	reflection.Register(s)
	pb.RegisterGreeterServer(s, &server{})

	log.Println("Starting test gRPC server")
	go func() {
		err = s.Serve(listener)
		if err != nil {
			log.Fatalf("Server error, %s", err)
		}
	}()
	defer s.Stop()

	select {
	case <-ctx.Done():
		log.Print("Context done, existing")
	}
	return nil
}

func readyHandler(w http.ResponseWriter, r *http.Request) {
	log.Print("Received ready request")
	fmt.Fprintf(w, "Ready")
}

func start() {
	ctx, cancel := context.WithCancel(context.Background())
	go handleSignals(cancel)
	go startTestServer(ctx, listenAddress)

	err := waitForServer(ctx, listenAddress)
	if err != nil {
		log.Fatalf("Couldn't connect to server: %s", err)
	}
	go startTestClients(ctx, listenAddress)

	http.HandleFunc("/ready", readyHandler)
	fmt.Printf("Starting http server at port %s\n", httpListenAddress)
	if err := http.ListenAndServe(httpListenAddress, nil); err != nil {
		log.Fatal(err)
	}
}

func main() {
	setCliFlags()
	flag.Parse()
	start()
}
