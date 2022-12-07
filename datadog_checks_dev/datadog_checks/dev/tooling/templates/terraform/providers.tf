provider "google" {
  credentials = var.account_json
  project = "datadog-integrations-lab"
  region = "europe-west4"
  zone = random_shuffle.az.result[0]
}
