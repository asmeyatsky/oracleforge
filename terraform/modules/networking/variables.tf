# ---------------------------------------------------------------------------
# Networking Module — Variables
# ---------------------------------------------------------------------------

variable "project_id" {
  description = "GCP project ID."
  type        = string
}

variable "region" {
  description = "GCP region for networking resources."
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev, staging, prod)."
  type        = string
}

variable "labels" {
  description = "Labels to apply to networking resources (where supported)."
  type        = map(string)
  default     = {}
}

variable "vpc_cidr" {
  description = "Primary CIDR block for the VPC (used for documentation; GCP VPCs are subnet-based)."
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_cidr" {
  description = "CIDR block for the main subnet."
  type        = string
  default     = "10.0.1.0/24"
}

variable "psc_cidr" {
  description = "CIDR block for Private Service Connect / private services access."
  type        = string
  default     = "10.0.64.0/20"
}
