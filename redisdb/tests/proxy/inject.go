// INFO-reply rewriting: overriding existing fields and appending faked ones.
package main

import (
	"bufio"
	"bytes"
	"os"
	"strconv"
	"strings"
)

// loadInjectLines reads a file of `key:value` INFO lines. Blank lines and lines
// beginning with '#' are ignored, so the file can be commented and grouped.
func loadInjectLines(path string) ([][]byte, error) {
	f, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer f.Close()

	var lines [][]byte
	sc := bufio.NewScanner(f)
	sc.Buffer(make([]byte, 1024*1024), 1024*1024)
	for sc.Scan() {
		ln := bytes.TrimRight(sc.Bytes(), "\r\n")
		trimmed := bytes.TrimSpace(ln)
		if len(trimmed) == 0 || trimmed[0] == '#' {
			continue
		}
		if bytes.IndexByte(ln, ':') < 0 {
			continue // not a key:value line
		}
		// Copy: Scanner reuses its buffer between iterations.
		cp := make([]byte, len(ln))
		copy(cp, ln)
		lines = append(lines, cp)
	}
	return lines, sc.Err()
}

func lineKey(line []byte) string {
	if i := bytes.IndexByte(line, ':'); i >= 0 {
		return string(line[:i])
	}
	return string(line)
}

// applyInject overrides any existing INFO field whose key matches an inject
// line and appends the rest under a "# Faked" section. Redis clients parse INFO
// as flat key:value pairs, so the section header is cosmetic; blank lines are
// ignored by both parsers.
func applyInject(payload []byte, inject [][]byte) []byte {
	override := make(map[string][]byte, len(inject))
	for _, il := range inject {
		override[lineKey(il)] = il
	}

	lines := bytes.Split(payload, []byte("\r\n"))
	used := make(map[string]bool, len(inject))
	out := make([][]byte, 0, len(lines)+len(inject)+2)
	for _, ln := range lines {
		if i := bytes.IndexByte(ln, ':'); i >= 0 {
			k := string(ln[:i])
			if rep, ok := override[k]; ok {
				out = append(out, rep)
				used[k] = true
				continue
			}
		}
		out = append(out, ln)
	}

	appended := false
	for _, il := range inject {
		if used[lineKey(il)] {
			continue
		}
		if !appended {
			out = append(out, []byte("# Faked"))
			appended = true
		}
		out = append(out, il)
	}

	// Preserve the trailing CRLF that a real INFO payload ends with.
	out = append(out, []byte(""))
	return bytes.Join(out, []byte("\r\n"))
}

// rewriteInfoReply rewrites the payload of a bulk ('$') or verbatim ('=') INFO
// reply and re-frames it with the corrected length. Non-string replies (e.g. an
// error) are returned untouched.
func rewriteInfoReply(reply []byte, inject [][]byte) []byte {
	if len(reply) == 0 {
		return reply
	}
	t := reply[0]
	if t != '$' && t != '=' {
		return reply
	}
	nl := bytes.IndexByte(reply, '\n')
	if nl < 0 {
		return reply
	}
	n := parseLen(reply[1 : nl+1])
	if n < 0 || nl+1+n > len(reply) {
		return reply
	}
	payload := reply[nl+1 : nl+1+n]

	newPayload := applyInject(payload, inject)

	out := make([]byte, 0, len(newPayload)+16)
	out = append(out, t)
	out = append(out, []byte(strconv.Itoa(len(newPayload)))...)
	out = append(out, '\r', '\n')
	out = append(out, newPayload...)
	out = append(out, '\r', '\n')
	return out
}

// normalizeCRLF rewrites all line endings to CRLF and guarantees a trailing
// CRLF. CLUSTER INFO replies are parsed by splitting on "\r\n" (by both redis-py
// and the receiver), so a canned reply authored with plain "\n" must be
// converted or it parses as a single unusable line.
func normalizeCRLF(s string) string {
	s = strings.ReplaceAll(s, "\r\n", "\n")
	s = strings.ReplaceAll(s, "\n", "\r\n")
	if !strings.HasSuffix(s, "\r\n") {
		s += "\r\n"
	}
	return s
}

// encodeBulk frames a string as a RESP bulk string reply.
func encodeBulk(s string) []byte {
	out := make([]byte, 0, len(s)+16)
	out = append(out, '$')
	out = append(out, []byte(strconv.Itoa(len(s)))...)
	out = append(out, '\r', '\n')
	out = append(out, []byte(s)...)
	out = append(out, '\r', '\n')
	return out
}
