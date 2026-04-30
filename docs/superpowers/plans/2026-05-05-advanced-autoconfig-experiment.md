# Advanced Auto-Config — KrakenD Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Demonstrate end-to-end that the Datadog Agent can discover the OpenMetrics endpoint of a KrakenD container via a declarative `auto_conf_discovery.yaml`, schedule the krakend check with the discovered port, and emit metrics — without any per-integration discovery code.

**Architecture:** Add a `discovery:` block to a new `auto_conf_discovery.yaml` file format that the file config provider reads. When AutoDiscovery matches a service to such a template, run a generic OpenMetrics prober against the container's exposed ports (hint ports first, full scan as fallback), verify the response is Prometheus-format, and resolve a new `%%discovered_port%%` template variable from the probe result. The resolution happens by wrapping the matched `Service` with a `serviceWithProbeResult` shim so existing call sites of `configresolver.Resolve` are unchanged.

**Tech Stack:** Go 1.22+ (`datadog-agent`), YAML, Python 3.13 (krakend integration), Docker. Build via `dda inv agent.build`. Tests via `dda inv test --targets=...` (never raw `go test` — see `datadog-agent/AGENTS.md`).

**Spec:** `docs/superpowers/specs/2026-05-05-advanced-autoconfig-experiment-design.md` in `integrations-core`.

**Repos involved:**
- `/home/vagrant/go/src/github.com/DataDog/integrations-core` — branch `vitkyrka/disco-autoconfig`. One new YAML file.
- `/home/vagrant/go/src/github.com/DataDog/datadog-agent` — feature branch to be created. Most of the work lives here.

**Commit policy (per `datadog-agent/CLAUDE_PERSONAL.md`):** Never amend commits — make new fixup commits on top instead. Never disable signing. Never bypass hooks with `--no-verify`. PRs as drafts only.

---

## File structure

### `integrations-core` (branch `vitkyrka/disco-autoconfig`)
- Create: `krakend/datadog_checks/krakend/data/auto_conf_discovery.yaml`

### `datadog-agent` (new feature branch)
- Modify: `comp/core/autodiscovery/integration/config.go` — add `DiscoveryConfig` struct + `Discovery *DiscoveryConfig` field on `Config`.
- Modify: `comp/core/autodiscovery/providers/config_reader.go` — add `auto_conf_discovery.yaml` to the file lookup; parse `discovery:` block.
- Modify: `comp/core/autodiscovery/providers/config_reader_test.go` — round-trip test for the new file.
- Create: `comp/core/autodiscovery/discovery/types.go` — `DiscoveryConfig` mirror, `ProbeResult` struct, `Prober` interface.
- Create: `comp/core/autodiscovery/discovery/candidates.go` — port ordering helper.
- Create: `comp/core/autodiscovery/discovery/candidates_test.go`.
- Create: `comp/core/autodiscovery/discovery/openmetrics_prober.go` — HTTP probe + Prometheus verification + cache.
- Create: `comp/core/autodiscovery/discovery/openmetrics_prober_test.go`.
- Create: `comp/core/autodiscovery/discovery/cache.go` — TTL cache used by the prober.
- Create: `comp/core/autodiscovery/discovery/cache_test.go`.
- Create: `comp/core/autodiscovery/discovery/service_wrapper.go` — `serviceWithProbeResult` shim that injects `discovered_port` via `GetExtraConfig`.
- Modify: `pkg/util/tmplvar/resolver.go` — register `"discovered"` → `GetDiscoveredPort`.
- Modify: `pkg/util/tmplvar/resolver_test.go` — tests for the new variable.
- Modify: `comp/core/autodiscovery/autodiscoveryimpl/configmgr.go` — call `Prober.Probe(...)` before `configresolver.Resolve`; wrap service with the probe result.

`configresolver.Resolve(tpl, svc)` keeps its current two-argument signature. The probe result reaches the resolver via the wrapped `Service` rather than a new function parameter — simpler than the spec's working assumption.

---

## Task 1: Add `auto_conf_discovery.yaml` to the krakend integration

Sets up the integration-side trigger artifact. Standalone — no Agent code needed yet.

**Files:**
- Create: `/home/vagrant/go/src/github.com/DataDog/integrations-core/krakend/datadog_checks/krakend/data/auto_conf_discovery.yaml`

- [ ] **Step 1: Create the file.**

```yaml
ad_identifiers:
  - krakend
discovery:
  type: openmetrics
  ports: [8090]
  path: /metrics
init_config:
instances:
  - openmetrics_endpoint: "http://%%host%%:%%discovered_port%%/metrics"
```

- [ ] **Step 2: Verify it's valid YAML.**

Run: `python3 -c "import yaml,sys; yaml.safe_load(open('/home/vagrant/go/src/github.com/DataDog/integrations-core/krakend/datadog_checks/krakend/data/auto_conf_discovery.yaml'))"`
Expected: no output, exit 0.

- [ ] **Step 3: Commit.**

```bash
cd /home/vagrant/go/src/github.com/DataDog/integrations-core
git add krakend/datadog_checks/krakend/data/auto_conf_discovery.yaml
git commit -m "$(cat <<'EOF'
krakend: add auto_conf_discovery.yaml for advanced auto-config experiment

Declares the krakend ad_identifier with an OpenMetrics probe spec
(default port 8090, /metrics path). Consumed by the new
auto_conf_discovery file format in datadog-agent.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Create a feature branch in datadog-agent

**Files:** none. Branching only.

- [ ] **Step 1: Create the feature branch.**

Run:
```bash
cd /home/vagrant/go/src/github.com/DataDog/datadog-agent
git fetch origin
git checkout -b vitkyrka/advanced-autoconfig-krakend origin/main
```

Expected: switched to a new branch off `origin/main`.

- [ ] **Step 2: Verify clean tree.**

Run: `git status --short`
Expected: empty output.

---

## Task 3: Add the `DiscoveryConfig` struct to `integration.Config`

Defines the canonical type the rest of the system consumes.

**Files:**
- Modify: `/home/vagrant/go/src/github.com/DataDog/datadog-agent/comp/core/autodiscovery/integration/config.go`
- Modify: `/home/vagrant/go/src/github.com/DataDog/datadog-agent/comp/core/autodiscovery/integration/config_test.go` (or create if absent — verify with `ls`).

- [ ] **Step 1: Write the failing test.**

Append to `comp/core/autodiscovery/integration/config_test.go`:

```go
func TestDiscoveryConfig_FieldsAndZeroValue(t *testing.T) {
	var c Config
	if c.Discovery != nil {
		t.Fatalf("Discovery should default to nil, got %+v", c.Discovery)
	}

	c.Discovery = &DiscoveryConfig{
		Type:  "openmetrics",
		Ports: []int{8090},
		Path:  "/metrics",
	}
	if c.Discovery.Type != "openmetrics" {
		t.Fatalf("Type round-trip failed: %s", c.Discovery.Type)
	}
	if got, want := len(c.Discovery.Ports), 1; got != want {
		t.Fatalf("Ports length: got %d want %d", got, want)
	}
	if c.Discovery.Path != "/metrics" {
		t.Fatalf("Path round-trip failed: %s", c.Discovery.Path)
	}
}
```

- [ ] **Step 2: Run the test and confirm it fails.**

Run: `dda inv test --targets=./comp/core/autodiscovery/integration/ -- -run TestDiscoveryConfig_FieldsAndZeroValue`
Expected: build error — `undefined: DiscoveryConfig`.

- [ ] **Step 3: Implement the struct.**

In `comp/core/autodiscovery/integration/config.go`, find the `Config` struct (around line 47). Add a new field at the end of the struct, just before the closing `}`:

```go
	// Discovery, when non-nil, signals that this config is a discovery
	// template: AutoDiscovery must run a probe against the matched service
	// before substituting %%discovered_port%%.
	Discovery *DiscoveryConfig `json:"discovery"` // (include in digest: true)
```

Then, after the `Config` type declaration (before the next type), add:

```go
// DiscoveryConfig describes how to probe a service to find its check
// endpoint. Currently only Type=="openmetrics" is supported.
type DiscoveryConfig struct {
	Type  string `yaml:"type"  json:"type"`
	Ports []int  `yaml:"ports,omitempty" json:"ports,omitempty"`
	Path  string `yaml:"path,omitempty"  json:"path,omitempty"`
}
```

- [ ] **Step 4: Run the test and confirm it passes.**

Run: `dda inv test --targets=./comp/core/autodiscovery/integration/ -- -run TestDiscoveryConfig_FieldsAndZeroValue`
Expected: PASS.

- [ ] **Step 5: Run the full integration package test to make sure nothing else broke.**

Run: `dda inv test --targets=./comp/core/autodiscovery/integration/`
Expected: PASS.

- [ ] **Step 6: Commit.**

```bash
git add comp/core/autodiscovery/integration/config.go comp/core/autodiscovery/integration/config_test.go
git commit -m "autodiscovery: add DiscoveryConfig type to integration.Config

For the advanced auto-config experiment. New optional field on
integration.Config, populated by the auto_conf_discovery.yaml provider
in a follow-up commit.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 4: Parse `auto_conf_discovery.yaml` in the file config provider

Make the file provider recognise the new file alongside `auto_conf.yaml` and populate `Config.Discovery`.

**Files:**
- Modify: `comp/core/autodiscovery/providers/config_reader.go`
- Modify: `comp/core/autodiscovery/providers/config_reader_test.go`

- [ ] **Step 1: Write the failing test.**

Append to `comp/core/autodiscovery/providers/config_reader_test.go`:

```go
func TestReadConfigFiles_AutoConfDiscovery(t *testing.T) {
	tmp := t.TempDir()
	intDir := filepath.Join(tmp, "krakend.d")
	if err := os.MkdirAll(intDir, 0755); err != nil {
		t.Fatal(err)
	}
	yamlBody := []byte(`ad_identifiers:
  - krakend
discovery:
  type: openmetrics
  ports: [8090]
  path: /metrics
init_config:
instances:
  - openmetrics_endpoint: "http://%%host%%:%%discovered_port%%/metrics"
`)
	if err := os.WriteFile(filepath.Join(intDir, "auto_conf_discovery.yaml"), yamlBody, 0644); err != nil {
		t.Fatal(err)
	}

	pkgconfigsetup.Datadog().SetWithoutSource("confd_path", tmp)
	t.Cleanup(func() {
		pkgconfigsetup.Datadog().SetWithoutSource("confd_path", "")
	})

	configs, _, _ := ReadConfigFiles(GetAll)
	var found *integration.Config
	for i := range configs {
		if configs[i].Name == "krakend" && configs[i].Discovery != nil {
			found = &configs[i]
			break
		}
	}
	if found == nil {
		t.Fatalf("did not find krakend config with Discovery set; got %d configs", len(configs))
	}
	if found.Discovery.Type != "openmetrics" {
		t.Fatalf("Type: got %q want %q", found.Discovery.Type, "openmetrics")
	}
	if !reflect.DeepEqual(found.Discovery.Ports, []int{8090}) {
		t.Fatalf("Ports: got %+v want [8090]", found.Discovery.Ports)
	}
	if found.Discovery.Path != "/metrics" {
		t.Fatalf("Path: got %q want %q", found.Discovery.Path, "/metrics")
	}
	if got := len(found.ADIdentifiers); got != 1 || found.ADIdentifiers[0] != "krakend" {
		t.Fatalf("ADIdentifiers: got %+v", found.ADIdentifiers)
	}
}
```

If `reflect` is not yet imported in the test file, add it.

- [ ] **Step 2: Run the test and confirm it fails.**

Run: `dda inv test --targets=./comp/core/autodiscovery/providers/ -- -run TestReadConfigFiles_AutoConfDiscovery`
Expected: FAIL — config not found, or `Discovery` is nil because the new field is not parsed yet.

- [ ] **Step 3: Implement the parsing.**

In `comp/core/autodiscovery/providers/config_reader.go`:

3a. Find the `configFormat` struct (around line 34). Add a `Discovery` field at the end:

```go
	Discovery               *integration.DiscoveryConfig       `yaml:"discovery,omitempty"`
```

3b. Find the function that copies parsed YAML fields onto the returned `integration.Config` (around line 490, where `conf.ADIdentifiers = cf.ADIdentifiers` and `conf.AdvancedADIdentifiers = cf.AdvancedADIdentifiers` are set). Add immediately after those lines:

```go
	conf.Discovery = cf.Discovery
```

3c. The file lookup currently includes `auto_conf.yaml` because of the loop in `collectEntry`/`collectDir` that iterates *all* `.yaml` files. `auto_conf_discovery.yaml` ends in `.yaml`, so it is already eligible. Verify by reading lines 290–340 of `config_reader.go`. If a special-case branch references `"auto_conf.yaml"` *exclusively* (other than the existing `ignore_autoconf` early-return at line 301), broaden it to also accept `"auto_conf_discovery.yaml"`. The existing `ignore_autoconf` early-return is independent and does not need changing for this experiment.

- [ ] **Step 4: Run the test and confirm it passes.**

Run: `dda inv test --targets=./comp/core/autodiscovery/providers/ -- -run TestReadConfigFiles_AutoConfDiscovery`
Expected: PASS.

- [ ] **Step 5: Run the full provider package test.**

Run: `dda inv test --targets=./comp/core/autodiscovery/providers/`
Expected: PASS.

- [ ] **Step 6: Commit.**

```bash
git add comp/core/autodiscovery/providers/config_reader.go comp/core/autodiscovery/providers/config_reader_test.go
git commit -m "autodiscovery/providers: parse auto_conf_discovery.yaml

Recognise the discovery: block in the file format and populate
integration.Config.Discovery. The file is picked up via the same .yaml
filename matcher that handles auto_conf.yaml today.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 5: Discovery package — types and `ProbeResult`

Lay down the package skeleton: shared types used by all later tasks. Tests come with the prober task, not here.

**Files:**
- Create: `comp/core/autodiscovery/discovery/types.go`

- [ ] **Step 1: Create the file.**

```go
// Unless explicitly stated otherwise all files in this repository are licensed
// under the Apache License Version 2.0.
// This product includes software developed at Datadog (https://www.datadoghq.com/).
// Copyright 2016-present Datadog, Inc.

// Package discovery implements probe-based "advanced auto-config" — running
// a verifying probe against a discovered Service to derive instance config
// values that cannot be expressed by template substitution alone.
package discovery

import (
	"context"

	"github.com/DataDog/datadog-agent/comp/core/autodiscovery/integration"
	"github.com/DataDog/datadog-agent/comp/core/autodiscovery/listeners"
)

// ProbeResult is the outcome of a successful probe.
type ProbeResult struct {
	// Port is the discovered TCP port that responded successfully to the
	// probe.
	Port uint16
}

// Prober probes a Service against a DiscoveryConfig and returns a result
// when one of the candidate (host, port, path) tuples verifies. If no
// candidate verifies within the budget, ok is false.
type Prober interface {
	Probe(ctx context.Context, cfg *integration.DiscoveryConfig, svc listeners.Service) (result ProbeResult, ok bool)
}
```

- [ ] **Step 2: Verify it builds.**

Run: `dda inv test --targets=./comp/core/autodiscovery/discovery/`
Expected: PASS (no tests yet, but the package must compile).

- [ ] **Step 3: Commit.**

```bash
git add comp/core/autodiscovery/discovery/types.go
git commit -m "autodiscovery/discovery: scaffold package with ProbeResult/Prober types

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 6: Discovery package — candidate port ordering

Pure function. Trivial to test in isolation.

**Files:**
- Create: `comp/core/autodiscovery/discovery/candidates.go`
- Create: `comp/core/autodiscovery/discovery/candidates_test.go`

- [ ] **Step 1: Write the failing test.**

Create `comp/core/autodiscovery/discovery/candidates_test.go`:

```go
// Unless explicitly stated otherwise all files in this repository are licensed
// under the Apache License Version 2.0.
// This product includes software developed at Datadog (https://www.datadoghq.com/).
// Copyright 2016-present Datadog, Inc.

package discovery

import (
	"reflect"
	"testing"

	workloadmeta "github.com/DataDog/datadog-agent/comp/core/workloadmeta/def"
)

func TestCandidatePorts(t *testing.T) {
	exposed := []workloadmeta.ContainerPort{{Port: 9000}, {Port: 8090}, {Port: 9001}}

	tests := []struct {
		name  string
		hints []int
		want  []uint16
	}{
		{"no hints — fallback only", nil, []uint16{9000, 8090, 9001}},
		{"hint matches one exposed", []int{8090}, []uint16{8090, 9000, 9001}},
		{"hint not exposed is dropped", []int{1234}, []uint16{9000, 8090, 9001}},
		{"two hints, declared order preserved", []int{8090, 9000}, []uint16{8090, 9000, 9001}},
		{"empty exposed yields empty", nil, []uint16{}},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			ex := exposed
			if tc.name == "empty exposed yields empty" {
				ex = nil
			}
			got := candidatePorts(tc.hints, ex)
			if !reflect.DeepEqual(got, tc.want) {
				t.Fatalf("got %+v want %+v", got, tc.want)
			}
		})
	}
}
```

- [ ] **Step 2: Run the test and confirm it fails.**

Run: `dda inv test --targets=./comp/core/autodiscovery/discovery/ -- -run TestCandidatePorts`
Expected: FAIL — `undefined: candidatePorts`.

- [ ] **Step 3: Implement.**

Create `comp/core/autodiscovery/discovery/candidates.go`:

```go
// Unless explicitly stated otherwise all files in this repository are licensed
// under the Apache License Version 2.0.
// This product includes software developed at Datadog (https://www.datadoghq.com/).
// Copyright 2016-present Datadog, Inc.

package discovery

import (
	workloadmeta "github.com/DataDog/datadog-agent/comp/core/workloadmeta/def"
)

func candidatePorts(hints []int, exposed []workloadmeta.ContainerPort) []uint16 {
	exposedSet := make(map[uint16]struct{}, len(exposed))
	for _, p := range exposed {
		exposedSet[uint16(p.Port)] = struct{}{}
	}

	out := make([]uint16, 0, len(exposed))
	seen := make(map[uint16]struct{}, len(exposed))

	for _, h := range hints {
		p := uint16(h)
		if _, ok := exposedSet[p]; !ok {
			continue
		}
		if _, dup := seen[p]; dup {
			continue
		}
		out = append(out, p)
		seen[p] = struct{}{}
	}

	for _, p := range exposed {
		port := uint16(p.Port)
		if _, dup := seen[port]; dup {
			continue
		}
		out = append(out, port)
		seen[port] = struct{}{}
	}

	return out
}
```

- [ ] **Step 4: Run the test and confirm it passes.**

Run: `dda inv test --targets=./comp/core/autodiscovery/discovery/ -- -run TestCandidatePorts`
Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add comp/core/autodiscovery/discovery/candidates.go comp/core/autodiscovery/discovery/candidates_test.go
git commit -m "autodiscovery/discovery: candidate port ordering

Hints first (when exposed), then remaining exposed ports in declared
order. Dedup-aware.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 7: Discovery package — TTL cache

Records probe outcomes per `(serviceID, configHash)` so we don't re-probe a known-good (or recently-failed) service on every reconcile.

**Files:**
- Create: `comp/core/autodiscovery/discovery/cache.go`
- Create: `comp/core/autodiscovery/discovery/cache_test.go`

- [ ] **Step 1: Write the failing test.**

Create `comp/core/autodiscovery/discovery/cache_test.go`:

```go
// Unless explicitly stated otherwise all files in this repository are licensed
// under the Apache License Version 2.0.
// This product includes software developed at Datadog (https://www.datadoghq.com/).
// Copyright 2016-present Datadog, Inc.

package discovery

import (
	"testing"
	"time"
)

func TestProbeCache_HitAndExpiry(t *testing.T) {
	now := time.Unix(1_700_000_000, 0)
	clock := func() time.Time { return now }
	c := newProbeCache(clock)

	// Empty cache — miss.
	if _, _, ok := c.get("svc1", "h1"); ok {
		t.Fatal("expected miss on empty cache")
	}

	// Successful probe entry, never expires.
	c.putSuccess("svc1", "h1", ProbeResult{Port: 8090})
	if r, success, ok := c.get("svc1", "h1"); !ok || !success || r.Port != 8090 {
		t.Fatalf("expected hit success(8090); got ok=%v success=%v port=%d", ok, success, r.Port)
	}

	// Failed probe entry, expires after 30s.
	c.putFailure("svc1", "h2", 30*time.Second)
	if _, success, ok := c.get("svc1", "h2"); !ok || success {
		t.Fatal("expected hit failure")
	}
	now = now.Add(31 * time.Second)
	if _, _, ok := c.get("svc1", "h2"); ok {
		t.Fatal("expected miss after expiry")
	}
}

func TestProbeCache_DifferentKeysIsolated(t *testing.T) {
	now := time.Unix(0, 0)
	c := newProbeCache(func() time.Time { return now })
	c.putSuccess("svcA", "h1", ProbeResult{Port: 1})
	c.putSuccess("svcB", "h1", ProbeResult{Port: 2})
	if r, _, _ := c.get("svcA", "h1"); r.Port != 1 {
		t.Fatalf("svcA: got %d", r.Port)
	}
	if r, _, _ := c.get("svcB", "h1"); r.Port != 2 {
		t.Fatalf("svcB: got %d", r.Port)
	}
}
```

- [ ] **Step 2: Run the test and confirm it fails.**

Run: `dda inv test --targets=./comp/core/autodiscovery/discovery/ -- -run TestProbeCache`
Expected: FAIL — `undefined: newProbeCache` etc.

- [ ] **Step 3: Implement.**

Create `comp/core/autodiscovery/discovery/cache.go`:

```go
// Unless explicitly stated otherwise all files in this repository are licensed
// under the Apache License Version 2.0.
// This product includes software developed at Datadog (https://www.datadoghq.com/).
// Copyright 2016-present Datadog, Inc.

package discovery

import (
	"sync"
	"time"
)

type cacheEntry struct {
	result    ProbeResult
	success   bool
	expiresAt time.Time // zero = never
}

type probeCache struct {
	mu      sync.Mutex
	entries map[string]cacheEntry
	now     func() time.Time
}

func newProbeCache(now func() time.Time) *probeCache {
	if now == nil {
		now = time.Now
	}
	return &probeCache{entries: make(map[string]cacheEntry), now: now}
}

func cacheKey(svcID, cfgHash string) string {
	return svcID + "|" + cfgHash
}

func (c *probeCache) get(svcID, cfgHash string) (ProbeResult, bool, bool) {
	c.mu.Lock()
	defer c.mu.Unlock()
	e, ok := c.entries[cacheKey(svcID, cfgHash)]
	if !ok {
		return ProbeResult{}, false, false
	}
	if !e.expiresAt.IsZero() && c.now().After(e.expiresAt) {
		delete(c.entries, cacheKey(svcID, cfgHash))
		return ProbeResult{}, false, false
	}
	return e.result, e.success, true
}

func (c *probeCache) putSuccess(svcID, cfgHash string, r ProbeResult) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.entries[cacheKey(svcID, cfgHash)] = cacheEntry{result: r, success: true}
}

func (c *probeCache) putFailure(svcID, cfgHash string, ttl time.Duration) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.entries[cacheKey(svcID, cfgHash)] = cacheEntry{success: false, expiresAt: c.now().Add(ttl)}
}
```

- [ ] **Step 4: Run the test and confirm it passes.**

Run: `dda inv test --targets=./comp/core/autodiscovery/discovery/ -- -run TestProbeCache`
Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add comp/core/autodiscovery/discovery/cache.go comp/core/autodiscovery/discovery/cache_test.go
git commit -m "autodiscovery/discovery: TTL probe cache

Per-(serviceID, configHash) cache. Successes never expire;
failures expire after caller-supplied TTL.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 8: Discovery package — OpenMetrics prober

The HTTP probe + Prometheus-line verification + budget loop. Uses `httptest` for unit tests.

**Files:**
- Create: `comp/core/autodiscovery/discovery/openmetrics_prober.go`
- Create: `comp/core/autodiscovery/discovery/openmetrics_prober_test.go`

- [ ] **Step 1: Write the failing test.**

Create `comp/core/autodiscovery/discovery/openmetrics_prober_test.go`:

```go
// Unless explicitly stated otherwise all files in this repository are licensed
// under the Apache License Version 2.0.
// This product includes software developed at Datadog (https://www.datadoghq.com/).
// Copyright 2016-present Datadog, Inc.

package discovery

import (
	"context"
	"net"
	"net/http"
	"net/http/httptest"
	"strconv"
	"testing"
	"time"

	"github.com/DataDog/datadog-agent/comp/core/autodiscovery/integration"
	workloadmeta "github.com/DataDog/datadog-agent/comp/core/workloadmeta/def"
)

func TestVerifyOpenMetricsResponse(t *testing.T) {
	cases := []struct {
		name        string
		status      int
		contentType string
		body        string
		want        bool
	}{
		{"prom-text", 200, "text/plain; version=0.0.4", "go_goroutines 5\n", true},
		{"openmetrics-text", 200, "application/openmetrics-text; version=1.0.0", "go_goroutines 5\n", true},
		{"json", 200, "application/json", `{"a":1}`, false},
		{"html", 200, "text/html", "<html></html>", false},
		{"401", 401, "text/plain", "go_goroutines 5\n", false},
		{"prom-no-line", 200, "text/plain", "# HELP only\n# TYPE only\n", false},
		{"prom-with-labels", 200, "text/plain", `http_requests_total{code="200"} 1027` + "\n", true},
		{"prom-with-comments-first", 200, "text/plain", "# HELP foo bar\n# TYPE foo counter\nfoo 1\n", true},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := verifyOpenMetricsResponse(tc.status, tc.contentType, []byte(tc.body)); got != tc.want {
				t.Fatalf("got %v want %v", got, tc.want)
			}
		})
	}
}

// fakeService implements listeners.Service minimally for the prober.
type fakeService struct {
	id    string
	hosts map[string]string
	ports []workloadmeta.ContainerPort
}

func (f *fakeService) GetServiceID() string                          { return f.id }
func (f *fakeService) GetADIdentifiers() []string                    { return []string{"krakend"} }
func (f *fakeService) GetHosts() (map[string]string, error)          { return f.hosts, nil }
func (f *fakeService) GetPorts() ([]workloadmeta.ContainerPort, error) {
	return f.ports, nil
}
func (f *fakeService) GetTags() ([]string, error)                    { return nil, nil }
func (f *fakeService) GetTagsWithCardinality(string) ([]string, error) { return nil, nil }
func (f *fakeService) GetPid() (int, error)                          { return 0, nil }
func (f *fakeService) GetHostname() (string, error)                  { return "", nil }
func (f *fakeService) IsReady() bool                                 { return true }
func (f *fakeService) GetCheckNames() []string                       { return nil }
func (f *fakeService) HasFilter(any) bool                            { return false }
func (f *fakeService) GetExtraConfig(string) (string, error)         { return "", nil }
func (f *fakeService) FilterTemplates(map[string]integration.Config) {}
func (f *fakeService) GetImageName() string                          { return "krakend:test" }
func (f *fakeService) Equal(other any) bool                          { return false }

func TestProbe_HintMatchesFirst(t *testing.T) {
	bad := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(404)
	}))
	defer bad.Close()
	good := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "text/plain; version=0.0.4")
		w.Write([]byte("go_goroutines 5\n"))
	}))
	defer good.Close()

	badHost, badPortStr, _ := net.SplitHostPort(bad.Listener.Addr().String())
	goodHost, goodPortStr, _ := net.SplitHostPort(good.Listener.Addr().String())
	badPort, _ := strconv.Atoi(badPortStr)
	goodPort, _ := strconv.Atoi(goodPortStr)
	if badHost != goodHost {
		t.Fatalf("test assumption: both servers on same host (got %s, %s)", badHost, goodHost)
	}

	svc := &fakeService{
		id:    "container_id://abc",
		hosts: map[string]string{"bridge": badHost},
		ports: []workloadmeta.ContainerPort{{Port: badPort}, {Port: goodPort}},
	}
	cfg := &integration.DiscoveryConfig{
		Type:  "openmetrics",
		Ports: []int{goodPort},
		Path:  "/metrics",
	}

	p := NewOpenMetricsProber(WithFailureTTL(time.Second))
	r, ok := p.Probe(context.Background(), cfg, svc)
	if !ok {
		t.Fatal("expected probe success")
	}
	if int(r.Port) != goodPort {
		t.Fatalf("port: got %d want %d", r.Port, goodPort)
	}
}

func TestProbe_AllFailReturnsFalse(t *testing.T) {
	bad := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(404)
	}))
	defer bad.Close()
	host, portStr, _ := net.SplitHostPort(bad.Listener.Addr().String())
	port, _ := strconv.Atoi(portStr)

	svc := &fakeService{
		id:    "container_id://xyz",
		hosts: map[string]string{"bridge": host},
		ports: []workloadmeta.ContainerPort{{Port: port}},
	}
	cfg := &integration.DiscoveryConfig{Type: "openmetrics", Path: "/metrics"}

	p := NewOpenMetricsProber(WithFailureTTL(time.Second))
	if _, ok := p.Probe(context.Background(), cfg, svc); ok {
		t.Fatal("expected probe failure")
	}
}
```

If the `listeners.Service` interface requires more methods than the stub provides, expand the stub to satisfy it. Run `go doc github.com/DataDog/datadog-agent/comp/core/autodiscovery/listeners.Service` to read the full interface.

- [ ] **Step 2: Run the test and confirm it fails.**

Run: `dda inv test --targets=./comp/core/autodiscovery/discovery/ -- -run TestVerifyOpenMetricsResponse`
Expected: FAIL — `undefined: verifyOpenMetricsResponse`.

- [ ] **Step 3: Implement.**

Create `comp/core/autodiscovery/discovery/openmetrics_prober.go`:

```go
// Unless explicitly stated otherwise all files in this repository are licensed
// under the Apache License Version 2.0.
// This product includes software developed at Datadog (https://www.datadoghq.com/).
// Copyright 2016-present Datadog, Inc.

package discovery

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"net"
	"net/http"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/DataDog/datadog-agent/comp/core/autodiscovery/integration"
	"github.com/DataDog/datadog-agent/comp/core/autodiscovery/listeners"
	"github.com/DataDog/datadog-agent/pkg/util/log"
)

const (
	defaultPath        = "/metrics"
	defaultPerProbe    = 500 * time.Millisecond
	defaultBudget      = 2 * time.Second
	defaultMaxAttempts = 8
	defaultFailureTTL  = 30 * time.Second
)

var promLineRe = regexp.MustCompile(`^[a-zA-Z_:][a-zA-Z0-9_:]*(\{[^}]*\})?\s+\S+`)

// OpenMetricsProberOption configures an OpenMetricsProber.
type OpenMetricsProberOption func(*openMetricsProber)

// WithFailureTTL overrides the negative-cache TTL.
func WithFailureTTL(d time.Duration) OpenMetricsProberOption {
	return func(p *openMetricsProber) { p.failureTTL = d }
}

type openMetricsProber struct {
	client      *http.Client
	cache       *probeCache
	perProbe    time.Duration
	totalBudget time.Duration
	maxAttempts int
	failureTTL  time.Duration
}

// NewOpenMetricsProber returns a Prober that verifies OpenMetrics endpoints.
func NewOpenMetricsProber(opts ...OpenMetricsProberOption) Prober {
	p := &openMetricsProber{
		client:      &http.Client{Transport: &http.Transport{DisableKeepAlives: true}},
		cache:       newProbeCache(time.Now),
		perProbe:    defaultPerProbe,
		totalBudget: defaultBudget,
		maxAttempts: defaultMaxAttempts,
		failureTTL:  defaultFailureTTL,
	}
	for _, o := range opts {
		o(p)
	}
	return p
}

func (p *openMetricsProber) Probe(ctx context.Context, cfg *integration.DiscoveryConfig, svc listeners.Service) (ProbeResult, bool) {
	if cfg == nil || cfg.Type != "openmetrics" {
		return ProbeResult{}, false
	}
	host, ok := pickHost(svc)
	if !ok {
		log.Debugf("autodiscovery/discovery: %s has no host, skipping", svc.GetServiceID())
		return ProbeResult{}, false
	}
	exposed, err := svc.GetPorts()
	if err != nil || len(exposed) == 0 {
		return ProbeResult{}, false
	}

	cfgHash := hashDiscoveryConfig(cfg)
	if r, success, hit := p.cache.get(svc.GetServiceID(), cfgHash); hit {
		return r, success
	}

	path := cfg.Path
	if path == "" {
		path = defaultPath
	}
	candidates := candidatePorts(cfg.Ports, exposed)
	deadline := time.Now().Add(p.totalBudget)

	attempts := 0
	for _, port := range candidates {
		if attempts >= p.maxAttempts || time.Now().After(deadline) {
			break
		}
		attempts++
		if p.tryPort(ctx, host, port, path) {
			r := ProbeResult{Port: port}
			p.cache.putSuccess(svc.GetServiceID(), cfgHash, r)
			log.Infof("autodiscovery/discovery: probe matched %s:%d%s for %s", host, port, path, svc.GetServiceID())
			return r, true
		}
	}

	p.cache.putFailure(svc.GetServiceID(), cfgHash, p.failureTTL)
	log.Debugf("autodiscovery/discovery: %d candidate(s) for %s did not match", len(candidates), svc.GetServiceID())
	return ProbeResult{}, false
}

func (p *openMetricsProber) tryPort(ctx context.Context, host string, port uint16, path string) bool {
	url := "http://" + net.JoinHostPort(host, strconv.Itoa(int(port))) + path
	tctx, cancel := context.WithTimeout(ctx, p.perProbe)
	defer cancel()
	req, err := http.NewRequestWithContext(tctx, http.MethodGet, url, nil)
	if err != nil {
		return false
	}
	resp, err := p.client.Do(req)
	if err != nil {
		return false
	}
	defer resp.Body.Close()
	body, err := io.ReadAll(io.LimitReader(resp.Body, 64*1024))
	if err != nil {
		return false
	}
	return verifyOpenMetricsResponse(resp.StatusCode, resp.Header.Get("Content-Type"), body)
}

func verifyOpenMetricsResponse(status int, contentType string, body []byte) bool {
	if status != http.StatusOK {
		return false
	}
	ct := strings.ToLower(contentType)
	if !strings.HasPrefix(ct, "text/plain") && !strings.HasPrefix(ct, "application/openmetrics-text") {
		return false
	}
	for _, line := range strings.Split(string(body), "\n") {
		s := strings.TrimSpace(line)
		if s == "" || strings.HasPrefix(s, "#") {
			continue
		}
		return promLineRe.MatchString(s)
	}
	return false
}

func pickHost(svc listeners.Service) (string, bool) {
	hosts, err := svc.GetHosts()
	if err != nil || len(hosts) == 0 {
		return "", false
	}
	if h, ok := hosts["bridge"]; ok && h != "" {
		return h, true
	}
	for _, h := range hosts {
		if h != "" {
			return h, true
		}
	}
	return "", false
}

func hashDiscoveryConfig(cfg *integration.DiscoveryConfig) string {
	h := sha256.New()
	fmt.Fprintf(h, "%s|%s|", cfg.Type, cfg.Path)
	for _, p := range cfg.Ports {
		fmt.Fprintf(h, "%d,", p)
	}
	return hex.EncodeToString(h.Sum(nil))
}
```

- [ ] **Step 4: Run the tests.**

Run: `dda inv test --targets=./comp/core/autodiscovery/discovery/`
Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add comp/core/autodiscovery/discovery/openmetrics_prober.go comp/core/autodiscovery/discovery/openmetrics_prober_test.go
git commit -m "autodiscovery/discovery: OpenMetrics prober

HTTP-GET each candidate port + path with a 500ms per-probe budget
and a 2s overall budget. Verify Content-Type is text/plain or
application/openmetrics-text and that the body's first non-comment
line is a Prometheus exposition line. Cache success/failure per
(serviceID, config hash).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 9: Service wrapper that injects `discovered_port` via `GetExtraConfig`

A small adapter so `%%discovered_port%%` lookup goes through the existing `GetExtraConfig` path on `listeners.Service`. Keeps the resolver unchanged.

**Files:**
- Create: `comp/core/autodiscovery/discovery/service_wrapper.go`
- Create: `comp/core/autodiscovery/discovery/service_wrapper_test.go`

- [ ] **Step 1: Write the failing test.**

Create `comp/core/autodiscovery/discovery/service_wrapper_test.go`:

```go
// Unless explicitly stated otherwise all files in this repository are licensed
// under the Apache License Version 2.0.
// This product includes software developed at Datadog (https://www.datadoghq.com/).
// Copyright 2016-present Datadog, Inc.

package discovery

import "testing"

func TestServiceWithProbeResult_GetExtraConfig(t *testing.T) {
	base := &fakeService{id: "svc"}
	w := WrapWithProbeResult(base, ProbeResult{Port: 8090})

	v, err := w.GetExtraConfig("discovered_port")
	if err != nil {
		t.Fatalf("error: %v", err)
	}
	if v != "8090" {
		t.Fatalf("got %q want 8090", v)
	}

	if _, err := w.GetExtraConfig("unknown"); err == nil {
		t.Fatal("expected error for unknown extra key")
	}
}
```

- [ ] **Step 2: Run the test and confirm it fails.**

Run: `dda inv test --targets=./comp/core/autodiscovery/discovery/ -- -run TestServiceWithProbeResult`
Expected: FAIL — `undefined: WrapWithProbeResult`.

- [ ] **Step 3: Implement.**

Create `comp/core/autodiscovery/discovery/service_wrapper.go`:

```go
// Unless explicitly stated otherwise all files in this repository are licensed
// under the Apache License Version 2.0.
// This product includes software developed at Datadog (https://www.datadoghq.com/).
// Copyright 2016-present Datadog, Inc.

package discovery

import (
	"strconv"

	"github.com/DataDog/datadog-agent/comp/core/autodiscovery/listeners"
)

// WrapWithProbeResult returns a Service that overlays ProbeResult-derived
// values on the underlying Service via GetExtraConfig. Today only
// "discovered_port" is exposed.
func WrapWithProbeResult(svc listeners.Service, r ProbeResult) listeners.Service {
	return &serviceWithProbeResult{Service: svc, result: r}
}

type serviceWithProbeResult struct {
	listeners.Service
	result ProbeResult
}

func (s *serviceWithProbeResult) GetExtraConfig(key string) (string, error) {
	if key == "discovered_port" {
		return strconv.Itoa(int(s.result.Port)), nil
	}
	return s.Service.GetExtraConfig(key)
}
```

- [ ] **Step 4: Run the test and confirm it passes.**

Run: `dda inv test --targets=./comp/core/autodiscovery/discovery/ -- -run TestServiceWithProbeResult`
Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add comp/core/autodiscovery/discovery/service_wrapper.go comp/core/autodiscovery/discovery/service_wrapper_test.go
git commit -m "autodiscovery/discovery: service wrapper exposing discovered_port

Tiny shim so %%discovered_port%% resolution can flow through the
existing GetExtraConfig path; no resolver signature change required.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 10: Add `%%discovered_port%%` template variable to `tmplvar`

Register the new top-level variable. Behavioural minimum: `%%discovered_port%%` resolves via `GetExtraConfig("discovered_port")`.

**Files:**
- Modify: `pkg/util/tmplvar/resolver.go`
- Modify: `pkg/util/tmplvar/resolver_test.go`

- [ ] **Step 1: Write the failing test.**

Append to `pkg/util/tmplvar/resolver_test.go`:

```go
func TestResolveDiscoveredPort(t *testing.T) {
	res := &mockResolvable{
		extraConfig: map[string]string{
			"discovered_port": "8090",
		},
	}
	r := NewTemplateResolver(YAMLParser, nil, false)
	out, err := r.ResolveDataWithTemplateVars([]byte(`url: "http://example:%%discovered_port%%/metrics"`+"\n"), res)
	if err != nil {
		t.Fatalf("err: %v", err)
	}
	if got, want := strings.TrimSpace(string(out)), `url: http://example:8090/metrics`; got != want {
		t.Fatalf("got %q want %q", got, want)
	}
}

func TestResolveDiscoveredPort_MissingErrors(t *testing.T) {
	res := &mockResolvable{}
	r := NewTemplateResolver(YAMLParser, nil, false)
	_, err := r.ResolveDataWithTemplateVars([]byte(`url: "http://example:%%discovered_port%%/metrics"`+"\n"), res)
	if err == nil {
		t.Fatal("expected error when discovered_port is unavailable")
	}
}
```

If `mockResolvable` does not yet have an `extraConfig` field, augment it. Inspect the existing definition (around line 50) and extend.

- [ ] **Step 2: Run the test and confirm it fails.**

Run: `dda inv test --targets=./pkg/util/tmplvar/ -- -run TestResolveDiscoveredPort`
Expected: FAIL — `discovered` is not a known template variable; substitution error.

- [ ] **Step 3: Implement.**

3a. In `pkg/util/tmplvar/resolver.go`, find `NewTemplateResolver` (line ~95). Inside the `templateVariables` map, add a new entry:

```go
		"discovered": GetDiscoveredPort,
```

3b. After the existing `GetAdditionalTplVariables` function (around line 467–479), add:

```go
// GetDiscoveredPort resolves the %%discovered_port%% template variable. It is
// populated by the autodiscovery/discovery package when a probe matches a
// service. The value flows in via GetExtraConfig on a Service wrapper.
func GetDiscoveredPort(tplVar string, res Resolvable) (string, error) {
	if tplVar != "port" {
		return "", noResolverError(fmt.Sprintf("unsupported %%discovered_%s%% variable; only %%discovered_port%% is recognised", tplVar))
	}
	v, err := res.GetExtraConfig("discovered_port")
	if err != nil || v == "" {
		return "", noResolverError("discovered_port not available — autodiscovery probe did not run or did not match")
	}
	return v, nil
}
```

- [ ] **Step 4: Run the test and confirm it passes.**

Run: `dda inv test --targets=./pkg/util/tmplvar/`
Expected: PASS (the new tests AND the full pre-existing suite).

- [ ] **Step 5: Commit.**

```bash
git add pkg/util/tmplvar/resolver.go pkg/util/tmplvar/resolver_test.go
git commit -m "tmplvar: add %%discovered_port%% template variable

Routes via Resolvable.GetExtraConfig("discovered_port"). Populated by
autodiscovery/discovery's serviceWithProbeResult wrapper after a
successful probe.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 11: Wire the prober into `configmgr` reconcile path

This is the integration step where the prober actually runs.

**Files:**
- Modify: `comp/core/autodiscovery/autodiscoveryimpl/configmgr.go`

- [ ] **Step 1: Read the surrounding code first.**

Open `comp/core/autodiscovery/autodiscoveryimpl/configmgr.go` and read the `resolveTemplateForService` function (around line 409) and where it's called from (search for `resolveTemplateForService(`). Also locate the constructor for `reconcilingConfigManager` (search for `func newReconcilingConfigManager` or `func NewReconciling`). Identify how dependencies (logger, secrets resolver, healthPlatform) are injected — we'll add the Prober alongside.

- [ ] **Step 2: Add a `prober` field on `reconcilingConfigManager`.**

Find the `reconcilingConfigManager` struct definition (likely at the top of `configmgr.go`). Add a field:

```go
	prober discovery.Prober
```

Add the import:

```go
	"github.com/DataDog/datadog-agent/comp/core/autodiscovery/discovery"
```

In the constructor that builds `reconcilingConfigManager`, add a parameter `prober discovery.Prober` and assign `cm.prober = prober`. Update all call sites of the constructor (use `git grep -n "newReconcilingConfigManager\|NewReconcilingConfigManager"` to find them) — pass `discovery.NewOpenMetricsProber()` from the AutoConfig wiring (the agent main composer file in `comp/core/autodiscovery/autodiscoveryimpl/autoconfig.go` is the natural site).

- [ ] **Step 3: Modify `resolveTemplateForService` to run the prober when the template demands it.**

Replace the existing `resolveTemplateForService` body (lines ~409–428) with:

```go
func (cm *reconcilingConfigManager) resolveTemplateForService(tpl integration.Config, svc listeners.Service) (integration.Config, bool) {
	digest := tpl.Digest()
	resolvedSvc := svc

	if tpl.Discovery != nil {
		result, ok := cm.prober.Probe(context.Background(), tpl.Discovery, svc)
		if !ok {
			msg := fmt.Sprintf("discovery probe did not match for template %s and service %s", tpl.Name, svc.GetServiceID())
			log.Debugf("autodiscovery: %s", msg)
			errorStats.setResolveWarning(tpl.Name, msg)
			return tpl, false
		}
		resolvedSvc = discovery.WrapWithProbeResult(svc, result)
	}

	config, err := configresolver.Resolve(tpl, resolvedSvc)
	if err != nil {
		msg := fmt.Sprintf("error resolving template %s for service %s: %v", tpl.Name, svc.GetServiceID(), err)
		log.Errorf("autodiscovery: skipping config - %s", msg)
		errorStats.setResolveWarning(tpl.Name, msg)
		cm.reportTemplateResolutionFailure(tpl, svc, err)
		return tpl, false
	}
	resolvedConfig, err := decryptConfig(config, cm.secretResolver, digest)
	if err != nil {
		msg := fmt.Sprintf("error decrypting secrets in config %s for service %s: %v", config.Name, svc.GetServiceID(), err)
		errorStats.setResolveWarning(tpl.Name, msg)
		return config, false
	}
	errorStats.removeResolveWarnings(tpl.Name)
	cm.clearTemplateResolutionFailure(tpl, svc)
	return resolvedConfig, true
}
```

Add `"context"` to the import block if it isn't already imported.

- [ ] **Step 4: Build and lint.**

Run: `dda inv test --targets=./comp/core/autodiscovery/autodiscoveryimpl/`
Expected: PASS.

Then run the linter:
Run: `dda inv linter.go --targets=./comp/core/autodiscovery/autodiscoveryimpl/ ./comp/core/autodiscovery/discovery/ ./comp/core/autodiscovery/integration/ ./comp/core/autodiscovery/providers/ ./pkg/util/tmplvar/`
Expected: PASS.

- [ ] **Step 5: Commit.**

```bash
git add comp/core/autodiscovery/autodiscoveryimpl/configmgr.go comp/core/autodiscovery/autodiscoveryimpl/autoconfig.go
git commit -m "autodiscovery: run discovery probe before resolving discovery templates

When a Config has Discovery set, run the OpenMetrics prober against
the matched Service before configresolver.Resolve. On match wrap the
service so %%discovered_port%% resolves; on no match skip scheduling
the check (logged at DEBUG).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

## Task 12: Build the agent

Verify the full Agent compiles before we run a docker container.

**Files:** none.

- [ ] **Step 1: Run the full unit test sweep across touched packages.**

Run:
```bash
dda inv test --targets=./comp/core/autodiscovery/integration/ \
                     ./comp/core/autodiscovery/providers/ \
                     ./comp/core/autodiscovery/discovery/ \
                     ./comp/core/autodiscovery/autodiscoveryimpl/ \
                     ./pkg/util/tmplvar/
```
Expected: PASS.

- [ ] **Step 2: Build the agent.**

Run: `dda inv agent.build --build-exclude=systemd`
Expected: agent binary at `bin/agent/agent`.

- [ ] **Step 3: Sanity check the binary.**

Run: `./bin/agent/agent version`
Expected: prints a version string and exits 0.

- [ ] **Step 4: No commit needed.** (The build is verification only.)

---

## Task 13: Demo scenario 1 — default port

End-to-end run with KrakenD on port 8090. Demonstrates the hint-port path.

**Files:** none. Manual test.

- [ ] **Step 1: Start KrakenD via its dev-env compose file.**

Run:
```bash
cd /home/vagrant/go/src/github.com/DataDog/integrations-core/krakend/tests/docker
docker compose up -d
```
Expected: krakend, backend, and any sidecars come up healthy. Verify with `docker compose ps`.

- [ ] **Step 2: Confirm the OpenMetrics endpoint is live.**

Run: `curl -s -o /dev/null -w "%{http_code} %{content_type}\n" http://localhost:8090/metrics`
Expected: `200 text/plain; ...`. If different, abort and investigate.

- [ ] **Step 3: Run the local Agent docker container with the locally built binary + krakend integration source bind-mounted.**

Use the helper script per `integrations-core/reference_docker_integration_testing.md`:

```bash
/home/vagrant/go/src/github.com/DataDog/experimental/users/vincent.whitchurch/hacks/bin/docker-agent-run.sh \
  -v "/home/vagrant/go/src/github.com/DataDog/integrations-core/krakend/datadog_checks/krakend:/opt/datadog-agent/embedded/lib/python3.13/site-packages/datadog_checks/krakend" \
  -v "/home/vagrant/go/src/github.com/DataDog/datadog-agent/bin/agent/agent:/opt/datadog-agent/bin/agent/agent" \
  -d datadog/agent:nightly-main-py3-jmx
```

Expected: container `dd-agent-foo` running. Find the krakend container's IP on the docker network (`docker inspect <krakend_container> | grep IPAddress`) — the agent container needs to be on the same network or the krakend container's published 8090 port must be reachable. If they aren't on the same network, attach the agent: `docker network connect <krakend_network> dd-agent-foo`.

- [ ] **Step 4: Wait ~30s for AD reconciliation, then check the agent status.**

Run: `docker exec dd-agent-foo agent status | sed -n '/krakend (/,/^[A-Z]/p'`
Expected: a `krakend` instance section appears with `Instance ID: krakend:<digest> [OK]`. The `Configuration source` shows the path to `auto_conf_discovery.yaml`. The instance config block contains `openmetrics_endpoint: http://<krakend-ip>:8090/metrics`.

- [ ] **Step 5: Confirm metrics flow.**

Run: `docker logs dd-agent-foo 2>&1 | grep -iE "krakend|discovery: probe matched"`
Expected: at least one line `autodiscovery/discovery: probe matched <ip>:8090/metrics for ...`. Check that the krakend check itself is running (no `[ERROR]` or `[WARNING]` mentions of the check).

- [ ] **Step 6: No commit. Capture observations as a quick note for follow-up.**

---

## Task 14: Demo scenario 2 — non-default port

Re-run with KrakenD listening on port 9000 instead of 8090. Demonstrates fallback scan.

**Files:** none.

- [ ] **Step 1: Stop scenario 1.**

Run:
```bash
cd /home/vagrant/go/src/github.com/DataDog/integrations-core/krakend/tests/docker
docker compose down
docker rm -f dd-agent-foo
```

- [ ] **Step 2: Reconfigure KrakenD to listen on 9000.**

Edit `integrations-core/krakend/tests/docker/krakend.json` (the field is the top-level `port`). Save the change locally — do not commit it. Update the docker-compose port mapping (`ports:`) accordingly: `"9000:9000"` and the EXPOSE in the compose file.

- [ ] **Step 3: Bring KrakenD back up.**

Run: `docker compose up -d` from the same directory.

- [ ] **Step 4: Verify the metrics endpoint is at 9000.**

Run: `curl -s -o /dev/null -w "%{http_code}\n" http://localhost:9000/metrics`
Expected: `200`.

- [ ] **Step 5: Re-run the agent.**

Same `docker-agent-run.sh` invocation as in Task 13 Step 3.

- [ ] **Step 6: Verify the agent discovered port 9000 via the fallback scan.**

Run: `docker exec dd-agent-foo agent status | sed -n '/krakend (/,/^[A-Z]/p'`
Expected: `openmetrics_endpoint: http://<krakend-ip>:9000/metrics`.

Run: `docker logs dd-agent-foo 2>&1 | grep "probe matched"`
Expected: a single line referencing port 9000.

- [ ] **Step 7: Revert the krakend.json + compose changes (do not commit them).**

Run: `git -C /home/vagrant/go/src/github.com/DataDog/integrations-core checkout -- krakend/tests/docker/`
Expected: changes reverted.

---

## Task 15: Demo scenario 3 — negative case

A container that matches the `krakend` ad_identifier but does not serve OpenMetrics. The probe should fail and no check should be scheduled.

**Files:** none.

- [ ] **Step 1: Stop the previous scenario.**

Run:
```bash
docker compose -f /home/vagrant/go/src/github.com/DataDog/integrations-core/krakend/tests/docker/docker-compose.yml down || true
docker rm -f dd-agent-foo || true
```

- [ ] **Step 2: Start a non-KrakenD container labelled with the krakend ad_identifier.**

Run:
```bash
docker run -d --name fake-krakend --label com.datadoghq.ad.check_names='["krakend"]' --label com.datadoghq.ad.init_configs='[{}]' --label com.datadoghq.ad.instances='[{}]' nginx:alpine
```
This labels nginx so AutoDiscovery sees `krakend` as the ad_identifier match (via the labels listener). Nginx serves HTML at `/`, not OpenMetrics — so the probe must fail.

- [ ] **Step 3: Run the agent.**

Same docker-agent-run.sh invocation as in Task 13 Step 3.

- [ ] **Step 4: Verify the negative outcome.**

Run: `docker exec dd-agent-foo agent status | grep -A3 'krakend'`
Expected: NO running krakend instance. (The check should be unconfigured.)

Run: `docker logs dd-agent-foo 2>&1 | grep -iE "discovery probe did not match|did not match|krakend"`
Expected: a DEBUG line `autodiscovery: discovery probe did not match for template krakend and service ...`. No traceback, no error spam.

- [ ] **Step 5: Tear down.**

Run:
```bash
docker rm -f fake-krakend dd-agent-foo
```

- [ ] **Step 6: No commit. Record results in a follow-up note for the user.**

---

## Task 16: Open draft PRs

Two PRs (one per repo). Both as drafts per `datadog-agent/CLAUDE_PERSONAL.md`.

- [ ] **Step 1: Push the integrations-core branch.**

```bash
cd /home/vagrant/go/src/github.com/DataDog/integrations-core
git push -u origin vitkyrka/disco-autoconfig
```

- [ ] **Step 2: Open the integrations-core draft PR.**

```bash
gh pr create --draft --title "krakend: declarative auto_conf_discovery.yaml" --body "$(cat <<'EOF'
## Summary
- Adds `auto_conf_discovery.yaml` to the krakend integration declaring an OpenMetrics probe spec (port 8090, /metrics).
- Pairs with the agent-side change in datadog-agent that consumes this file format.

## Test plan
- [ ] Build the matching agent change in datadog-agent.
- [ ] Bring up krakend dev env (`tests/docker/docker-compose.yml`).
- [ ] Run agent with locally built binary + this integration source bind-mounted; confirm krakend check schedules with `openmetrics_endpoint: http://<host>:8090/metrics`.
- [ ] Repeat with krakend on port 9000; confirm fallback scan finds it.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 3: Push the datadog-agent branch.**

```bash
cd /home/vagrant/go/src/github.com/DataDog/datadog-agent
git push -u origin vitkyrka/advanced-autoconfig-krakend
```

- [ ] **Step 4: Open the datadog-agent draft PR.**

```bash
gh pr create --draft --title "autodiscovery: declarative discovery probes (KrakenD experiment)" --body "$(cat <<'EOF'
## Summary
- New file format `auto_conf_discovery.yaml` parsed by the file config provider.
- New `comp/core/autodiscovery/discovery` package with an OpenMetrics prober (HTTP GET + Prometheus-line verification + 30s negative cache).
- New `%%discovered_port%%` template variable, populated via a Service wrapper after a successful probe.
- AutoDiscovery's reconcile path now runs the prober before resolving any template that has a `discovery:` block; on no-match the check is not scheduled (logged at DEBUG).

Targets the `generic-openmetrics-scan` bucket from the integrations-core analysis (51/260 integrations, 20%).

## Test plan
- [ ] `dda inv test --targets=./comp/core/autodiscovery/...` and `./pkg/util/tmplvar/` pass.
- [ ] `dda inv linter.go` clean on touched packages.
- [ ] End-to-end with the krakend dev env (default port 8090, non-default port 9000, negative case with mislabelled container) — see DSCVR/6650004331.

## Companion PR
- integrations-core: <link to integrations-core PR once created>

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 5: Cross-link the PRs.**

After both URLs exist, edit each PR body and replace the `<link to ... PR>` placeholder. Use `gh pr edit <number> --body "$(cat <<'EOF' ... EOF)"`.

- [ ] **Step 6: Report PR URLs back to the user.**

---

## Self-review notes

- **Spec coverage check:** Architecture (Tasks 3, 4, 11), file format (Task 1), probe semantics (Tasks 6, 7, 8), `%%discovered_port%%` (Task 10), demo (Tasks 13–15). Risks-to-verify section is exercised by Task 13 Step 3 (network attach) and Step 4 (reconciliation timing).
- **Spec deviation:** the spec's "extended `Resolve` signature" is replaced with a `serviceWithProbeResult` wrapper. Strictly cleaner — no API change. Recorded in the file structure section above.
- **One spec item not in a task:** "Cluster-agent / kube_service / kube_endpoints listeners" — explicitly out of scope per the spec's non-goals; intentionally not in any task.
- **Type consistency:** `DiscoveryConfig` is in `comp/core/autodiscovery/integration` and used (not redefined) by `comp/core/autodiscovery/discovery`. `ProbeResult` is `discovery`-package-only. `Prober` is the only interface; the prober tests use it through `NewOpenMetricsProber`.
- **Test discipline:** Tasks 3–10 are TDD (test → fail → implement → pass → commit). Tasks 11–15 are integration/manual.
- **No `go test`:** every test command goes through `dda inv test --targets=...` per `datadog-agent/CLAUDE_PERSONAL.md`.
