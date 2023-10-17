resource "google_compute_instance" "openstack" {
  desired_status = var.desired_status
  name = var.instance_name
  machine_type = "n1-standard-4"
  tags = ["openstack", "lab"]
  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2004-lts"
      size = 100
    }
  }
  network_interface {
    network = "default"
    network_ip = var.network_ip
    access_config {
      nat_ip = var.nat_ip
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
    host = "${google_compute_instance.openstack.network_interface.0.access_config.0.nat_ip}"
  }
  provisioner "remote-exec" {
    script = "script.sh"
  }
}

data "google_compute_instance" "openstack" {
  name = google_compute_instance.openstack.name
  depends_on = [google_compute_instance.openstack]
}

output "ip" {
  value = data.google_compute_instance.openstack.network_interface[0].access_config[0].nat_ip
}

output "internal_ip" {
  value = data.google_compute_instance.openstack.network_interface[0].network_ip
}

output "ssh_private_key" {
  value = "${tls_private_key.ssh-key.private_key_pem}"
  sensitive = true
}

output "ssh_public_key" {
  value = "${tls_private_key.ssh-key.public_key_openssh}"
}