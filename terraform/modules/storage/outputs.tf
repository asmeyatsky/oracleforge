# ---------------------------------------------------------------------------
# Cloud Storage Module — Outputs
# ---------------------------------------------------------------------------

output "raw_bucket_name" {
  description = "Name of the raw exports GCS bucket."
  value       = google_storage_bucket.raw.name
}

output "raw_bucket_url" {
  description = "gsutil URI of the raw exports bucket."
  value       = google_storage_bucket.raw.url
}

output "staging_bucket_name" {
  description = "Name of the staging GCS bucket."
  value       = google_storage_bucket.staging.name
}

output "staging_bucket_url" {
  description = "gsutil URI of the staging bucket."
  value       = google_storage_bucket.staging.url
}

output "archive_bucket_name" {
  description = "Name of the archive GCS bucket."
  value       = google_storage_bucket.archive.name
}

output "archive_bucket_url" {
  description = "gsutil URI of the archive bucket."
  value       = google_storage_bucket.archive.url
}
