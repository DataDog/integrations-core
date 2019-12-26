provider "google" {
  version = "~> 2.11"
  credentials = var.account_json
  project = "datadog-integrations-lab"
  region = "europe-west4"
  zone = random_shuffle.az.result[0]
}
