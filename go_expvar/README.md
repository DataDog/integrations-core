# Go_expvar Integration

## Overview

Get metrics from go_expvar service in real time to:

* Visualize and monitor go_expvar states
* Be notified about go_expvar failovers and events.

## Installation

Install the `dd-check-go_expvar` package manually or with your favorite configuration manager

## Configuration

Edit the `go_expvar.yaml` file to point to your server and port, set the masters to monitor

Use Go's expvar package to expose your memory information
package ...

```
import (
    ...
    "net/http"
    "expvar"
    ...
)

// If your application has no http server running for the DefaultServeMux,
// you'll have to have a http server running for expvar to use, for example
// by adding the following to your init function
func init() {
    go http.ServeAndListen(":8080", nil)
}

...

// You can also expose variables that are specific to your application
// See http://golang.org/pkg/expvar/ for more information

var (
    exp_points_processed = expvar.NewInt("points_processed")
)

func processPoints(p RawPoints) {
    points_processed, err := parsePoints(p)
    exp_points_processed.Add(points_processed)
    ...
}

...
```

Configure the Agent to connect to your application's expvar and specify the metrics you want to collect
Edit conf.d/go_expvar.yaml

```
init_config:
instances:
   -   expvar_url: http://localhost:8080/debug/vars
       tags:
           - optionaltag1
           - optionaltag2
       metrics:
           - path: memstats/PauseTotalNs
             alias: go_expvar.gc.pause_time_in_ns
             type: rate                  # default is a gauge
           - path: memstats/Alloc        # will be reported as go_expvar.memstats.alloc
           - path: points_processed
             type: rate
```

## Validation

When you run `datadog-agent info` you should see something like the following:

    Checks
    ======

        go_expvar
        -----------
          - instance #0 [OK]
          - Collected 39 metrics, 0 events & 7 service checks

## Compatibility

The go_expvar check is compatible with all major platforms
