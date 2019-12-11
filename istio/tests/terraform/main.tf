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

provider "google" {
  version = "~> 2.11"
  credentials = var.account_json
  project = "datadog-integrations-lab"
  region = "europe-west4"
  zone = random_shuffle.az.result[0]
}

resource "local_file" "kubeconfig" {
  content = "${data.template_file.kubeconfig.rendered}"
  filename = "${path.module}/kubeconfig"
}

resource "google_container_cluster" "gke_cluster" {
  name = replace("istio-cluster-${var.user}-${random_string.suffix.result}", ".", "-")
  location = random_shuffle.az.result[0]
  min_master_version = "1.13.11-gke.14"

  lifecycle {
    ignore_changes = ["node_pool"]
  }

  initial_node_count = 4

  master_auth {
    username = "user"
    password = "${random_id.password.hex}"
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
  }
}

data "template_file" "kubeconfig" {
  template = "${file("${path.module}/kubeconfig-template.yaml")}"

  vars = {
    cluster_name = "${google_container_cluster.gke_cluster.name}"
    user_name = "${google_container_cluster.gke_cluster.master_auth.0.username}"
    user_password = "${google_container_cluster.gke_cluster.master_auth.0.password}"
    endpoint = "${google_container_cluster.gke_cluster.endpoint}"
    cluster_ca = "${google_container_cluster.gke_cluster.master_auth.0.cluster_ca_certificate}"
    client_cert = "${google_container_cluster.gke_cluster.master_auth.0.client_certificate}"
    client_cert_key = "${google_container_cluster.gke_cluster.master_auth.0.client_key}"
  }
}

resource "null_resource" "startup" {
  provisioner "local-exec" {
    command = "python ./script.py"
    environment = {
      KUBECONFIG = "${local_file.kubeconfig.filename}"
      ISTIO_VERSION = "1.2.3"
    }
  }
}

output "kubeconfig" {
  value = abspath("${local_file.kubeconfig.filename}")
}
