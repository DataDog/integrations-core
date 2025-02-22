package sshserver

import (
	"fmt"
	"log"
	"os"

	gliderssh "github.com/gliderlabs/ssh"
	"golang.org/x/crypto/ssh"
)

const sshPort = ":22"

func StartSSHServer(fips_mode bool, keyPath string) {
	log.Print("SSH server starting")
	var allowed_ciphers []string
	var allowed_keyExchanges []string
	// Ciphers and keys gotten from https://cs.opensource.google/go/x/crypto/+/refs/tags/v0.27.0:ssh/common.go;l=27
	if fips_mode {
		allowed_ciphers = []string{"aes128-cbc"}
		allowed_keyExchanges = []string{"ecdh-sha2-nistp256"}
	} else {
		allowed_ciphers = []string{"chacha20-poly1305@openssh.com"}
		allowed_keyExchanges = []string{"ecdh-sha2-nistp256"}
	}

	privateKey, err := loadPrivateKey(keyPath)
	if err != nil {
		log.Fatalf("Failed to load private key: %v", err)
	}
	sshConfig := &ssh.ServerConfig{
		Config: ssh.Config{
			Ciphers:      allowed_ciphers, // Set allowed ciphers
			KeyExchanges: allowed_keyExchanges,
		},
	}
	server := &gliderssh.Server{
			Addr: sshPort,
			PublicKeyHandler: func(ctx gliderssh.Context, key gliderssh.PublicKey) bool {
				log.Print("New connection attempt...")
				return true
			},
			PasswordHandler: func(ctx gliderssh.Context, password string) bool {
				log.Print("New connection attempt...")
				return true
			},
			HostSigners: []gliderssh.Signer{privateKey},
			ServerConfigCallback: func(ctx gliderssh.Context) *ssh.ServerConfig {
				return sshConfig
			},
		}
	// Start the SSH server
	log.Fatal(server.ListenAndServe())
}

// Load private key
func loadPrivateKey(path string) (ssh.Signer, error) {
	keyData, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("failed to read private key: %v", err)
	}

	signer, err := ssh.ParsePrivateKey(keyData)
	if err != nil {
		return nil, fmt.Errorf("failed to parse private key: %v", err)
	}
	return signer, nil
}
