path "sys/metrics*" {
  capabilities = ["read", "list"]
}

// Might be needed later for license monitoring
path "sys/license" {
  capabilities = ["read", "list"]
}
