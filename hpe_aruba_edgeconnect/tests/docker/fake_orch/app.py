#!/usr/bin/env python3
# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Fake HPE Aruba EdgeConnect orchestrator for E2E tests."""

import os
import ssl

from flask import Flask, jsonify, request

app = Flask(__name__)

CERT_FILE = "/app/certs/cert.pem"
KEY_FILE = "/app/certs/key.pem"

ORCH_USERNAME = os.environ.get("ORCH_USERNAME", "admin")
ORCH_PASSWORD = os.environ.get("ORCH_PASSWORD", "")

APPLIANCE_IP = os.environ.get("APPLIANCE_IP", "172.16.3.21")
PEER_NEWYORK_IP = "10.0.0.2"
PEER_SANFRAN_IP = "10.0.0.3"


def _appliance(ip, ne_pk, host_name, site, startup_time=None):
    return {
        "id": ne_pk,
        "uuid": "19dde6b0-e971-4cbe-8714-c42c29657a2a",
        "networkRole": "0",
        "site": site,
        "sitePriority": 0,
        "userName": "admin",
        "password": None,
        "groupId": "2.Network",
        "IP": ip,
        "webProtocolType": 3,
        "serial": "SN001",
        "hasUnsavedChanges": False,
        "rebootRequired": False,
        "model": "EC-V",
        "hardwareRevision": "209005002001 Rev 102786",
        "hostName": host_name,
        "applianceId": 182356,
        "platform": "VMware",
        "mode": "router",
        "bypass": False,
        "softwareVersion": "9.3.1",
        "startupTime": startup_time,
        "webProtocol": "BOTH",
        "systemBandwidth": 300000,
        "state": 1,
        "dynamicUuid": "2f938d31-8eb6-428d-9a16-208aec647d3d",
        "portalObjectId": "69811624fb692e7082aff5ca",
        "discoveredFrom": 2,
        "reachabilityChannel": 2,
        "preconfigStatus": None,
        "suricataVersion": "6.0.10",
        "signatureFamily": "5.x",
        "ip": ip,
        "nePk": ne_pk,
    }


APPLIANCE_LIST = [
    _appliance(APPLIANCE_IP, "1.NE", "SydneySP01", "SYD", startup_time=86400),
    _appliance(PEER_NEWYORK_IP, "4.NE", "NewYorkSP01", "NYC"),
    _appliance(PEER_SANFRAN_IP, "5.NE", "SanFranSP02", "SFO"),
]


@app.route("/gms/rest/authentication/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    if data.get("user") != ORCH_USERNAME or data.get("password") != ORCH_PASSWORD:
        return jsonify({"status": "unauthorized"}), 401
    return jsonify({"status": "ok"})


@app.route("/gms/rest/appliance")
def appliances():
    return jsonify(APPLIANCE_LIST)


@app.route("/gms/rest/gms/overlays/config")
def overlay_config():
    return jsonify([{"id": 0, "name": "business"}])


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(CERT_FILE, KEY_FILE)
    app.run(host="0.0.0.0", port=8443, ssl_context=ctx)
