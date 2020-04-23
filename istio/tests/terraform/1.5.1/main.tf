# Shared common terraform config found in the templates/terraform folder in datadog_checks_dev
resource "google_container_cluster" "gke_cluster" {
  name = replace("istio-cluster-${var.user}-${random_string.suffix.result}", ".", "-")
  location = random_shuffle.az.result[0]

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

resource "null_resource" "startup" {
  provisioner "local-exec" {
    command = "python ./script.py"
    environment = {
      KUBECONFIG = "${local_file.kubeconfig.filename}"
      ISTIO_VERSION = "1.5.1"
    }
  }
}

output "kubeconfig" {
  value = abspath("${local_file.kubeconfig.filename}")
}