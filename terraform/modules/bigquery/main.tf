# ---------------------------------------------------------------------------
# BigQuery Module — Medallion Architecture Datasets (Bronze / Silver / Gold)
# ---------------------------------------------------------------------------

locals {
  # Map BigQuery location from the GCP region.  BigQuery uses multi-region
  # names for some locations; for single-region deployments the region string
  # itself is a valid location.
  bq_location = var.region
}

# ── Bronze (raw / landing) ──────────────────────────────────────────────────

resource "google_bigquery_dataset" "bronze" {
  project    = var.project_id
  dataset_id = "oracleforge_bronze_${var.environment}"
  location   = local.bq_location

  friendly_name              = "OracleForge Bronze (${var.environment})"
  description                = "Raw CDC data ingested from Oracle EBS via Datastream."
  delete_contents_on_destroy = false
  default_table_expiration_ms = null

  labels = merge(var.labels, { tier = "bronze" })

  access {
    role          = "WRITER"
    user_by_email = var.pipeline_sa_email
  }

  access {
    role          = "READER"
    user_by_email = var.viewer_sa_email
  }

  access {
    role          = "OWNER"
    special_group = "projectOwners"
  }
}

# ── Silver (cleansed / conformed) ───────────────────────────────────────────

resource "google_bigquery_dataset" "silver" {
  project    = var.project_id
  dataset_id = "oracleforge_silver_${var.environment}"
  location   = local.bq_location

  friendly_name              = "OracleForge Silver (${var.environment})"
  description                = "Cleansed and conformed data derived from bronze."
  delete_contents_on_destroy = false
  default_table_expiration_ms = null

  labels = merge(var.labels, { tier = "silver" })

  access {
    role          = "WRITER"
    user_by_email = var.pipeline_sa_email
  }

  access {
    role          = "READER"
    user_by_email = var.viewer_sa_email
  }

  access {
    role          = "OWNER"
    special_group = "projectOwners"
  }
}

# ── Gold (curated / business-ready) ────────────────────────────────────────

resource "google_bigquery_dataset" "gold" {
  project    = var.project_id
  dataset_id = "oracleforge_gold_${var.environment}"
  location   = local.bq_location

  friendly_name              = "OracleForge Gold (${var.environment})"
  description                = "Curated business-ready datasets for analytics and reporting."
  delete_contents_on_destroy = false
  default_table_expiration_ms = null

  labels = merge(var.labels, { tier = "gold" })

  access {
    role          = "WRITER"
    user_by_email = var.pipeline_sa_email
  }

  access {
    role          = "READER"
    user_by_email = var.viewer_sa_email
  }

  access {
    role          = "OWNER"
    special_group = "projectOwners"
  }
}
