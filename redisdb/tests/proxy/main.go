// info-proxy is a transparent Redis (RESP) proxy that forwards every command
// to a backend Redis untouched, except that it augments the reply to `INFO all`
// with additional key:value lines and, optionally, serves a canned `CLUSTER
// INFO` reply. It exists so a test environment can exercise metrics that a
// plain Redis instance cannot emit on its own (managed-service-only fields,
// cluster/sentinel fields, module fields), for any scraper that reads INFO.
//
// Both the Datadog redisdb check and the OpenTelemetry redisreceiver collect
// almost all of their metrics by parsing the INFO reply as flat key:value
// pairs, so a single injection point fakes fields for both.
package main

import (
	"bufio"
	"bytes"
	"log"
	"net"
	"os"
	"strings"
)

type config struct {
	listenAddr      string
	backendAddr     string
	inject          [][]byte
	clusterInfoText string
}

func getenv(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}

func main() {
	cfg := config{
		listenAddr:  getenv("LISTEN_ADDR", ":6379"),
		backendAddr: getenv("BACKEND_ADDR", "redis-master:6379"),
	}

	injectFile := getenv("INJECT_FILE", "/etc/info-proxy/inject.conf")
	if lines, err := loadInjectLines(injectFile); err != nil {
		log.Printf("info-proxy: no inject file at %s (%v); passing INFO through unchanged", injectFile, err)
	} else {
		cfg.inject = lines
		log.Printf("info-proxy: loaded %d inject line(s) from %s", len(lines), injectFile)
	}

	clusterFile := getenv("CLUSTER_INFO_FILE", "/etc/info-proxy/cluster_info.txt")
	if b, err := os.ReadFile(clusterFile); err == nil && len(bytes.TrimSpace(b)) > 0 {
		cfg.clusterInfoText = normalizeCRLF(string(b))
		log.Printf("info-proxy: will serve canned CLUSTER INFO from %s", clusterFile)
	}

	ln, err := net.Listen("tcp", cfg.listenAddr)
	if err != nil {
		log.Fatalf("info-proxy: listen %s: %v", cfg.listenAddr, err)
	}
	log.Printf("info-proxy: listening on %s -> backend %s", cfg.listenAddr, cfg.backendAddr)

	for {
		conn, err := ln.Accept()
		if err != nil {
			log.Printf("info-proxy: accept: %v", err)
			continue
		}
		go handle(conn, cfg)
	}
}

// handle proxies one client connection over a dedicated backend connection,
// preserving per-connection AUTH and the negotiated RESP version. It assumes one
// reply per request (true for both scrapers); it does not model SUBSCRIBE/MONITOR
// push frames, which neither uses.
func handle(client net.Conn, cfg config) {
	defer client.Close()

	backend, err := net.Dial("tcp", cfg.backendAddr)
	if err != nil {
		log.Printf("info-proxy: dial backend %s: %v", cfg.backendAddr, err)
		return
	}
	defer backend.Close()

	cr := bufio.NewReader(client)
	br := bufio.NewReader(backend)

	for {
		raw, args, err := readRequest(cr)
		if len(raw) == 0 || len(args) == 0 {
			if err != nil {
				return
			}
			// Nothing actionable (e.g. a stray newline); forward and continue.
			if len(raw) > 0 {
				if _, werr := backend.Write(raw); werr != nil {
					return
				}
			}
			continue
		}

		cmd := strings.ToUpper(string(args[0]))
		var sub string
		if len(args) > 1 {
			sub = strings.ToUpper(string(args[1]))
		}

		// Serve a canned CLUSTER INFO without touching the backend so a
		// standalone instance can present as cluster-enabled.
		if cfg.clusterInfoText != "" && cmd == "CLUSTER" && sub == "INFO" {
			if _, werr := client.Write(encodeBulk(cfg.clusterInfoText)); werr != nil {
				return
			}
			if err != nil {
				return
			}
			continue
		}

		if _, werr := backend.Write(raw); werr != nil {
			return
		}

		reply, rerr := readReply(br)
		if cmd == "INFO" && isFullInfo(args) && len(cfg.inject) > 0 {
			reply = rewriteInfoReply(reply, cfg.inject)
		}
		if _, werr := client.Write(reply); werr != nil {
			return
		}

		if err != nil || rerr != nil {
			return
		}
	}
}

// isFullInfo reports whether an INFO request targets the full metric set, which
// is what both scrapers request ("INFO all"). Section-scoped requests such as
// "INFO commandstats" or "INFO keyspace" are left untouched so their narrowly
// parsed replies are not polluted with injected fields.
func isFullInfo(args [][]byte) bool {
	if len(args) == 1 {
		return true // bare INFO -> default sections
	}
	switch strings.ToLower(string(args[1])) {
	case "all", "everything", "default":
		return true
	}
	return false
}
