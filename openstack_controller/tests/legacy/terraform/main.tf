# Shared common terraform config found in the templates/terraform folder in datadog_checks_dev
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
  sensitive = true
}

output "ssh_public_key" {
  value = "${tls_private_key.ssh-key.public_key_openssh}"
}
