package main

import (
	"bufio"
	"bytes"
	"strconv"
	"strings"
	"testing"
)

func reader(s string) *bufio.Reader {
	return bufio.NewReader(strings.NewReader(s))
}

func TestReadReplyBulk(t *testing.T) {
	raw, err := readReply(reader("$5\r\nhello\r\n"))
	if err != nil {
		t.Fatal(err)
	}
	if string(raw) != "$5\r\nhello\r\n" {
		t.Fatalf("got %q", raw)
	}
}

func TestReadReplyNullBulk(t *testing.T) {
	raw, _ := readReply(reader("$-1\r\n"))
	if string(raw) != "$-1\r\n" {
		t.Fatalf("got %q", raw)
	}
}

func TestReadReplyArray(t *testing.T) {
	in := "*2\r\n$3\r\nfoo\r\n:42\r\n"
	raw, err := readReply(reader(in))
	if err != nil {
		t.Fatal(err)
	}
	if string(raw) != in {
		t.Fatalf("got %q", raw)
	}
}

func TestReadReplyRESP3Map(t *testing.T) {
	// %1 { "proto" => 3 } as sent by HELLO-style replies
	in := "%1\r\n$5\r\nproto\r\n:3\r\n"
	raw, err := readReply(reader(in))
	if err != nil {
		t.Fatal(err)
	}
	if string(raw) != in {
		t.Fatalf("got %q", raw)
	}
}

func TestReadReplyRESP3Attribute(t *testing.T) {
	// |1 attribute prefix followed by the real reply (+OK)
	in := "|1\r\n$3\r\nkey\r\n$3\r\nval\r\n+OK\r\n"
	raw, err := readReply(reader(in))
	if err != nil {
		t.Fatal(err)
	}
	if string(raw) != in {
		t.Fatalf("got %q", raw)
	}
}

func TestReadReplyVerbatim(t *testing.T) {
	in := "=15\r\ntxt:hello world\r\n"
	raw, err := readReply(reader(in))
	if err != nil {
		t.Fatal(err)
	}
	if string(raw) != in {
		t.Fatalf("got %q", raw)
	}
}

func TestReadRequestArray(t *testing.T) {
	in := "*2\r\n$4\r\nINFO\r\n$3\r\nall\r\n"
	raw, args, err := readRequest(reader(in))
	if err != nil {
		t.Fatal(err)
	}
	if string(raw) != in {
		t.Fatalf("raw %q", raw)
	}
	if len(args) != 2 || string(args[0]) != "INFO" || string(args[1]) != "all" {
		t.Fatalf("args %q", args)
	}
}

func TestReadRequestInline(t *testing.T) {
	_, args, err := readRequest(reader("PING\r\n"))
	if err != nil {
		t.Fatal(err)
	}
	if len(args) != 1 || string(args[0]) != "PING" {
		t.Fatalf("args %q", args)
	}
}

func TestIsFullInfo(t *testing.T) {
	cases := []struct {
		args [][]byte
		want bool
	}{
		{[][]byte{[]byte("INFO")}, true},
		{[][]byte{[]byte("INFO"), []byte("all")}, true},
		{[][]byte{[]byte("INFO"), []byte("everything")}, true},
		{[][]byte{[]byte("INFO"), []byte("commandstats")}, false},
		{[][]byte{[]byte("INFO"), []byte("keyspace")}, false},
	}
	for _, c := range cases {
		if got := isFullInfo(c.args); got != c.want {
			t.Errorf("isFullInfo(%q)=%v want %v", c.args, got, c.want)
		}
	}
}

func TestApplyInjectAppend(t *testing.T) {
	payload := []byte("# Server\r\nredis_version:7.2.0\r\n")
	inject := [][]byte{[]byte("bytes_received_per_sec:123")}
	out := applyInject(payload, inject)
	if !bytes.Contains(out, []byte("bytes_received_per_sec:123")) {
		t.Fatalf("append missing: %q", out)
	}
	if !bytes.Contains(out, []byte("redis_version:7.2.0")) {
		t.Fatalf("original dropped: %q", out)
	}
}

func TestApplyInjectOverride(t *testing.T) {
	payload := []byte("# Cluster\r\ncluster_enabled:0\r\n")
	inject := [][]byte{[]byte("cluster_enabled:1")}
	out := applyInject(payload, inject)
	if bytes.Contains(out, []byte("cluster_enabled:0")) {
		t.Fatalf("original value not overridden: %q", out)
	}
	if !bytes.Contains(out, []byte("cluster_enabled:1")) {
		t.Fatalf("override missing: %q", out)
	}
	// Override must not also append a duplicate under "# Faked".
	if bytes.Count(out, []byte("cluster_enabled:")) != 1 {
		t.Fatalf("duplicate key after override: %q", out)
	}
}

func TestRewriteInfoReplyReframesLength(t *testing.T) {
	payload := "redis_version:7.2.0\r\n"
	reply := []byte("$" + strconv.Itoa(len(payload)) + "\r\n" + payload + "\r\n")
	inject := [][]byte{[]byte("sentinel_masters:2")}
	out := rewriteInfoReply(reply, inject)

	// Parse the reframed reply back and confirm the declared length matches.
	raw, err := readReply(reader(string(out)))
	if err != nil {
		t.Fatalf("reframed reply unreadable: %v (%q)", err, out)
	}
	if !bytes.Equal(raw, out) {
		t.Fatalf("reframed length mismatch: reader consumed %q of %q", raw, out)
	}
	if !bytes.Contains(out, []byte("sentinel_masters:2")) {
		t.Fatalf("inject missing: %q", out)
	}
}

func TestRewriteInfoReplyLeavesErrorsAlone(t *testing.T) {
	reply := []byte("-ERR unknown\r\n")
	out := rewriteInfoReply(reply, [][]byte{[]byte("x:1")})
	if !bytes.Equal(out, reply) {
		t.Fatalf("error reply modified: %q", out)
	}
}
