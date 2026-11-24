// (C) Datadog, Inc. 2026-present
// All rights reserved
// Licensed under a 3-clause BSD style license (see LICENSE)

// Command karpenter_metrics_v1 prints every metric that the Karpenter release pinned in go.mod registers, as a Prometheus
// exposition with the help text and type of each metric.
// The tests in tests/test_metric_coverage.py run the check on that exposition and compare the result with metadata.csv.
//
// It imports the real Karpenter code and builds its controllers offline with every feature gate on.
// Then it creates one series per registered metric, so that the registry exposes the metrics that have no series yet.
//
// It takes no arguments and prints the fixture to stdout, see README.md.
// A maintainer runs it by hand when bumping the supported Karpenter release.
package main

import (
	"bytes"
	"context"
	"fmt"
	"os"
	"reflect"
	"regexp"
	"runtime/debug"
	"slices"
	"strings"
	"unsafe"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/awslabs/operatorpkg/status"
	prometheusv2 "github.com/jonathan-innis/aws-sdk-go-prometheus/v2"
	"github.com/prometheus/client_golang/prometheus"
	dto "github.com/prometheus/client_model/go"
	"github.com/prometheus/common/expfmt"
	"k8s.io/client-go/tools/record"
	"k8s.io/utils/clock"
	crfake "sigs.k8s.io/controller-runtime/pkg/client/fake"
	"sigs.k8s.io/controller-runtime/pkg/manager"
	crmetrics "sigs.k8s.io/controller-runtime/pkg/metrics"
	cpfake "sigs.k8s.io/karpenter/pkg/cloudprovider/fake"
	"sigs.k8s.io/karpenter/pkg/controllers"
	"sigs.k8s.io/karpenter/pkg/controllers/node/health"
	"sigs.k8s.io/karpenter/pkg/controllers/nodeoverlay"
	"sigs.k8s.io/karpenter/pkg/controllers/state"
	"sigs.k8s.io/karpenter/pkg/events"
	"sigs.k8s.io/karpenter/pkg/operator/options"
	"sigs.k8s.io/karpenter/pkg/state/prediction"

	awsv1 "github.com/aws/karpenter-provider-aws/pkg/apis/v1"
	// Importing the provider's controllers registers the metrics it declares at package level.
	_ "github.com/aws/karpenter-provider-aws/pkg/controllers"
	// The operator and the cloud provider decorator register theirs at package level too, but only the Karpenter
	// binary imports them.
	_ "sigs.k8s.io/karpenter/pkg/cloudprovider/metrics"
	_ "sigs.k8s.io/karpenter/pkg/operator"
)

const (
	providerModule    = "github.com/aws/karpenter-provider-aws"
	coreModule        = "sigs.k8s.io/karpenter"
	operatorpkgModule = "github.com/awslabs/operatorpkg"

	// fixtureFile is the file that the output is redirected to. The test reads the same name.
	fixtureFile = "karpenter_metrics_v1.txt"

	// labelValue is the value of every label of the series that the tool creates. The names, types and help text of
	// the metrics do not depend on it.
	labelValue = "x"
)

// exclusion is a group of registered metrics that the fixture leaves out on purpose.
// The fixture header records each group that matched, with its reason, so that a reader can tell an omission from a miss.
type exclusion struct {
	reason   string
	names    []string // exact metric names
	prefixes []string // metric name prefixes
}

func (e exclusion) matches(name string) bool {
	return slices.Contains(e.names, name) ||
		slices.ContainsFunc(e.prefixes, func(prefix string) bool { return strings.HasPrefix(name, prefix) })
}

var exclusions = []exclusion{
	{
		reason: "Go runtime metrics. The collector registers a different set depending on the Go version that " +
			"builds this tool, not on Karpenter.",
		prefixes: []string{"go_"},
	},
	{
		reason: "Deprecated since Karpenter v1.1.0 in favor of the per-kind operator_<kind>_* metrics, and no " +
			"longer emitted from v1.16 (https://github.com/aws/karpenter-provider-aws/pull/9791).",
		names: []string{
			"operator_status_condition_count",
			"operator_status_condition_current_status_seconds",
			"operator_status_condition_transition_seconds",
			"operator_status_condition_transitions_total",
			"operator_termination_current_time_seconds",
			"operator_termination_duration_seconds",
		},
	},
}

// selfPopulating are the prefixes of the metrics of the collectors that create their own series, which the tool can
// therefore leave alone: the Go runtime and the process.
var selfPopulating = []string{"go_", "process_"}

// stubManager only has to hand out an event recorder: that is all NewControllers asks of the manager.
type stubManager struct{ manager.Manager }

func (stubManager) GetEventRecorderFor(string) record.EventRecorder { return &record.FakeRecorder{} }

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

func run() error {
	versions := moduleVersions()

	registerAll()

	registry, ok := crmetrics.Registry.(*prometheus.Registry)
	if !ok {
		return fmt.Errorf("the metrics registry is a %T, expected a *prometheus.Registry", crmetrics.Registry)
	}
	if err := createSeries(registry); err != nil {
		return err
	}
	families, err := registry.Gather()
	if err != nil {
		return err
	}
	kept, excluded := applyExclusions(families)
	zeroValues(kept)

	var out bytes.Buffer
	writeHeader(&out, excluded, versions)
	encoder := expfmt.NewEncoder(&out, expfmt.FmtText)
	for _, family := range kept {
		if err := encoder.Encode(family); err != nil {
			return err
		}
	}

	// Only the fixture goes to stdout, so that it can be redirected to a file. Everything else goes to stderr.
	if _, err := os.Stdout.Write(out.Bytes()); err != nil {
		return err
	}
	fmt.Fprintf(os.Stderr, "listed %d metrics for Karpenter %s\n", len(kept), versions[providerModule])
	return nil
}

// registerAll makes Karpenter register the metrics that are created at runtime rather than at package level.
func registerAll() {
	opts := &options.Options{}
	// Turn every feature gate on: gated controllers register their metrics too.
	for _, gate := range reflect.ValueOf(&opts.FeatureGates).Elem().Fields() {
		if gate.Kind() == reflect.Bool && gate.CanSet() {
			gate.SetBool(true)
		}
	}
	ctx := options.ToContext(context.Background(), opts)

	kubeClient := crfake.NewClientBuilder().Build()
	cloudProvider := cpfake.NewCloudProvider()
	cloudProvider.Reset() // defines the repair policies that node repair requires
	recorder := events.NewRecorder(&record.FakeRecorder{})

	repairPolicyMatcher, err := health.NewRepairPolicyMatcher(ctx, cloudProvider)
	if err != nil {
		panic(err)
	}

	// Core: all controllers, including the per-object status controllers that operatorpkg names after the kind.
	controllers.NewControllers(
		ctx,
		stubManager{},
		clock.RealClock{},
		kubeClient,
		recorder,
		cloudProvider,
		cloudProvider,
		state.NewCluster(clock.RealClock{}, kubeClient, cloudProvider, state.WithRepairPolicyMatcher(repairPolicyMatcher)),
		nodeoverlay.NewInstanceTypeStore(),
		prediction.NewStore(),
	)
	// The provider registers its own per-object status controller and wires the AWS SDK metrics in the operator.
	status.NewController[*awsv1.EC2NodeClass](kubeClient, &record.FakeRecorder{})
	prometheusv2.WithPrometheusMetrics(aws.Config{}, crmetrics.Registry)
}

var (
	fqName         = regexp.MustCompile(`fqName: "([^"]+)"`)
	variableLabels = regexp.MustCompile(`variableLabels: \{([^}]*)\}`)
)

// registeredCollectors returns the collectors of a registry.
// The registry does not expose them, and a collector is the only place that tells the type of a metric.
func registeredCollectors(registry *prometheus.Registry) ([]prometheus.Collector, error) {
	field := reflect.ValueOf(registry).Elem().FieldByName("collectorsByID")
	if !field.IsValid() || field.Kind() != reflect.Map {
		return nil, fmt.Errorf("the registry has no collectorsByID map, this tool does not support this client_golang version")
	}
	// The field is unexported, so reading it takes the address of the field.
	field = reflect.NewAt(field.Type(), unsafe.Pointer(field.UnsafeAddr())).Elem()

	var collectors []prometheus.Collector
	for _, value := range field.Seq2() {
		collector, ok := value.Interface().(prometheus.Collector)
		if !ok {
			return nil, fmt.Errorf("unexpected %s in the registry", value.Type())
		}
		collectors = append(collectors, collector)
	}
	return collectors, nil
}

// createSeries gives every registered metric one series, so that Gather returns it.
// A metric with labels has no series until something uses it, and the registry only returns metrics with a series.
func createSeries(registry *prometheus.Registry) error {
	collectors, err := registeredCollectors(registry)
	if err != nil {
		return err
	}
	for _, collector := range collectors {
		descs := make(chan *prometheus.Desc)
		go func() {
			collector.Describe(descs)
			close(descs)
		}()
		var names []string
		var labels []string
		for desc := range descs {
			names = append(names, fqName.FindStringSubmatch(desc.String())[1])
			if m := variableLabels.FindStringSubmatch(desc.String()); m != nil && m[1] != "" {
				labels = strings.Split(m[1], ",")
			}
		}
		values := slices.Repeat([]string{labelValue}, len(labels))

		switch c := collector.(type) {
		case *prometheus.CounterVec:
			c.WithLabelValues(values...)
		case *prometheus.GaugeVec:
			c.WithLabelValues(values...)
		case *prometheus.HistogramVec:
			c.WithLabelValues(values...)
		case *prometheus.SummaryVec:
			c.WithLabelValues(values...)
		case prometheus.Counter, prometheus.Gauge, prometheus.Histogram, prometheus.Summary:
			// A metric without labels has a series from the start.
		default:
			// Fail rather than leave a metric out of the fixture without saying so.
			for _, name := range names {
				if !hasAnyPrefix(name, selfPopulating) {
					return fmt.Errorf("cannot create a series for %T, which registers %v", collector, names)
				}
			}
		}
	}
	return nil
}

func hasAnyPrefix(name string, prefixes []string) bool {
	return slices.ContainsFunc(prefixes, func(prefix string) bool { return strings.HasPrefix(name, prefix) })
}

// applyExclusions splits the families into those the fixture lists and, per exclusion, the names of those it leaves out.
// A family goes to the first exclusion that matches it.
func applyExclusions(families []*dto.MetricFamily) (kept []*dto.MetricFamily, excluded [][]string) {
	excluded = make([][]string, len(exclusions))
	for _, family := range families {
		name := family.GetName()
		i := slices.IndexFunc(exclusions, func(e exclusion) bool { return e.matches(name) })
		if i < 0 {
			kept = append(kept, family)
			continue
		}
		excluded[i] = append(excluded[i], name)
	}
	return kept, excluded
}

// zeroValues sets every value to 0, so that the output does not change from run to run.
// The process collector reports values that do.
func zeroValues(families []*dto.MetricFamily) {
	for _, family := range families {
		for _, metric := range family.Metric {
			switch {
			case metric.Counter != nil:
				metric.Counter.Value = new(0.0)
				metric.Counter.Exemplar = nil
			case metric.Gauge != nil:
				metric.Gauge.Value = new(0.0)
			case metric.Untyped != nil:
				metric.Untyped.Value = new(0.0)
			case metric.Histogram != nil:
				metric.Histogram.SampleCount = new(uint64(0))
				metric.Histogram.SampleSum = new(0.0)
				for _, bucket := range metric.Histogram.Bucket {
					bucket.CumulativeCount = new(uint64(0))
					bucket.Exemplar = nil
				}
			case metric.Summary != nil:
				metric.Summary.SampleCount = new(uint64(0))
				metric.Summary.SampleSum = new(0.0)
				for _, quantile := range metric.Summary.Quantile {
					quantile.Value = new(0.0)
				}
			}
		}
	}
}

// writeHeader writes the comments at the top of the fixture. The exposition format ignores them.
func writeHeader(b *bytes.Buffer, excluded [][]string, versions map[string]string) {
	fmt.Fprintf(b, "# Metrics registered by Karpenter, as a Prometheus exposition. GENERATED, do not edit.\n")
	fmt.Fprintf(b, "#\n# Regenerate with: cd karpenter/scripts/karpenter_metrics_v1 && go run . > ../../tests/fixtures/%s\n", fixtureFile)
	fmt.Fprintf(b, "# Built from %s %s with %s %s and %s %s.\n",
		providerModule, versions[providerModule], coreModule, versions[coreModule], operatorpkgModule, versions[operatorpkgModule])
	fmt.Fprintf(b, "#\n# Every metric has one series with the label value %q and the value 0.\n", labelValue)
	fmt.Fprintf(b, "# The tests run the check on this file and compare the metrics it submits with metadata.csv.\n")
	for i, e := range exclusions {
		if len(excluded[i]) == 0 {
			continue
		}
		fmt.Fprintf(b, "#\n# Left out on purpose (%d): %s\n", len(excluded[i]), e.reason)
		if len(e.names) > 0 {
			fmt.Fprintf(b, "#   %s\n", strings.Join(excluded[i], ", "))
		}
	}
	fmt.Fprintln(b)
}

func moduleVersions() map[string]string {
	versions := map[string]string{}
	info, ok := debug.ReadBuildInfo()
	if !ok {
		return versions
	}
	for _, dep := range info.Deps {
		versions[dep.Path] = dep.Version
	}
	return versions
}
