# ---------------------------------------------------------------------------
# BigQuery Module — Variables
# ---------------------------------------------------------------------------

variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "GCP region / BigQuery data location."
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)."
  type        = string
}

variable "labels" {
  description = "Labels to apply to all BigQuery datasets."
  type        = map(string)
  default     = {}
}

variable "pipeline_sa_email" {
  description = "Email of the pipeline service account (BigQuery Data Editor)."
  type        = string
}

variable "viewer_sa_email" {
  description = "Email of the viewer service account (BigQuery Data Viewer)."
  type        = string
}
