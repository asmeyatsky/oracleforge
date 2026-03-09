# ---------------------------------------------------------------------------
# Datastream Module — Outputs
# ---------------------------------------------------------------------------

output "stream_id" {
  description = "ID of the Datastream CDC stream."
  value       = google_datastream_stream.oracle_to_bigquery.stream_id
}

output "stream_name" {
  description = "Full resource name of the Datastream stream."
  value       = google_datastream_stream.oracle_to_bigquery.name
}

output "oracle_connection_profile_id" {
  description = "ID of the Oracle source connection profile."
  value       = google_datastream_connection_profile.oracle_source.connection_profile_id
}

output "bigquery_connection_profile_id" {
  description = "ID of the BigQuery destination connection profile."
  value       = google_datastream_connection_profile.bigquery_dest.connection_profile_id
}
