# variables.tf for OracleForge Landing Zone

variable "project_id" {
  description = "The GCP Project ID."
  type        = str
}

variable "region" {
  description = "Default GCP Region."
  type        = str
  default     = "me-central2" # Dammam
}

variable "compliance_auditors" {
  description = "List of auditor members for SAMA/NDMO compliance."
  type        = list(string)
  default     = []
}
