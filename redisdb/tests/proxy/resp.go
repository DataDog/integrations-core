// RESP framing for the INFO-rewrite proxy.
//
// The proxy only needs to (a) split the client->server stream into individual
// requests so it can spot the INFO command, and (b) split the server->client
// stream into individual replies so it can rewrite exactly the reply that
// belongs to an INFO request and forward everything else untouched. It never
// needs to interpret values beyond finding their byte boundaries, so the reader
// captures raw bytes and returns them verbatim.
//
// Both RESP2 and RESP3 are supported because the two scrapers negotiate
// different protocols: the Datadog redisdb check pins RESP2 (protocol=2) while
// the OpenTelemetry redisreceiver's go-redis client negotiates RESP3 via HELLO.
package main

import (
	"bufio"
	"bytes"
	"io"
	"strconv"
)

// readLine reads through the next \n and returns the bytes including the
// trailing CRLF. The RESP grammar terminates every framing token with CRLF.
func readLine(r *bufio.Reader) ([]byte, error) {
	line, err := r.ReadBytes('\n')
	if err != nil {
		return line, err
	}
	return line, nil
}

// parseLen parses the integer count that follows a RESP type byte (e.g. the
// "5" in "$5\r\n"). It tolerates the trailing CRLF and any RESP3 streaming
// marker ("?"), returning -1 when the count cannot be parsed (treated as null).
func parseLen(b []byte) int {
	s := string(bytes.TrimRight(b, "\r\n"))
	if s == "" || s == "?" {
		return -1
	}
	n, err := strconv.Atoi(s)
	if err != nil {
		return -1
	}
	return n
}

// readReply reads one complete RESP value of any type and returns its raw
// bytes. Aggregate types (arrays, maps, sets, pushes, attributes) are read
// recursively so nested values are captured whole. This is what lets the proxy
// forward every non-INFO reply byte-for-byte.
func readReply(r *bufio.Reader) ([]byte, error) {
	line, err := readLine(r)
	if err != nil {
		return line, err
	}
	if len(line) == 0 {
		return line, nil
	}

	switch line[0] {
	// Single-line replies: simple string, error, integer, null, boolean,
	// double, big number. The whole value is the line itself.
	case '+', '-', ':', '_', '#', ',', '(':
		return line, nil

	// Length-prefixed blobs: bulk string, blob error, verbatim string.
	// A negative length is the RESP2 null bulk string ("$-1\r\n").
	case '$', '!', '=':
		n := parseLen(line[1:])
		if n < 0 {
			return line, nil
		}
		buf := make([]byte, n+2) // payload + CRLF
		if _, err := io.ReadFull(r, buf); err != nil {
			return append(line, buf...), err
		}
		return append(line, buf...), nil

	// Aggregates with N elements: array, set, push.
	case '*', '~', '>':
		count := parseLen(line[1:])
		out := line
		if count < 0 {
			return out, nil
		}
		for i := 0; i < count; i++ {
			child, err := readReply(r)
			out = append(out, child...)
			if err != nil {
				return out, err
			}
		}
		return out, nil

	// Aggregates with N key/value pairs: map, attribute. An attribute block
	// ("|") is a metadata prefix that is followed by the actual reply, so we
	// read one more value after it to complete the logical reply.
	case '%', '|':
		count := parseLen(line[1:])
		out := line
		if count >= 0 {
			for i := 0; i < count*2; i++ {
				child, err := readReply(r)
				out = append(out, child...)
				if err != nil {
					return out, err
				}
			}
		}
		if line[0] == '|' {
			child, err := readReply(r)
			out = append(out, child...)
			if err != nil {
				return out, err
			}
		}
		return out, nil

	default:
		// Inline/unknown: forward the single line best-effort.
		return line, nil
	}
}

// readRequest reads one client request and returns its raw bytes plus the
// decoded argument list (used only to identify the command). Clients always
// send commands as RESP arrays of bulk strings regardless of the negotiated
// protocol version; inline commands are handled as a fallback for humans using
// a raw socket.
func readRequest(r *bufio.Reader) (raw []byte, args [][]byte, err error) {
	line, err := readLine(r)
	if err != nil {
		return line, nil, err
	}
	if len(line) == 0 {
		return line, nil, nil
	}

	if line[0] != '*' {
		// Inline command: whitespace-separated tokens on one line.
		for _, f := range bytes.Fields(bytes.TrimRight(line, "\r\n")) {
			args = append(args, f)
		}
		return line, args, nil
	}

	n := parseLen(line[1:])
	raw = append(raw, line...)
	for i := 0; i < n; i++ {
		l2, err := readLine(r)
		raw = append(raw, l2...)
		if err != nil {
			return raw, args, err
		}
		if len(l2) == 0 || l2[0] != '$' {
			continue
		}
		ln := parseLen(l2[1:])
		if ln < 0 {
			continue
		}
		buf := make([]byte, ln+2) // payload + CRLF
		if _, err := io.ReadFull(r, buf); err != nil {
			raw = append(raw, buf...)
			return raw, args, err
		}
		raw = append(raw, buf...)
		args = append(args, buf[:ln])
	}
	return raw, args, nil
}
