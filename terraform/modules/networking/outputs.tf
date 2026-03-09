# ---------------------------------------------------------------------------
# Networking Module — Outputs
# ---------------------------------------------------------------------------

output "vpc_id" {
  description = "Self-link of the OracleForge VPC."
  value       = google_compute_network.vpc.self_link
}

output "vpc_name" {
  description = "Name of the OracleForge VPC."
  value       = google_compute_network.vpc.name
}

output "subnet_id" {
  description = "Self-link of the primary subnet."
  value       = google_compute_subnetwork.main.self_link
}

output "subnet_name" {
  description = "Name of the primary subnet."
  value       = google_compute_subnetwork.main.name
}

output "private_connection_id" {
  description = "Fully-qualified ID of the Datastream private connection."
  value       = google_datastream_private_connection.datastream.id
}

output "private_services_peering_id" {
  description = "ID of the private services networking connection."
  value       = google_service_networking_connection.private_services.id
}
