# ---------------------------------------------------------------------------
# IAM Module — Outputs
# ---------------------------------------------------------------------------

output "pipeline_sa_email" {
  description = "Email address of the oracleforge-pipeline service account."
  value       = google_service_account.pipeline.email
}

output "pipeline_sa_id" {
  description = "Fully-qualified ID of the oracleforge-pipeline service account."
  value       = google_service_account.pipeline.id
}

output "datastream_sa_email" {
  description = "Email address of the oracleforge-datastream service account."
  value       = google_service_account.datastream.email
}

output "datastream_sa_id" {
  description = "Fully-qualified ID of the oracleforge-datastream service account."
  value       = google_service_account.datastream.id
}

output "viewer_sa_email" {
  description = "Email address of the oracleforge-viewer service account."
  value       = google_service_account.viewer.email
}

output "viewer_sa_id" {
  description = "Fully-qualified ID of the oracleforge-viewer service account."
  value       = google_service_account.viewer.id
}
