exit_after_auth = true
pid_file = "/tmp/agent_pid"

auto_auth {
  method "jwt" {
    config = {
      path = "/home/jwt/claim"
      role = "datadog"
    }
  }

  sink "file" {
    config = {
      path = "/home/sink/token"
    }
  }
}

vault {
  address = "http://0.0.0.0:8200"
}
