path "sys/metrics*" {
  capabilities = ["read", "list"]
}

path "sys/audit" {
  capabilities = ["read", "sudo"]
}

path "sys/license" {
  capabilities = ["read", "list"]
}

path "sys/mounts" {
  capabilities = ["read", "list"]
}

path "sys/host-info" {
  capabilities = ["read", "list"]
}
