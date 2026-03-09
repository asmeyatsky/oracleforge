# ---------------------------------------------------------------------------
# IAM Module — Variables
# ---------------------------------------------------------------------------

variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)."
  type        = string
}

variable "labels" {
  description = "Labels passed through for reference (not all IAM resources support labels)."
  type        = map(string)
  default     = {}
}
