# ---------------------------------------------------------------------------
# OracleForge GCP Landing Zone — Root Input Variables
# ---------------------------------------------------------------------------

variable "project_id" {
  description = "GCP project ID where all resources will be provisioned."
  type        = string
}

variable "region" {
  description = "Default GCP region. Supports us-central1, me-central1, me-central2, etc."
  type        = string
  default     = "us-central1"
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)."
  type        = string
  default     = "dev"

  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be one of: dev, staging, prod."
  }
}

variable "oracle_host" {
  description = "Hostname or IP of the Oracle EBS source database."
  type        = string
}

variable "oracle_port" {
  description = "Listener port of the Oracle source database."
  type        = number
  default     = 1521
}

variable "oracle_username" {
  description = "Username for the Oracle Datastream replication user."
  type        = string
  sensitive   = true
}

variable "oracle_password" {
  description = "Password for the Oracle Datastream replication user."
  type        = string
  sensitive   = true
}

variable "oracle_database" {
  description = "Oracle SID or service name."
  type        = string
  default     = "EBSPROD"
}

variable "oracle_schemas" {
  description = "List of Oracle schemas to replicate via Datastream."
  type        = list(string)
  default     = ["APPS", "AR", "AP", "GL", "INV", "PO"]
}

variable "vpc_cidr" {
  description = "Primary CIDR block for the OracleForge VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_cidr" {
  description = "CIDR block for the main subnet."
  type        = string
  default     = "10.0.1.0/24"
}

variable "psc_cidr" {
  description = "CIDR block for Private Service Connect / private service access."
  type        = string
  default     = "10.0.64.0/20"
}

variable "labels" {
  description = "Additional labels to apply to all resources."
  type        = map(string)
  default     = {}
}
