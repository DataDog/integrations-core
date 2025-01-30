package main

import (
	"crypto/tls"
	"fmt"
	"log"
	"net/http"
	"os"
)

func main() {
	// Get the allowed cipher from command-line argument
	if len(os.Args) < 2 {
		log.Fatal("Usage: server <TLS_CIPHER>")
	}
	tlsCipher := os.Args[1]

	// Define allowed ciphers for TLS 1.2
	cipherMap := map[string]uint16{
		"ECDHE-RSA-CHACHA20-POLY1305": tls.TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305,
		"ECDHE-RSA-AES128-SHA256": tls.TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256,
	}

	cipher, exists := cipherMap[tlsCipher]
	if !exists {
		log.Fatalf("Unsupported cipher: %s", tlsCipher)
	}

	// TLS Configuration
	tlsConfig := &tls.Config{
		MinVersion:               tls.VersionTLS12,
		MaxVersion:               tls.VersionTLS12, // Force TLS 1.2 only
		CipherSuites:             []uint16{cipher}, // Restrict to a single cipher
		PreferServerCipherSuites: true,

	}

	// Define a simple HTTP handler
	handler := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("<html><body><h1>Secure Server</h1></body></html>"))
	})

	// Create HTTPS server
	server := &http.Server{
		Addr:      ":443",
		Handler:   handler,
		TLSConfig: tlsConfig,
		TLSNextProto: make(map[string]func(*http.Server, *tls.Conn, http.Handler)),
	}

	fmt.Printf("Serving on https://localhost:8443 using cipher %s with TLSv1.2 enforced\n", tlsCipher)
	log.Fatal(server.ListenAndServeTLS("./ca.crt", "./ca.key"))
}
