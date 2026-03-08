# main.tf for OracleForge Landing Zone

provider "google" {
  project = var.project_id
  region  = var.region
}

# VPC Network
resource "google_compute_network" "oracleforge_vpc" {
  name                    = "oracleforge-vpc"
  auto_create_subnetworks = false
}

# Subnets for regional lockdown
resource "google_compute_subnetwork" "dammam_subnet" {
  name          = "dammam-subnet"
  ip_cidr_range = "10.0.1.0/24"
  region        = "me-central2" # Dammam
  network       = google_compute_network.oracleforge_vpc.id
}

resource "google_compute_subnetwork" "doha_subnet" {
  name          = "doha-subnet"
  ip_cidr_range = "10.0.2.0/24"
  region        = "me-west1" # Doha
  network       = google_compute_network.oracleforge_vpc.id
}

# KMS Key for Encryption (CMEK)
resource "google_kms_key_ring" "oracleforge_keyring" {
  name     = "oracleforge-keyring"
  location = var.region
}

resource "google_kms_crypto_key" "oracleforge_key" {
  name     = "oracleforge-key"
  key_ring = google_kms_key_ring.oracleforge_keyring.id
}

# IAM Policies for SAMA/NDMO Compliance
resource "google_project_iam_binding" "bq_data_viewer" {
  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  members = var.compliance_auditors
}
