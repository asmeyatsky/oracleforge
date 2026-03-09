# ---------------------------------------------------------------------------
# Datastream Module — Variables
# ---------------------------------------------------------------------------

variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "GCP region for Datastream resources."
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)."
  type        = string
}

variable "labels" {
  description = "Labels to apply to Datastream resources."
  type        = map(string)
  default     = {}
}

# ── Oracle Source ───────────────────────────────────────────────────────────

variable "oracle_host" {
  description = "Hostname or IP of the Oracle EBS database."
  type        = string
}

variable "oracle_port" {
  description = "Oracle listener port."
  type        = number
  default     = 1521
}

variable "oracle_username" {
  description = "Oracle replication user."
  type        = string
  sensitive   = true
}

variable "oracle_password" {
  description = "Oracle replication password."
  type        = string
  sensitive   = true
}

variable "oracle_database" {
  description = "Oracle SID or service name."
  type        = string
}

variable "oracle_schemas" {
  description = "List of Oracle schemas to replicate."
  type        = list(string)
  default     = ["APPS"]
}

# ── BigQuery Destination ───────────────────────────────────────────────────

variable "bronze_dataset_id" {
  description = "BigQuery dataset ID for the bronze (landing) tier."
  type        = string
}

# ── Networking ─────────────────────────────────────────────────────────────

variable "vpc_id" {
  description = "Self-link of the VPC where Datastream runs."
  type        = string
}

variable "datastream_sa_email" {
  description = "Email of the Datastream service account."
  type        = string
}

variable "private_connection_id" {
  description = "ID of the Datastream private connection from the networking module."
  type        = string
}
