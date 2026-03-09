# ---------------------------------------------------------------------------
# OracleForge GCP Landing Zone — Root Module
# ---------------------------------------------------------------------------
# Composes the networking, IAM, BigQuery, GCS, and Datastream sub-modules
# into a single deployable landing zone for Oracle EBS modernization on GCP.
# ---------------------------------------------------------------------------

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0, < 7.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = ">= 5.0, < 7.0"
    }
  }

  # Uncomment and configure for remote state:
  # backend "gcs" {
  #   bucket = "oracleforge-tfstate"
  #   prefix = "landing-zone"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# ── Local values ────────────────────────────────────────────────────────────

locals {
  common_labels = merge(
    {
      project     = "oracleforge"
      environment = var.environment
      managed_by  = "terraform"
    },
    var.labels,
  )
}

# ── Networking ──────────────────────────────────────────────────────────────

module "networking" {
  source = "./modules/networking"

  project_id  = var.project_id
  region      = var.region
  environment = var.environment
  vpc_cidr    = var.vpc_cidr
  subnet_cidr = var.subnet_cidr
  psc_cidr    = var.psc_cidr
  labels      = local.common_labels
}

# ── IAM ─────────────────────────────────────────────────────────────────────

module "iam" {
  source = "./modules/iam"

  project_id  = var.project_id
  environment = var.environment
  labels      = local.common_labels
}

# ── BigQuery (Medallion Architecture) ───────────────────────────────────────

module "bigquery" {
  source = "./modules/bigquery"

  project_id  = var.project_id
  region      = var.region
  environment = var.environment
  labels      = local.common_labels

  # Grant the pipeline SA permissions inside the datasets
  pipeline_sa_email = module.iam.pipeline_sa_email
  viewer_sa_email   = module.iam.viewer_sa_email
}

# ── Cloud Storage ───────────────────────────────────────────────────────────

module "storage" {
  source = "./modules/storage"

  project_id  = var.project_id
  region      = var.region
  environment = var.environment
  labels      = local.common_labels

  pipeline_sa_email = module.iam.pipeline_sa_email
}

# ── Datastream (Oracle CDC → BigQuery) ──────────────────────────────────────

module "datastream" {
  source = "./modules/datastream"

  project_id  = var.project_id
  region      = var.region
  environment = var.environment
  labels      = local.common_labels

  oracle_host     = var.oracle_host
  oracle_port     = var.oracle_port
  oracle_username = var.oracle_username
  oracle_password = var.oracle_password
  oracle_database = var.oracle_database
  oracle_schemas  = var.oracle_schemas

  bronze_dataset_id       = module.bigquery.bronze_dataset_id
  vpc_id                  = module.networking.vpc_id
  datastream_sa_email     = module.iam.datastream_sa_email
  private_connection_id   = module.networking.private_connection_id
}
