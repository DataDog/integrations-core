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

	"google.golang.org/grpc"
	"google.golang.org/grpc/channelz/service"
	"google.golang.org/grpc/credentials/insecure"
)

var (
	listenAddress     string
	httpListenAddress string
)

func setCliFlags() {
	flag.StringVar(&listenAddress, "address", ":8080", "Address for listener")
	flag.StringVar(&httpListenAddress, "http-listend-address", ":8081", "Http listener address")
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

func startTestClients(ctx context.Context, targetAddress string) error {
	for i := 0; i < 2; i++ {
		log.Printf("Starting test client %d", i)
		testConn, err := grpc.Dial(targetAddress,
			grpc.WithDefaultServiceConfig(`{"loadBalancingConfig": [{"round_robin":{}}]}`),
			grpc.WithTransportCredentials(insecure.NewCredentials()),
		)
		if err != nil {
			log.Fatalf("Error opening test clients: %s", err)
			return err
		}
		defer testConn.Close()
	}
	select {
	case <-ctx.Done():
		log.Print("Context done, existing")
		return nil
	}
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
