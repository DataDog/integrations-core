variable "account_json" {
  type = string
}

locals {
  password = "ThisIsAVeryWeirdRandomPassword"
  user = "user"
}

resource "random_shuffle" "az" {
  input = ["europe-west2-a", "europe-west2-b", "europe-west2-c"]
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
  region = "europe-west2"
  zone = random_shuffle.az.result[0]
}

provider "kubernetes" {
  version = "~> 1.2"
  username = local.user
  password = local.password
  host     = "https://${google_container_cluster.gke_cluster.endpoint}"

  client_certificate     = base64decode(google_container_cluster.gke_cluster.master_auth.0.client_certificate)
  client_key             = base64decode(google_container_cluster.gke_cluster.master_auth.0.client_key)
  cluster_ca_certificate = base64decode(google_container_cluster.gke_cluster.master_auth.0.cluster_ca_certificate)
}

resource "google_compute_network" "vpc_network" {
  name = "istio-network"
}

resource "google_compute_firewall" "default" {
  name    = "istio-test-http-ip-firewall"
  network = google_compute_network.vpc_network.name

  allow {
    protocol = "icmp"
  }

  allow {
    protocol = "tcp"
    ports    = ["80"]
  }

  source_ranges = ["38.122.226.210"]
}

resource "google_container_cluster" "gke_cluster" {
  name               = "istio-terraform-test-${random_string.suffix.result}"
  location           = random_shuffle.az.result[0]
  node_version = "1.13.7-gke.8"
  min_master_version = "1.13.7-gke.8"
  network           = google_compute_network.vpc_network.name

  lifecycle {
    ignore_changes = ["node_pool"]
  }

  initial_node_count = 4

  master_auth {
    username = local.user
    password = local.password
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

  provisioner "local-exec" {
    command = "./script.sh"
    environment = {
      CA_CERTIFICATE = base64decode(google_container_cluster.gke_cluster.master_auth.0.cluster_ca_certificate)
      K8S_SERVER     = "https://${google_container_cluster.gke_cluster.endpoint}"
      K8S_USERNAME   = local.user
      K8S_PASSWORD   = local.password
      ISTIO_VERSION  = "1.2.0"
    }
  }
}

resource "kubernetes_service" "citadel" {
  metadata {
    name = "prometheus-citadel"
    namespace = "istio-system"
  }
  spec {
    selector = {
      istio = "citadel"
    }
    port {
      port        = 80
      target_port = 15014
    }

    type = "LoadBalancer"
  }
}

resource "kubernetes_service" "galley" {
  metadata {
    name = "prometheus-galley"
    namespace = "istio-system"
  }
  spec {
    selector = {
      istio = "galley"
    }
    port {
      port        = 80
      target_port = 15014
    }

    type = "LoadBalancer"
  }
}

resource "kubernetes_service" "mesh" {
  metadata {
    name = "prometheus-mesh"
    namespace = "istio-system"
  }
  spec {
    selector = {
      app = "telemetry"
    }
    port {
      port        = 80
      target_port = 42422
    }

    type = "LoadBalancer"
  }
}

resource "kubernetes_service" "mixer" {
  metadata {
    name = "prometheus-mixer"
    namespace = "istio-system"
  }
  spec {
    selector = {
      app = "telemetry"
    }
    port {
      port        = 80
      target_port = 15014
    }

    type = "LoadBalancer"
  }
}

resource "kubernetes_service" "pilot" {
  metadata {
    name = "prometheus-pilot"
    namespace = "istio-system"
  }
  spec {
    selector = {
      istio = "pilot"
    }
    port {
      port        = 80
      target_port = 15014
    }

    type = "LoadBalancer"
  }
}

output "citadel-ip" {
  value = kubernetes_service.citadel.load_balancer_ingress.0.ip
}

output "galley-ip" {
  value = kubernetes_service.galley.load_balancer_ingress.0.ip
}

output "mesh-ip" {
  value = kubernetes_service.mesh.load_balancer_ingress.0.ip
}

output "mixer-ip" {
  value = kubernetes_service.mixer.load_balancer_ingress.0.ip
}

output "pilot-ip" {
  value = kubernetes_service.pilot.load_balancer_ingress.0.ip
}
