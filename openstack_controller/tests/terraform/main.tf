variable "account_json" {
  type = string
}

variable "user" {
  type = string
}

resource "random_shuffle" "az" {
  input = ["europe-west2-a", "europe-west2-b", "europe-west2-c"]
  result_count = 1
}

provider "google" {
  credentials = var.account_json
  project = "datadog-integrations-lab"
  region = "europe-west2"
  zone = "${random_shuffle.az.result[0]}"
}

resource "tls_private_key" "ssh-key" {
  algorithm = "RSA"
  rsa_bits = 4096
}

resource "random_string" "suffix" {
  length = 8
  special = false
  upper = false
}

resource "google_compute_instance" "devstack" {
  name = replace("devstack-${var.user}-${random_string.suffix.result}", ".", "-")
  machine_type = "n1-standard-4"

  tags = ["openstack", "lab"]

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-1804-lts"
      size = 100
    }
  }

  network_interface {
    network = "default"
    access_config {
    }
  }

  metadata = {
    enable-oslogin = "TRUE"
    ssh-keys = "ubuntu:${tls_private_key.ssh-key.public_key_openssh} ubuntu"
  }

  connection {
    type = "ssh"
    user = "ubuntu"
    private_key = "${tls_private_key.ssh-key.private_key_pem}"
    host = "${google_compute_instance.devstack.network_interface.0.access_config.0.nat_ip}"
  }

  provisioner "remote-exec" {
    script = "script.sh"
  }
}

output "ip" {
  value = "${google_compute_instance.devstack.network_interface.0.access_config.0.nat_ip}"
}

output "internal_ip" {
  value = "${google_compute_instance.devstack.network_interface.0.network_ip}"
}

output "ssh_private_key" {
  value = "${tls_private_key.ssh-key.private_key_pem}"
}

output "ssh_public_key" {
  value = "${tls_private_key.ssh-key.public_key_openssh}"
}
