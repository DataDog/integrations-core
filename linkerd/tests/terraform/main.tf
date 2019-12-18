variable "account_json" {
  type = string
}

variable "user" {
  type = string
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

resource "tls_private_key" "ssh-key" {
  algorithm = "RSA"
  rsa_bits = 4096
}

provider "google" {
  version = "~> 2.11"
  credentials = var.account_json
  project = "datadog-integrations-lab"
  region = "europe-west4"
  zone = random_shuffle.az.result[0]
}

resource "local_file" "kubeconfig" {
  content = data.template_file.kubeconfig.rendered
  filename = "${path.module}/kubeconfig"
}

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
  min_master_version = "1.13.11-gke.14"

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

data "template_file" "kubeconfig" {
  template = file("${path.module}/kubeconfig-template.yaml")

  vars = {
    cluster_name = google_container_cluster.gke_cluster.name
    user_name = google_container_cluster.gke_cluster.master_auth.0.username
    user_password = google_container_cluster.gke_cluster.master_auth.0.password
    endpoint = google_container_cluster.gke_cluster.endpoint
    cluster_ca = google_container_cluster.gke_cluster.master_auth.0.cluster_ca_certificate
    client_cert = google_container_cluster.gke_cluster.master_auth.0.client_certificate
    client_cert_key = google_container_cluster.gke_cluster.master_auth.0.client_key
  }
}

output "kubeconfig" {
  value = abspath(local_file.kubeconfig.filename)
}
