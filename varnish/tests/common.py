# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

# This is a small extract of metrics from varnish. This is meant to test that
# the check gather metrics. This the check return everything from varnish
# without any selection/rename, their is no point in having a complete list.
COMMON_METRICS = [
    "varnish.uptime",              # metrics where the "MAIN" prefix was removed
    "varnish.sess_conn",           # metrics where the "MAIN" prefix was removed
    "varnish.sess_drop",           # metrics where the "MAIN" prefix was removed
    "varnish.sess_fail",           # metrics where the "MAIN" prefix was removed
    "varnish.client_req_400",      # metrics where the "MAIN" prefix was removed
    "varnish.client_req_417",      # metrics where the "MAIN" prefix was removed
    "varnish.client_req",          # metrics where the "MAIN" prefix was removed
    "varnish.cache_hit",           # metrics where the "MAIN" prefix was removed
    "varnish.cache_hitpass",       # metrics where the "MAIN" prefix was removed
    "varnish.cache_miss",          # metrics where the "MAIN" prefix was removed
    "varnish.backend_conn",        # metrics where the "MAIN" prefix was removed
    "varnish.backend_unhealthy",   # metrics where the "MAIN" prefix was removed
    "varnish.backend_busy",        # metrics where the "MAIN" prefix was removed
    "varnish.fetch_eof",           # metrics where the "MAIN" prefix was removed
    "varnish.fetch_bad",           # metrics where the "MAIN" prefix was removed
    "varnish.fetch_none",          # metrics where the "MAIN" prefix was removed
    "varnish.fetch_1xx",           # metrics where the "MAIN" prefix was removed
    "varnish.pools",               # metrics where the "MAIN" prefix was removed
    "varnish.busy_sleep",          # metrics where the "MAIN" prefix was removed
    "varnish.busy_wakeup",         # metrics where the "MAIN" prefix was removed
    "varnish.busy_killed",         # metrics where the "MAIN" prefix was removed
    "varnish.sess_queued",         # metrics where the "MAIN" prefix was removed
    "varnish.sess_dropped",        # metrics where the "MAIN" prefix was removed
    "varnish.n_object",            # metrics where the "MAIN" prefix was removed
    "varnish.n_vampireobject",     # metrics where the "MAIN" prefix was removed
    "varnish.n_vcl",               # metrics where the "MAIN" prefix was removed
    "varnish.n_vcl_avail",         # metrics where the "MAIN" prefix was removed
    "varnish.n_vcl_discard",       # metrics where the "MAIN" prefix was removed
    "varnish.bans",                # metrics where the "MAIN" prefix was removed
    "varnish.bans_completed",      # metrics where the "MAIN" prefix was removed
    "varnish.bans_obj",            # metrics where the "MAIN" prefix was removed
    "varnish.bans_req",            # metrics where the "MAIN" prefix was removed
    "varnish.MGT.child_start",
    "varnish.MGT.child_exit",
    "varnish.MGT.child_stop",
    "varnish.MEMPOOL.busyobj.live",
    "varnish.MEMPOOL.busyobj.pool",
    "varnish.MEMPOOL.busyobj.allocs",
    "varnish.MEMPOOL.busyobj.frees",
    "varnish.SMA.s0.c_req",
    "varnish.SMA.s0.c_fail",
    "varnish.SMA.Transient.c_req",
    "varnish.SMA.Transient.c_fail",
    "varnish.VBE.boot.default.req",
    "varnish.LCK.backend.creat",
    "varnish.LCK.backend_tcp.creat",
    "varnish.LCK.ban.creat",
    "varnish.LCK.ban.locks",
    "varnish.LCK.busyobj.creat",
    "varnish.LCK.mempool.creat",
    "varnish.LCK.vbe.creat",
    "varnish.LCK.vbe.destroy",
    "varnish.LCK.vcl.creat",
    "varnish.LCK.vcl.destroy",
    "varnish.LCK.vcl.locks",
    "varnish.n_purges",
    "varnish.n_purgesps",
]

VARNISH_DEFAULT_VERSION = "4.1.7"
VARNISHADM_PATH = "varnishadm"
SECRETFILE_PATH = "secretfile"
DAEMON_ADDRESS = "localhost:6082"

HERE = os.path.join(os.path.dirname(__file__))
FIXTURE_DIR = os.path.join(HERE, "fixtures")

CHECK_NAME = "varnish"


def get_config_by_version(name=None):
    config = {
        "varnishstat": get_varnish_stat_path(),
        "tags": ["cluster:webs"]
    }

    if name:
        config["name"] = name
    return config


def get_varnish_stat_path():
    varnish_version = os.environ.get("VARNISH_VERSION", VARNISH_DEFAULT_VERSION).split(".")[0]
    return "docker exec ci_varnish{} varnishstat".format(varnish_version)
