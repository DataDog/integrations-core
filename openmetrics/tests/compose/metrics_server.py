#!/usr/bin/env python3
from http.server import HTTPServer, BaseHTTPRequestHandler

histogram_count = 0
histogram_sum = 0.0
request_number = 0
diff_values = [2, 2, 2, -5]
buckets = {
    "1.0": 0,
    "50.0": 0,
    "100.0": 0,
    "200.0": 0,
    "500.0": 0,
    "1000.0": 0,
    "+Inf": 0
}

class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global histogram_count, histogram_sum, buckets, request_number, diff_values
        
        if self.path == '/metrics':
            self.send_response(200)
            self.send_header('Content-Type', 'application/openmetrics-text')
            self.end_headers()

            increment = diff_values[request_number % len(diff_values)]
            request_number += 1
            
            histogram_count += increment
            histogram_sum += increment * 10.0
            
            for le in buckets:
                buckets[le] += increment
            
            bucket_metrics = ""
            for le, count in buckets.items():
                bucket_metrics += f'custom_histogram_bucket{{le="{le}"}} {count}\n'
            
            metrics = f"""# TYPE custom_histogram histogram
# HELP custom_histogram A custom histogram metric
{bucket_metrics}custom_histogram_count {histogram_count}
custom_histogram_sum {histogram_sum}
"""
            self.wfile.write(metrics.encode())
        else:
            self.send_response(404)
            self.end_headers()


if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8080), MetricsHandler)
    print("Metrics server running on http://0.0.0.0:8080/metrics")
    server.serve_forever()
