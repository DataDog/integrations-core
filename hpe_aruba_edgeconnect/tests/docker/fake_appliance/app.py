#!/usr/bin/env python3
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Fake HPE Aruba EdgeConnect appliance for E2E tests."""

import os
import ssl

from flask import Flask, jsonify, request, send_file

app = Flask(__name__)

DATA_DIR = "/app/data"
CERT_FILE = "/app/certs/cert.pem"
KEY_FILE = "/app/certs/key.pem"

APPLIANCE_USERNAME = os.environ.get("APPLIANCE_USERNAME", "admin")
APPLIANCE_PASSWORD = os.environ.get("APPLIANCE_PASSWORD", "")


@app.route("/rest/json/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    if data.get("user") != APPLIANCE_USERNAME or data.get("password") != APPLIANCE_PASSWORD:
        return jsonify({"status": "unauthorized"}), 401
    return jsonify({"status": "ok"})


@app.route("/rest/json/stats/minuteRange")
def minute_range():
    return jsonify({"newest": 100000060})


@app.route("/rest/json/stats/minuteStats/<filename>")
def minute_stats(filename: str):
    archive = os.path.join(DATA_DIR, filename)
    if not os.path.isfile(archive):
        return jsonify({"error": f"not found: {filename}"}), 404
    return send_file(archive, mimetype="application/gzip")


@app.route("/rest/json/networkInterfaces")
def network_interfaces():
    return jsonify(
        {
            "ifInfo": [
                {"ifName": "wan0", "admin": 1, "oper": 1, "speed": 1000000},
            ]
        }
    )


@app.route("/rest/json/cpustat")
def cpu_stats():
    return jsonify({"cpuPct": 50})


@app.route("/rest/json/memory")
def memory_stats():
    return jsonify({"memPct": 60})


@app.route("/rest/json/diskUsage")
def disk_usage():
    return jsonify({"diskPct": 40})


@app.route("/rest/json/alarm")
def alarms():
    return jsonify({"outstanding": []})


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(CERT_FILE, KEY_FILE)
    app.run(host="0.0.0.0", port=8444, ssl_context=ctx)
