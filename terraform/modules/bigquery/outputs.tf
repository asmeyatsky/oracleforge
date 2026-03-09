# ---------------------------------------------------------------------------
# BigQuery Module — Outputs
# ---------------------------------------------------------------------------

output "bronze_dataset_id" {
  description = "Fully-qualified dataset ID of the bronze dataset."
  value       = google_bigquery_dataset.bronze.dataset_id
}

output "silver_dataset_id" {
  description = "Fully-qualified dataset ID of the silver dataset."
  value       = google_bigquery_dataset.silver.dataset_id
}

output "gold_dataset_id" {
  description = "Fully-qualified dataset ID of the gold dataset."
  value       = google_bigquery_dataset.gold.dataset_id
}

output "bronze_dataset_self_link" {
  description = "Self-link of the bronze dataset."
  value       = google_bigquery_dataset.bronze.self_link
}
