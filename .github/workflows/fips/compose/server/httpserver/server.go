package httpserver

import (
	"crypto/tls"
	"log"
	"net/http"
)

const port = ":443"

func StartHTTPServer(fips_mode bool, certFile, keyFile string) {
	var cipher uint16
	if fips_mode {
		cipher = tls.TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256
		log.Printf("FIPS mode enabled. Using cipher %s\n", cipher)
	} else {
		cipher = tls.TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305
		log.Printf("FIPS mode disabled. Using cipher %s\n", cipher)
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
		Addr:      port,
		Handler:   handler,
		TLSConfig: tlsConfig,
		TLSNextProto: make(map[string]func(*http.Server, *tls.Conn, http.Handler)),
	}

	log.Fatal(server.ListenAndServeTLS(certFile, keyFile))
}
