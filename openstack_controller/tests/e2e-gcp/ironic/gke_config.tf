variable "credentials_file" {
  type = string
}

variable "desired_status" {
  type = string
}

variable "network_ip" {
  type = string
}

variable "nat_ip" {
  type = string
}

variable "instance_name" {
  type = string
}

resource "tls_private_key" "ssh-key" {
  algorithm = "RSA"
  rsa_bits = 4096
}
