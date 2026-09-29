# Test config file for GitLab, with every metrics exporter enabled.
#
# Kept separate from gitlab.rb because it uses the nested `gitaly['configuration']`
# syntax, which the older versions in the default hatch matrix (13.12, 14.10)
# do not understand. Use this file only with the `exporters` env.
prometheus_monitoring['enable'] = true
prometheus['listen_address'] = '0.0.0.0:9090'
gitlab_rails['monitoring_whitelist'] = ['0.0.0.0/0']

# Workhorse metrics (gitlab_workhorse_http_requests_total,
# gitlab_workhorse_http_request_duration_seconds) are served by Workhorse's own
# listener. They never appear on the Rails /-/metrics endpoint.
gitlab_workhorse['prometheus_listen_addr'] = '0.0.0.0:9229'

# Sidekiq metrics (sidekiq_mem_total_bytes, sidekiq_load_balancing_count) come
# from the Sidekiq exporter, also a separate listener from Rails.
sidekiq['metrics_enabled'] = true
sidekiq['listen_address'] = '0.0.0.0'
sidekiq['listen_port'] = 8082

# Current Omnibus reads Gitaly settings only from `gitaly['configuration']`; the
# flat `gitaly['prometheus_listen_addr']` used by gitlab.rb is legacy and is
# ignored on recent versions, leaving Gitaly bound to localhost and unreachable
# from the host.
# `adaptive: true` is what makes gitaly_concurrency_limiting_current_limit exist:
# the gauge is seeded from initial_limit when the adaptive calculator starts.
# Note the docs say adaptive limiting requires cgroups, but that applies to
# recalibration, not to the metric being exported. Without cgroup limits the
# value simply stays at initial_limit, which is enough to exercise the metric
# and avoids needing a privileged container.
gitaly['configuration'] = {
  prometheus_listen_addr: '0.0.0.0:9236',
  concurrency: [
    {
      rpc: '/gitaly.SmartHTTPService/PostUploadPackWithSidechannel',
      max_queue_wait: '1s',
      max_queue_size: 10,
      adaptive: true,
      min_limit: 10,
      initial_limit: 20,
      max_limit: 40,
    },
  ],
}

# Trim services that are irrelevant to metric collection but slow the boot down.
# Do not add grafana['enable'] here: the bundled Grafana was removed from Omnibus
# in 16.3, and reading a removed key makes `gitlab-ctl reconfigure` fail outright.
registry['enable'] = false
alertmanager['enable'] = false
