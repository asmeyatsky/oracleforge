# ---------------------------------------------------------------------------
# OracleForge GCP Landing Zone — Root Outputs
# ---------------------------------------------------------------------------

# ── BigQuery ────────────────────────────────────────────────────────────────

output "bigquery_bronze_dataset_id" {
  description = "Fully-qualified ID of the bronze (raw) BigQuery dataset."
  value       = module.bigquery.bronze_dataset_id
}

output "bigquery_silver_dataset_id" {
  description = "Fully-qualified ID of the silver (cleansed) BigQuery dataset."
  value       = module.bigquery.silver_dataset_id
}

output "bigquery_gold_dataset_id" {
  description = "Fully-qualified ID of the gold (curated) BigQuery dataset."
  value       = module.bigquery.gold_dataset_id
}

# ── GCS Buckets ─────────────────────────────────────────────────────────────

output "gcs_raw_bucket_name" {
  description = "Name of the GCS bucket for raw Oracle exports."
  value       = module.storage.raw_bucket_name
}

output "gcs_staging_bucket_name" {
  description = "Name of the GCS bucket for staging / intermediate data."
  value       = module.storage.staging_bucket_name
}

output "gcs_archive_bucket_name" {
  description = "Name of the GCS bucket for long-term archive."
  value       = module.storage.archive_bucket_name
}

# ── IAM ─────────────────────────────────────────────────────────────────────

output "pipeline_service_account_email" {
  description = "Email of the oracleforge-pipeline service account."
  value       = module.iam.pipeline_sa_email
}

output "datastream_service_account_email" {
  description = "Email of the oracleforge-datastream service account."
  value       = module.iam.datastream_sa_email
}

output "viewer_service_account_email" {
  description = "Email of the oracleforge-viewer service account."
  value       = module.iam.viewer_sa_email
}

# ── Datastream ──────────────────────────────────────────────────────────────

output "datastream_stream_id" {
  description = "ID of the Datastream CDC stream."
  value       = module.datastream.stream_id
}

# ── Networking ──────────────────────────────────────────────────────────────

output "vpc_id" {
  description = "Self-link of the OracleForge VPC."
  value       = module.networking.vpc_id
}

output "subnet_id" {
  description = "Self-link of the primary subnet."
  value       = module.networking.subnet_id
}
