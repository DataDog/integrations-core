variable "account_json" {
  type = string
}

variable "user" {
  type = string
}

resource "tls_private_key" "ssh-key" {
  algorithm = "RSA"
  rsa_bits = 4096
}

resource "random_id" "password" {
  byte_length = 16
}

resource "random_shuffle" "az" {
  input = ["europe-west4-a", "europe-west4-b", "europe-west4-c"]
  result_count = 1
}

resource "random_string" "suffix" {
  length = 8
  special = false
  upper = false
}
