# Shared common terraform config found in the templates/terraform folder in datadog_checks_dev
resource "google_compute_instance" "linkerd-init" {
  name = replace("linkerd-init-${var.user}-${random_string.suffix.result}", ".", "-")
  machine_type = "n1-standard-2"

  tags = ["linkerd", "lab"]
  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-1804-lts"
      size = 30
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
    private_key = tls_private_key.ssh-key.private_key_pem
    host = google_compute_instance.linkerd-init.network_interface.0.access_config.0.nat_ip
  }

  provisioner "file" {
    source = local_file.kubeconfig.filename
    destination = "kubeconfig"
  }

}

resource "null_resource" "linkerd-init" {
  depends_on = [google_container_cluster.gke_cluster, google_compute_instance.linkerd-init]

  connection {
    type = "ssh"
    user = "ubuntu"
    private_key = tls_private_key.ssh-key.private_key_pem
    host = google_compute_instance.linkerd-init.network_interface.0.access_config.0.nat_ip
  }

  provisioner "remote-exec" {
    script = "linkerd-init.sh"
  }
}

resource "google_container_cluster" "gke_cluster" {
  name = replace("linkerd-cluster-${var.user}-${random_string.suffix.result}", ".", "-")
  location = random_shuffle.az.result[0]

  lifecycle {
    ignore_changes = ["node_pool"]
  }

  initial_node_count = 3

  master_auth {
    username = "user"
    password = random_id.password.hex
  }

  node_config {
    disk_size_gb = 10
    disk_type = "pd-standard"
    machine_type = "n1-standard-2"
    oauth_scopes = [
      "https://www.googleapis.com/auth/compute",
      "https://www.googleapis.com/auth/devstorage.read_only",
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring",
    ]
    tags = ["linkerd", "lab"]
  }
}

output "kubeconfig" {
  value = abspath(local_file.kubeconfig.filename)
}
