variable "account_json" {
  type = string
}

provider "google" {
  credentials = var.account_json
  project = "datadog-integrations-lab"
  region = "europe-west4"
  zone = "europe-west4-c"
}

resource "tls_private_key" "ssh-key" {
  algorithm = "RSA"
  rsa_bits = 4096
}

resource "random_string" "suffix" {
  length = 8
  special = false
  upper = false
}

resource "google_compute_instance" "oracle" {
  name = "oracle-${random_string.suffix.result}"
  machine_type = "n1-standard-4"

  tags = ["oracle", "lab"]

  boot_disk {
    initialize_params {
      image = "centos-cloud/centos-7"
      size = 200
    }
  }

  network_interface {
    network = "default"
    access_config {
    }
  }

  attached_disk {
    source = "oracle-sources"
  }

  metadata_startup_script = <<EOF
groupadd oinstall
groupadd dba
useradd -g oinstall -G dba oracle
echo "oracle ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers
sudo -u oracle mkdir /home/oracle/.ssh
sudo -u oracle curl -o /home/oracle/.ssh/authorized_keys "http://metadata.google.internal/computeMetadata/v1/instance/attributes/ssh-keys" -H "Metadata-Flavor: Google"
sudo -u oracle sed -i 's/oracle://' /home/oracle/.ssh/authorized_keys
EOF

  metadata = {
    enable-oslogin = "TRUE"
    ssh-keys = "oracle:${tls_private_key.ssh-key.public_key_openssh} oracle"
  }

  connection {
    type = "ssh"
    user = "oracle"
    private_key = "${tls_private_key.ssh-key.private_key_pem}"
    host = "${google_compute_instance.oracle.network_interface.0.access_config.0.nat_ip}"
  }

  provisioner "file" {
    source = "db.rsp"
    destination = "/tmp/db.rsp"
  }

  provisioner "file" {
    source = "cfgrsp.properties"
    destination = "/tmp/cfgrsp.properties"
  }

  provisioner "file" {
    source = "grant.sql"
    destination = "/tmp/grant.sql"
  }

  provisioner "remote-exec" {
    script = "script.sh"
  }
}

output "ip" {
  value = "${google_compute_instance.oracle.network_interface.0.access_config.0.nat_ip}"
}

output "internal_ip" {
  value = "${google_compute_instance.oracle.network_interface.0.network_ip}"
}

output "ssh_private_key" {
  value = "${tls_private_key.ssh-key.private_key_pem}"
}

output "ssh_public_key" {
  value = "${tls_private_key.ssh-key.public_key_openssh}"
}

