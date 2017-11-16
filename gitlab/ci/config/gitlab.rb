# Test config file for Gitlab
prometheus_monitoring['enable'] = true
prometheus['listen_address'] = '0.0.0.0:9090'
# For the sake of these tests, whitelist access to monitor this instance
gitlab_rails['monitoring_whitelist'] = ['0.0.0.0/0']
