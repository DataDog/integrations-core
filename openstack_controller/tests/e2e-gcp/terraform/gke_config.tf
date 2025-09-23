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

variable "local_conf_path" {
  type = string
}

variable "main_script_path" {
  type = string
}

variable "install_deps_script_path" {
  type = string
}