package main

import (
	"log"
	"os"

	"server/httpserver"
	"server/sshserver"
)

func main() {
	if len(os.Args) < 2 {
		log.Fatal("Usage: go run main.go <mode>")
	}

	var fips_mode bool
	if os.Args[1] == "fips" {
		fips_mode = true
	} else {
		fips_mode = false
	}

	// Use absolute path for the certificate and key files
	// Use environment variables to set the path
	workdir := os.Getenv("WORKDIR")
	if workdir == "" {
		workdir = "."
	}
	certFile := workdir+"/ca.crt"
	keyFile := workdir+"/ca.key"

	// Start the HTTP and SSH servers concurrently
	go httpserver.StartHTTPServer(fips_mode, certFile, keyFile)
	sshserver.StartSSHServer(fips_mode, keyFile)
}

