#!/usr/bin/env python3
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Fake HPE Aruba EdgeConnect appliance for E2E tests."""

import os
import ssl
import time

from flask import Flask, jsonify, request, send_file

app = Flask(__name__)

MINUTE_STATS_INTERVAL = 60
_BASE_TIMESTAMP = 100000060

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
    elapsed = int(time.time() - app.config["start_time"])
    newest = _BASE_TIMESTAMP + (elapsed // MINUTE_STATS_INTERVAL) * MINUTE_STATS_INTERVAL
    return jsonify({"newest": newest})


@app.route("/rest/json/stats/minuteStats/<filename>")
def minute_stats(filename: str):
    archive = os.path.join(DATA_DIR, filename)
    if not os.path.isfile(archive):
        # Serve the canonical fixture for any timestamp the check requests
        archive = os.path.join(DATA_DIR, f"st2-{_BASE_TIMESTAMP}.tgz")
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
    timestamp = _BASE_TIMESTAMP * 1000
    return jsonify(
        {
            "latestTimestamp": timestamp,
            "data": [
                {
                    str(timestamp): [
                        {
                            "cpu_number": "ALL",
                            "pIdle": "50.00",
                            "pUser": "30.00",
                            "pSys": "15.00",
                            "pIRQ": "3.00",
                            "pNice": "2.00",
                        },
                    ],
                },
            ],
        }
    )


@app.route("/rest/json/memory")
def memory_stats():
    return jsonify(
        {
            "total": 3945080,
            "free": 770848,
            "buffers": 2516,
            "cached": 729568,
            "used": 3174232,
        }
    )


@app.route("/rest/json/diskUsage")
def disk_usage():
    return jsonify(
        {
            "/dev": {"1k-blocks": 1965848, "used": 0, "available": 1965848, "usedpercent": 0, "filesystem": "none"},
            "/": {
                "1k-blocks": 6126976,
                "used": 1193348,
                "available": 4619060,
                "usedpercent": 21,
                "filesystem": "/dev/disk/by-label/ROOT_1",
            },
            "/var": {
                "1k-blocks": 42030588,
                "used": 4328968,
                "available": 35553256,
                "usedpercent": 11,
                "filesystem": "/root/dev/disk/by-label/VAR",
            },
            "/boot": {
                "1k-blocks": 999288,
                "used": 31676,
                "available": 915188,
                "usedpercent": 4,
                "filesystem": "/dev/sda5",
            },
            "/bootmgr": {
                "1k-blocks": 999320,
                "used": 3268,
                "available": 943624,
                "usedpercent": 1,
                "filesystem": "/dev/sda1",
            },
            "/config": {
                "1k-blocks": 1015700,
                "used": 1632,
                "available": 961640,
                "usedpercent": 1,
                "filesystem": "/dev/sda3",
            },
            "/run": {"1k-blocks": 1972540, "used": 4776, "available": 1967764, "usedpercent": 1, "filesystem": "tmpfs"},
            "/var/volatile": {
                "1k-blocks": 1972540,
                "used": 2384,
                "available": 1970156,
                "usedpercent": 1,
                "filesystem": "tmpfs",
            },
        }
    )


@app.route("/rest/json/alarm")
def alarms():
    return jsonify({"outstanding": []})


@app.route("/rest/json/systemInfo")
def system_info():
    return jsonify(
        {
            "hostName": "FakeAppliance01",
            "applianceid": 1,
            "model": "EC-V 209005002001 Rev 102786",
            "modelShort": "EC-V",
            "platform": "VMware",
            "status": "Normal",
            "uptime": 86400000,
            "uptimeString": "1d 0h 0m 0s",
            "release": "ECOS 9.5.2.1_102786",
            "releaseWithoutPrefix": "9.5.2.1_102786",
            "serial": "00-00-00-02-F4-6D",
            "uuid": "3dbcbf55-33e0-418f-b98c-3626f98cb0da",
            "deploymentMode": "router",
            "biosVersion": "6.00",
            "alarmSummary": {
                "num_cleared": 0,
                "num_critical": 0,
                "num_major": 0,
                "num_minor": 0,
                "num_outstanding": 0,
                "num_warning": 0,
            },
        }
    )


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.config["start_time"] = time.time()
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(CERT_FILE, KEY_FILE)
    app.run(host="0.0.0.0", port=8444, ssl_context=ctx)
