package main

import (
	"encoding/csv"
	"fmt"
	"io"
	"os"
	"regexp"
	"slices"
	"strings"

	"github.com/mdigger/htmlx"
)

// Metric represents a CockroachDB metric.
type Metric struct {
	// The metric name.
	Name string

	// Details about the metric.
	Description string

	// Metric type (e.g., gauge, counter).
	Type string

	// Metric unit (e.g., timestamp, milliseconds).
	Unit string
}

var (
	prometheusMetricNameRegex  = regexp.MustCompile("[^a-zA-Z0-9_]")
	cockroachdbMetricNameRegex = regexp.MustCompile("[^a-zA-Z0-9_\\.]")
)

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintln(os.Stderr, "invalid number of arguments")
		usage()
		os.Exit(1)
	}

	if err := run(); err != nil {
		fmt.Fprintf(os.Stderr, "%v\n", err)
		os.Exit(1)
	}
}

func usage() {
	text := `
Usage: %s METRICS [METADATA] [METRIC_MAP]

A program to generate the metadata.csv and metric name mapping required by the
cockroachdb Datadog integration.

https://github.com/DataDog/integrations-core/blob/master/cockroachdb/metadata.csv
https://github.com/DataDog/integrations-core/blob/master/cockroachdb/datadog_checks/cockroachdb/metrics.py


    METRICS         CockroachDB metrics.html file from
                    https://github.com/cockroachdb/cockroach/blob/master/docs/generated/metrics/metrics.html

    METADATA        Name of the file to write the metadata.csv content

    METRIC_MAP      Name of the file to write the metric name mapping content
`

	text = strings.TrimSpace(text)
	fmt.Printf(text, os.Args[0])
}

func run() error {
	f, err := os.Open(os.Args[1])
	if err != nil {
		return fmt.Errorf("failed opening input file: %w", err)
	}
	defer f.Close()

	metrics, err := parseMetrics(f)
	if err != nil {
		return fmt.Errorf("failed parsing metrics: %w", err)
	}

	metrics = addAdditionalMetrics(metrics)

	if duplicates, ok := containsDuplicates(metrics); ok {
		return fmt.Errorf("found duplicate metrics:\n%s", strings.Join(duplicates, "\n"))
	}

	// Sort the metrics by metric name.
	slices.SortFunc(metrics, func(a, b Metric) int {
		if a.Name < b.Name {
			return -1
		}

		if a.Name > b.Name {
			return 1
		}

		return 0
	})

	metadataFileName := "metadata.csv"
	if len(os.Args) > 2 {
		metadataFileName = os.Args[2]
	}
	metadataFile, err := os.Create(metadataFileName)
	if err != nil {
		return fmt.Errorf("failed creating metadata file: %w", err)
	}
	if err := writeMetadata(metadataFile, metrics); err != nil {
		return fmt.Errorf("failed writing metadata: %w", err)
	}

	mappingFileName := "mapping.txt"
	if len(os.Args) > 3 {
		mappingFileName = os.Args[3]
	}
	mappingFile, err := os.Create(mappingFileName)
	if err != nil {
		return fmt.Errorf("failed creating mapping file: %w", err)
	}
	if err := writeMapping(mappingFile, metrics); err != nil {
		return fmt.Errorf("failed writing mapping: %w", err)
	}

	return nil
}

// parseMetrics parses and traverses the metrics.html to build a slice of all
// metrics within that HTML file.
func parseMetrics(r io.Reader) ([]Metric, error) {
	node, err := htmlx.Parse(r)
	if err != nil {
		return nil, fmt.Errorf("failed parsing html: %w", err)
	}

	metrics := make([]Metric, 0)

	// Metrics are located in tr HTML elements.
	for _, tr := range node.FindAll(htmlx.TagName("tr")) {
		tdNodes := tr.FindAll(htmlx.TagName("td"))

		// This tr has no td HTML elements.
		if len(tdNodes) == 0 {
			continue
		}

		// The parser expects exactly 8 td HTML elements. Otherwise the format
		// of the HTML has changed and this parser would be incorrect.
		if len(tdNodes) > 0 && len(tdNodes) != 8 {
			return nil, fmt.Errorf("invalid record: unexpected number of td elements (%d): %s", len(tdNodes), tr.String())
		}

		m := Metric{
			Name:        tdNodes[1].Text(),
			Description: tdNodes[2].Text(),
			Type:        tdNodes[4].Text(),
			Unit:        tdNodes[5].Text(),
		}

		metrics = append(metrics, m)

	}

	return metrics, nil
}

// addAdditionalMetrics adds metrics to the metrics slice that are not
// otherwise included in the provided metrics.html file. For example,
// metrics.html is generated from CockroachDB running in insecure mode, so
// `security.certificate.*` metrics are not included. This function gives us a
// capability to add them.
func addAdditionalMetrics(metrics []Metric) []Metric {
	return append(metrics, []Metric{
		{
			Name:        "admission.admitted.kv.bulk_normal_pri",
			Description: "Number of requests admitted",
			Type:        "COUNTER",
			Unit:        "COUNT",
		},
		{
			Name:        "admission.errored.kv.bulk_normal_pri",
			Description: "Number of requests admitted",
			Type:        "COUNTER",
			Unit:        "COUNT",
		},
		{
			Name:        "admission.requested.kv.bulk_normal_pri",
			Description: "Number of requests admitted",
			Type:        "COUNTER",
			Unit:        "COUNT",
		},
		{
			Name:        "admission.wait_durations.kv.bulk_normal_pri",
			Description: "Number of requests admitted",
			Type:        "COUNTER",
			Unit:        "COUNT",
		},
		{
			Name:        "admission.wait_queue_length.kv.bulk_normal_pri",
			Description: "Number of requests admitted",
			Type:        "COUNTER",
			Unit:        "COUNT",
		},
		{
			Name:        "seconds_until_enterprise_license_expiry",
			Description: "Seconds until enterprise license expiry (0 if no license present or running without enterprise features)",
			Type:        "GAUGE",
			Unit:        "SECONDS",
		},
		{
			Name:        "security.certificate.expiration.ca",
			Description: "Expiration for the CA certificate. 0 means no certificate or error.",
			Type:        "GAUGE",
			Unit:        "TIMESTAMP",
		},
		{
			Name:        "security.certificate.expiration.ca-client-tenant",
			Description: "Expiration for the Tenant Client CA certificate. 0 means no certificate or error.",
			Type:        "GAUGE",
			Unit:        "TIMESTAMP",
		},
		{
			Name:        "security.certificate.expiration.client",
			Description: "Minimum expiration for client certificates, labeled by SQL user. 0 means no certificate or error.",
			Type:        "GAUGE",
			Unit:        "TIMESTAMP",
		},
		{
			Name:        "security.certificate.expiration.client-ca",
			Description: "Expiration for the client CA certificate. 0 means no certificate or error.",
			Type:        "GAUGE",
			Unit:        "TIMESTAMP",
		},
		{
			Name:        "security.certificate.expiration.client-tenant",
			Description: "Expiration for the Tenant Client certificate. 0 means no certificate or error.",
			Type:        "GAUGE",
			Unit:        "TIMESTAMP",
		},
		{
			Name:        "security.certificate.expiration.node",
			Description: "Expiration for the node certificate. 0 means no certificate or error.",
			Type:        "GAUGE",
			Unit:        "TIMESTAMP",
		},
		{
			Name:        "security.certificate.expiration.node-client",
			Description: "Expiration for the node's client certificate. 0 means no certificate or error.",
			Type:        "GAUGE",
			Unit:        "TIMESTAMP",
		},
		{
			Name:        "security.certificate.expiration.ui",
			Description: "Expiration for the UI certificate. 0 means no certificate or error.",
			Type:        "GAUGE",
			Unit:        "TIMESTAMP",
		},
		{
			Name:        "security.certificate.expiration.ui-ca",
			Description: "Expiration for the UI CA certificate. 0 means no certificate or error.",
			Type:        "GAUGE",
			Unit:        "TIMESTAMP",
		},
	}...,
	)
}

// containsDuplicates checks if there are duplicate metrics in the dataset.
func containsDuplicates(metrics []Metric) ([]string, bool) {
	metricsSet := make(map[string]struct{})
	duplicatesSet := make(map[string]struct{}, 0)

	for _, metric := range metrics {
		if _, ok := metricsSet[metric.Name]; ok {
			duplicatesSet[metric.Name] = struct{}{}
		}
		metricsSet[metric.Name] = struct{}{}
	}

	duplicates := make([]string, 0, len(duplicatesSet))
	for key := range duplicatesSet {
		duplicates = append(duplicates, key)
	}

	if len(duplicates) > 0 {
		return duplicates, true
	}

	return nil, false
}

// writeMetadata writes the metadata.csv content as required by
// https://github.com/DataDog/integrations-core/blob/master/cockroachdb/metadata.csv.
func writeMetadata(w io.Writer, metrics []Metric) error {
	cWriter := csv.NewWriter(w)
	cWriter.Write([]string{
		"metric_name",
		"metric_type",
		"interval",
		"unit_name",
		"per_unit_name",
		"description",
		"orientation",
		"integration",
		"short_name",
		"curated_metric",
	})

	for _, metric := range metrics {
		err := cWriter.Write([]string{
			fmt.Sprintf("cockroachdb.%s", cockroachdbMetricName(metric.Name)),
			strings.ToLower(metric.Type),
			"",
			strings.ToLower(metric.Unit),
			"",
			metric.Description,
			"0",
			"cockroachdb",
			"",
			"",
		})
		if err != nil {
			return err
		}

		// Add the `.bucket`, `.count`, and `.sum` metrics for histograms as
		// required by Datadog. We do this on write since we want these to be
		// grouped with their respective metric irrespective of sort order.
		if strings.ToLower(metric.Type) == "histogram" {
			for _, suffix := range []string{"bucket", "count", "sum"} {
				err := cWriter.Write([]string{
					fmt.Sprintf("cockroachdb.%s", cockroachdbMetricName(strings.Join([]string{metric.Name, suffix}, "."))),
					strings.ToLower(metric.Type),
					"",
					strings.ToLower(metric.Unit),
					"",
					metric.Description,
					"0",
					"cockroachdb",
					"",
					"",
				})
				if err != nil {
					return err
				}
			}
		}
	}

	cWriter.Flush()

	return cWriter.Error()
}

// writeMapping writes the METRIC_MAP as required by
// https://github.com/DataDog/integrations-core/blob/master/cockroachdb/datadog_checks/cockroachdb/metrics.py.
func writeMapping(w io.Writer, metrics []Metric) error {
	if _, err := fmt.Fprintln(w, "METRIC_MAP = {"); err != nil {
		return err
	}

	for _, metric := range metrics {
		if _, err := fmt.Fprintf(w, "    '%s': '%s',\n",
			prometheusMetricName(metric.Name),
			cockroachdbMetricName(metric.Name),
		); err != nil {
			return err
		}

		// Add the `.bucket`, `.count`, and `.sum` metrics for histograms as
		// required by Datadog. We do this on write since we want these to be
		// grouped with their respective metric irrespective of sort order.
		if strings.ToLower(metric.Type) == "histogram" {
			for _, suffix := range []string{"bucket", "count", "sum"} {
				if _, err := fmt.Fprintf(w, "    '%s': '%s',\n",
					prometheusMetricName(strings.Join([]string{metric.Name, suffix}, ".")),
					cockroachdbMetricName(strings.Join([]string{metric.Name, suffix}, ".")),
				); err != nil {
					return err
				}
			}
		}
	}

	if _, err := fmt.Fprintf(w, "}"); err != nil {
		return err
	}

	return nil
}

// cockroachdbMetricName returns an updated metric name that's compatible with
// CockroachDB.
func cockroachdbMetricName(s string) string {
	return cockroachdbMetricNameRegex.ReplaceAllString(s, "_")
}

// prometheusMetricName returns an updated metric name that's compatible with
// Prometheus.
func prometheusMetricName(s string) string {
	return prometheusMetricNameRegex.ReplaceAllString(s, "_")
}
