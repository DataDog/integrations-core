# Agent Check: Varnish

# Overview

This check collects varnish metrics regarding:

* Clients: connections and requests
* Cache performance: hits, evictions, etc
* Threads: creation, failures, threads queued
* Backends: successful, failed, retried connections

It also submits service checks for the health of each backend.

# Installation

The varnish check is packaged with the Agent, so simply [install the Agent](https://app.datadoghq.com/account/settings#agent) on your varnish servers. If you need the newest version of the check, install the `dd-check-varnish` package.

# Configuration

If you're running Varnish 4.1+, add the dd-agent system user to the varnish group (e.g. `sudo usermod -G varnish -a dd-agent`).

Then, create a file `varnish.yaml` in the Agent's `conf.d` directory:

```
init_config:

instances:
  - varnishstat: /usr/bin/varnishstat
    varnishadm: <PATH_TO_VARNISHADM_BIN>     # to submit service checks for the health of each backend
#   secretfile: <PATH_TO_VARNISH_SECRETFILE> # if you configured varnishadm and your secret file isn't /etc/varnish/secret
#   tags:
#     - instance:production
```

If you don't set `varnishadm`, the Agent won't check backend health. If you do set it, the Agent needs privileges to execute the binary with root privileges. Add the following to your `/etc/sudoers` file:

```
dd-agent ALL=(ALL) NOPASSWD:/usr/bin/varnishadm
```

Restart the Agent to start sending varnish metrics and service checks to Datadog.

# Validation

Run the Agent's `info` subcommand and look for `varnish` under the Checks section:

```
  Checks
  ======
    [...]

    varnish
    -------
      - instance #0 [OK]
      - Collected 26 metrics, 0 events & 1 service check

    [...]
```
# Compatibility

The Varnish check is compatible with all major platforms.

# Service Checks

**varnish.backend_healthy**:

The Agent submits this service check if you configure `varnishadm`. It submits a service check for each varnish backend, tagging each with `backend:<backend_name>`.

# Further Reading

See our [series of blog posts](https://www.datadoghq.com/blog/top-varnish-performance-metrics/) about monitoring varnish with Datadog.

# Metrics

See [metadata.csv](https://github.com/DataDog/integrations-core/blob/master/varnish/metadata.csv) for a list of metrics provided by this check.

The check submits different metrics depending on the major version of varnish:

### Varnish 3.x

varnish.accept_fail
varnish.backend_busy
varnish.backend_conn
varnish.backend_fail
varnish.backend_recycle
varnish.backend_req
varnish.backend_retry
varnish.backend_reuse
varnish.backend_toolate
varnish.backend_unhealthy
varnish.backend_unused
varnish.cache_hit
varnish.cache_hitpass
varnish.cache_miss
varnish.client_conn
varnish.client_drop
varnish.client_drop_late
varnish.client_req
varnish.dir_dns_cache_full
varnish.dir_dns_failed
varnish.dir_dns_hit
varnish.dir_dns_lookups
varnish.esi_errors
varnish.esi_parse
varnish.esi_warnings
varnish.fetch_1xx
varnish.fetch_204
varnish.fetch_304
varnish.fetch_bad
varnish.fetch_chunked
varnish.fetch_close
varnish.fetch_eof
varnish.fetch_failed
varnish.fetch_head
varnish.fetch_length
varnish.fetch_oldhttp
varnish.fetch_zero
varnish.hcb_insert
varnish.hcb_lock
varnish.hcb_nolock
varnish.LCK.backend.colls
varnish.LCK.backend.creat
varnish.LCK.backend.destroy
varnish.LCK.backend.locks
varnish.LCK.ban.colls
varnish.LCK.ban.creat
varnish.LCK.ban.destroy
varnish.LCK.ban.locks
varnish.LCK.cli.colls
varnish.LCK.cli.creat
varnish.LCK.cli.destroy
varnish.LCK.cli.locks
varnish.LCK.exp.colls
varnish.LCK.exp.creat
varnish.LCK.exp.destroy
varnish.LCK.exp.locks
varnish.LCK.hcb.colls
varnish.LCK.hcb.creat
varnish.LCK.hcb.destroy
varnish.LCK.hcb.locks
varnish.LCK.hcl.colls
varnish.LCK.hcl.creat
varnish.LCK.hcl.destroy
varnish.LCK.hcl.locks
varnish.LCK.herder.colls
varnish.LCK.herder.creat
varnish.LCK.herder.destroy
varnish.LCK.herder.locks
varnish.LCK.hsl.colls
varnish.LCK.hsl.creat
varnish.LCK.hsl.destroy
varnish.LCK.hsl.locks
varnish.LCK.lru.colls
varnish.LCK.lru.creat
varnish.LCK.lru.destroy
varnish.LCK.lru.locks
varnish.LCK.objhdr.colls
varnish.LCK.objhdr.creat
varnish.LCK.objhdr.destroy
varnish.LCK.objhdr.locks
varnish.LCK.sessmem.colls
varnish.LCK.sessmem.creat
varnish.LCK.sessmem.destroy
varnish.LCK.sessmem.locks
varnish.LCK.sma.colls
varnish.LCK.sma.creat
varnish.LCK.sma.destroy
varnish.LCK.sma.locks
varnish.LCK.smf.colls
varnish.LCK.smf.creat
varnish.LCK.smf.destroy
varnish.LCK.smf.locks
varnish.LCK.smp.colls
varnish.LCK.smp.creat
varnish.LCK.smp.destroy
varnish.LCK.smp.locks
varnish.LCK.sms.colls
varnish.LCK.sms.creat
varnish.LCK.sms.destroy
varnish.LCK.sms.locks
varnish.LCK.stat.colls
varnish.LCK.stat.creat
varnish.LCK.stat.destroy
varnish.LCK.stat.locks
varnish.LCK.vbe.colls
varnish.LCK.vbe.creat
varnish.LCK.vbe.destroy
varnish.LCK.vbe.locks
varnish.LCK.vbp.colls
varnish.LCK.vbp.creat
varnish.LCK.vbp.destroy
varnish.LCK.vbp.locks
varnish.LCK.vcl.colls
varnish.LCK.vcl.creat
varnish.LCK.vcl.destroy
varnish.LCK.vcl.locks
varnish.LCK.wq.colls
varnish.LCK.wq.creat
varnish.LCK.wq.destroy
varnish.LCK.wq.locks
varnish.LCK.wstat.colls
varnish.LCK.wstat.creat
varnish.LCK.wstat.destroy
varnish.LCK.wstat.locks
varnish.losthdr
varnish.n_backend
varnish.n_deathrow
varnish.n_ban
varnish.n_ban_add
varnish.n_ban_dups
varnish.n_ban_obj_test
varnish.n_ban_re_test
varnish.n_ban_retire
varnish.n_expired
varnish.n_gunzip
varnish.n_gzip
varnish.n_lru_moved
varnish.n_lru_nuked
varnish.n_lru_saved
varnish.n_object
varnish.n_objectcore
varnish.n_objecthead
varnish.n_objoverflow
varnish.n_objsendfile
varnish.n_objwrite
varnish.n_purge
varnish.n_purge_add
varnish.n_purge_dups
varnish.n_purge_obj_test
varnish.n_purge_re_test
varnish.n_purge_retire
varnish.n_sess
varnish.n_sess_mem
varnish.n_smf
varnish.n_smf_frag
varnish.n_smf_large
varnish.n_vampireobject
varnish.n_vbe_conn
varnish.n_vbc
varnish.n_vcl
varnish.n_vcl_avail
varnish.n_vcl_discard
varnish.n_waitinglist
varnish.n_wrk
varnish.n_wrk_create
varnish.n_wrk_drop
varnish.n_wrk_failed
varnish.n_wrk_lqueue
varnish.n_wrk_max
varnish.n_wrk_overflow
varnish.n_wrk_queue
varnish.n_wrk_queued
varnish.s_bodybytes
varnish.s_fetch
varnish.s_hdrbytes
varnish.s_pass
varnish.s_pipe
varnish.s_req
varnish.s_sess
varnish.sess_closed
varnish.sess_herd
varnish.sess_linger
varnish.sess_pipeline
varnish.sess_readahead
varnish.shm_cont
varnish.shm_cycles
varnish.shm_flushes
varnish.shm_records
varnish.shm_writes
varnish.sm_balloc
varnish.sm_bfree
varnish.sm_nobj
varnish.sm_nreq
varnish.sma_balloc
varnish.sma_bfree
varnish.sma_nbytes
varnish.sma_nobj
varnish.sma_nreq
varnish.SMA.s0.c_bytes
varnish.SMA.s0.c_fail
varnish.SMA.s0.c_freed
varnish.SMA.s0.c_req
varnish.SMA.s0.g_alloc
varnish.SMA.s0.g_bytes
varnish.SMA.s0.g_space
varnish.SMA.Transient.c_bytes
varnish.SMA.Transient.c_fail
varnish.SMA.Transient.c_freed
varnish.SMA.Transient.c_req
varnish.SMA.Transient.g_alloc
varnish.SMA.Transient.g_bytes
varnish.SMA.Transient.g_space
varnish.sms_balloc
varnish.sms_bfree
varnish.sms_nbytes
varnish.sms_nobj
varnish.sms_nreq
varnish.uptime

### Varnish 4.x

varnish.backend_busy
varnish.backend_conn
varnish.backend_fail
varnish.backend_recycle
varnish.backend_req
varnish.backend_retry
varnish.backend_reuse
varnish.backend_toolate
varnish.backend_unhealthy
varnish.bans
varnish.bans_added
varnish.bans_completed
varnish.bans_deleted
varnish.bans_dups
varnish.bans_lurker_contention
varnish.bans_lurker_obj_killed
varnish.bans_lurker_tested
varnish.bans_lurker_tests_tested
varnish.bans_obj
varnish.bans_obj_killed
varnish.bans_persisted_bytes
varnish.bans_persisted_fragmentation
varnish.bans_req
varnish.bans_tested
varnish.bans_tests_tested
varnish.busy_sleep
varnish.busy_wakeup
varnish.cache_hit
varnish.cache_hitpass
varnish.cache_miss
varnish.client_req
varnish.client_req_400
varnish.client_req_411
varnish.client_req_413
varnish.client_req_417
varnish.esi_errors
varnish.esi_warnings
varnish.exp_mailed
varnish.exp_received
varnish.fetch_1xx
varnish.fetch_204
varnish.fetch_304
varnish.fetch_bad
varnish.fetch_chunked
varnish.fetch_close
varnish.fetch_eof
varnish.fetch_failed
varnish.fetch_head
varnish.fetch_length
varnish.fetch_no_thread
varnish.fetch_oldhttp
varnish.fetch_zero
varnish.hcb_insert
varnish.hcb_lock
varnish.hcb_nolock
varnish.LCK.backend.creat
varnish.LCK.backend.destroy
varnish.LCK.backend.locks
varnish.LCK.ban.creat
varnish.LCK.ban.destroy
varnish.LCK.ban.locks
varnish.LCK.busyobj.creat
varnish.LCK.busyobj.destroy
varnish.LCK.busyobj.locks
varnish.LCK.cli.creat
varnish.LCK.cli.destroy
varnish.LCK.cli.locks
varnish.LCK.exp.creat
varnish.LCK.exp.destroy
varnish.LCK.exp.locks
varnish.LCK.hcb.creat
varnish.LCK.hcb.destroy
varnish.LCK.hcb.locks
varnish.LCK.hcl.creat
varnish.LCK.hcl.destroy
varnish.LCK.hcl.locks
varnish.LCK.herder.creat
varnish.LCK.herder.destroy
varnish.LCK.herder.locks
varnish.LCK.hsl.creat
varnish.LCK.hsl.destroy
varnish.LCK.hsl.locks
varnish.LCK.lru.creat
varnish.LCK.lru.destroy
varnish.LCK.lru.locks
varnish.LCK.mempool.creat
varnish.LCK.mempool.destroy
varnish.LCK.mempool.locks
varnish.LCK.nbusyobj.creat
varnish.LCK.nbusyobj.destroy
varnish.LCK.nbusyobj.locks
varnish.LCK.objhdr.creat
varnish.LCK.objhdr.destroy
varnish.LCK.objhdr.locks
varnish.LCK.pipestat.creat
varnish.LCK.pipestat.destroy
varnish.LCK.pipestat.locks
varnish.LCK.sess.creat
varnish.LCK.sess.destroy
varnish.LCK.sess.locks
varnish.LCK.sessmem.creat
varnish.LCK.sessmem.destroy
varnish.LCK.sessmem.locks
varnish.LCK.sma.creat
varnish.LCK.sma.destroy
varnish.LCK.sma.locks
varnish.LCK.smf.creat
varnish.LCK.smf.destroy
varnish.LCK.smf.locks
varnish.LCK.smp.creat
varnish.LCK.smp.destroy
varnish.LCK.smp.locks
varnish.LCK.sms.creat
varnish.LCK.sms.destroy
varnish.LCK.sms.locks
varnish.LCK.vbp.creat
varnish.LCK.vbp.destroy
varnish.LCK.vbp.locks
varnish.LCK.vcapace.creat
varnish.LCK.vcapace.destroy
varnish.LCK.vcapace.locks
varnish.LCK.vcl.creat
varnish.LCK.vcl.destroy
varnish.LCK.vcl.locks
varnish.LCK.vxid.creat
varnish.LCK.vxid.destroy
varnish.LCK.vxid.locks
varnish.LCK.wq.creat
varnish.LCK.wq.destroy
varnish.LCK.wq.locks
varnish.LCK.wstat.creat
varnish.LCK.wstat.destroy
varnish.LCK.wstat.locks
varnish.losthdr
varnish.MEMPOOL.busyobj.allocs
varnish.MEMPOOL.busyobj.frees
varnish.MEMPOOL.busyobj.live
varnish.MEMPOOL.busyobj.pool
varnish.MEMPOOL.busyobj.randry
varnish.MEMPOOL.busyobj.recycle
varnish.MEMPOOL.busyobj.surplus
varnish.MEMPOOL.busyobj.sz_needed
varnish.MEMPOOL.busyobj.sz_wanted
varnish.MEMPOOL.busyobj.timeout
varnish.MEMPOOL.busyobj.toosmall
varnish.MEMPOOL.req0.allocs
varnish.MEMPOOL.req0.frees
varnish.MEMPOOL.req0.live
varnish.MEMPOOL.req0.pool
varnish.MEMPOOL.req0.randry
varnish.MEMPOOL.req0.recycle
varnish.MEMPOOL.req0.surplus
varnish.MEMPOOL.req0.sz_needed
varnish.MEMPOOL.req0.sz_wanted
varnish.MEMPOOL.req0.timeout
varnish.MEMPOOL.req0.toosmall
varnish.MEMPOOL.req1.allocs
varnish.MEMPOOL.req1.frees
varnish.MEMPOOL.req1.live
varnish.MEMPOOL.req1.pool
varnish.MEMPOOL.req1.randry
varnish.MEMPOOL.req1.recycle
varnish.MEMPOOL.req1.surplus
varnish.MEMPOOL.req1.sz_needed
varnish.MEMPOOL.req1.sz_wanted
varnish.MEMPOOL.req1.timeout
varnish.MEMPOOL.req1.toosmall
varnish.MEMPOOL.sess0.allocs
varnish.MEMPOOL.sess0.frees
varnish.MEMPOOL.sess0.live
varnish.MEMPOOL.sess0.pool
varnish.MEMPOOL.sess0.randry
varnish.MEMPOOL.sess0.recycle
varnish.MEMPOOL.sess0.surplus
varnish.MEMPOOL.sess0.sz_needed
varnish.MEMPOOL.sess0.sz_wanted
varnish.MEMPOOL.sess0.timeout
varnish.MEMPOOL.sess0.toosmall
varnish.MEMPOOL.sess1.allocs
varnish.MEMPOOL.sess1.frees
varnish.MEMPOOL.sess1.live
varnish.MEMPOOL.sess1.pool
varnish.MEMPOOL.sess1.randry
varnish.MEMPOOL.sess1.recycle
varnish.MEMPOOL.sess1.surplus
varnish.MEMPOOL.sess1.sz_needed
varnish.MEMPOOL.sess1.sz_wanted
varnish.MEMPOOL.sess1.timeout
varnish.MEMPOOL.sess1.toosmall
varnish.MEMPOOL.vbc.allocs
varnish.MEMPOOL.vbc.frees
varnish.MEMPOOL.vbc.live
varnish.MEMPOOL.vbc.pool
varnish.MEMPOOL.vbc.randry
varnish.MEMPOOL.vbc.recycle
varnish.MEMPOOL.vbc.surplus
varnish.MEMPOOL.vbc.sz_needed
varnish.MEMPOOL.vbc.sz_wanted
varnish.MEMPOOL.vbc.timeout
varnish.MEMPOOL.vbc.toosmall
varnish.MGT.child_died
varnish.MGT.child_dump
varnish.MGT.child_exit
varnish.MGT.child_panic
varnish.MGT.child_start
varnish.MGT.child_stop
varnish.MGT.uptime
varnish.n_backend
varnish.n_expired
varnish.n_gunzip
varnish.n_gzip
varnish.n_lru_moved
varnish.n_lru_nuked
varnish.n_obj_purged
varnish.n_object
varnish.n_objectcore
varnish.n_objecthead
varnish.n_purges
varnish.n_vampireobject
varnish.n_vcl
varnish.n_vcl_avail
varnish.n_vcl_discard
varnish.n_waitinglist
varnish.pools
varnish.s_fetch
varnish.s_pass
varnish.s_pipe
varnish.s_pipe_hdrbytes
varnish.s_pipe_in
varnish.s_pipe_out
varnish.s_req
varnish.s_req_bodybytes
varnish.s_req_hdrbytes
varnish.s_resp_bodybytes
varnish.s_resp_hdrbytes
varnish.s_sess
varnish.s_synth
varnish.sess_closed
varnish.sess_conn
varnish.sess_drop
varnish.sess_dropped
varnish.sess_fail
varnish.sess_herd
varnish.sess_pipe_overflow
varnish.sess_pipeline
varnish.sess_queued
varnish.sess_readahead
varnish.shm_cont
varnish.shm_cycles
varnish.shm_flushes
varnish.shm_records
varnish.shm_writes
varnish.SMA.s0.c_bytes
varnish.SMA.s0.c_fail
varnish.SMA.s0.c_freed
varnish.SMA.s0.c_req
varnish.SMA.s0.g_alloc
varnish.SMA.s0.g_bytes
varnish.SMA.s0.g_space
varnish.SMA.Transient.c_bytes
varnish.SMA.Transient.c_fail
varnish.SMA.Transient.c_freed
varnish.SMA.Transient.c_req
varnish.SMA.Transient.g_alloc
varnish.SMA.Transient.g_bytes
varnish.SMA.Transient.g_space
varnish.sms_balloc
varnish.sms_bfree
varnish.sms_nbytes
varnish.sms_nobj
varnish.sms_nreq
varnish.thread_queue_len
varnish.threads
varnish.threads_created
varnish.threads_destroyed
varnish.threads_failed
varnish.threads_limited
varnish.uptime
varnish.VBE.default_127.0.0.1_80.bereq_bodybytes
varnish.VBE.default_127.0.0.1_80.bereq_hdrbytes
varnish.VBE.default_127.0.0.1_80.beresp_bodybytes
varnish.VBE.default_127.0.0.1_80.beresp_hdrbytes
varnish.VBE.default_127.0.0.1_80.pipe_hdrbytes
varnish.VBE.default_127.0.0.1_80.pipe_in
varnish.VBE.default_127.0.0.1_80.pipe_out
varnish.VBE.default_127.0.0.1_80.vcls
varnish.vmods
varnish.vsm_cooling
varnish.vsm_free
varnish.vsm_overflow
varnish.vsm_overflowed
varnish.vsm_used