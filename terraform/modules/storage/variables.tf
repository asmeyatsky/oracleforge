# ---------------------------------------------------------------------------
# Cloud Storage Module — Variables
# ---------------------------------------------------------------------------

variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "GCP region for bucket location."
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)."
  type        = string
}

variable "labels" {
  description = "Labels to apply to all GCS buckets."
  type        = map(string)
  default     = {}
}

variable "pipeline_sa_email" {
  description = "Email of the pipeline service account (Storage Object Admin)."
  type        = string
}

variable "archive_age_days" {
  description = "Number of days after which objects transition to ARCHIVE storage class."
  type        = number
  default     = 90
}

variable "delete_age_days" {
  description = "Number of days after which objects are permanently deleted."
  type        = number
  default     = 365
}

variable "force_destroy" {
  description = "Allow Terraform to destroy buckets even if they contain objects. Use with care."
  type        = bool
  default     = false
}
