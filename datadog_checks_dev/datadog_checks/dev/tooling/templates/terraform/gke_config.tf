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

resource "local_file" "kubeconfig" {
  content = "${data.template_file.kubeconfig.rendered}"
  filename = "${path.module}/kubeconfig"
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
