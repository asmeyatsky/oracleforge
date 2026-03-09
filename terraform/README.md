# OracleForge GCP Landing Zone — Terraform

Infrastructure-as-Code for the OracleForge Oracle EBS to GCP Modernization
Accelerator.  This Terraform root module provisions a complete GCP landing zone
with the **medallion architecture** (bronze / silver / gold), Oracle CDC via
Google Cloud Datastream, and least-privilege IAM.

## Architecture

```
                ┌──────────────┐
                │  Oracle EBS  │
                │  (on-prem)   │
                └──────┬───────┘
                       │ CDC (LogMiner)
              ┌────────▼─────────┐
              │   Datastream     │
              │  (private conn)  │
              └────────┬─────────┘
                       │
        ┌──────────────▼──────────────┐
        │     BigQuery — Bronze       │  Raw CDC rows
        ├─────────────────────────────┤
        │     BigQuery — Silver       │  Cleansed / conformed
        ├─────────────────────────────┤
        │     BigQuery — Gold         │  Business-ready
        └─────────────────────────────┘

        ┌─────────────────────────────┐
        │  GCS: raw | staging | arch  │  Exports & backups
        └─────────────────────────────┘
```

## Modules

| Module | Description |
|---|---|
| `modules/networking` | VPC, subnet, Private Service Connect, Datastream private connection, firewall rules |
| `modules/iam` | Service accounts (pipeline, datastream, viewer) and project-level IAM bindings |
| `modules/bigquery` | Medallion architecture datasets (bronze, silver, gold) with dataset-level access |
| `modules/storage` | GCS buckets (raw, staging, archive) with versioning and lifecycle rules |
| `modules/datastream` | Oracle source and BigQuery destination connection profiles; CDC stream |

## Prerequisites

1. **GCP project** with billing enabled.
2. **APIs enabled** — the following APIs must be active:
   - `compute.googleapis.com`
   - `bigquery.googleapis.com`
   - `storage.googleapis.com`
   - `datastream.googleapis.com`
   - `servicenetworking.googleapis.com`
   - `iam.googleapis.com`
3. **Terraform >= 1.5** and the `google` / `google-beta` providers >= 5.0.
4. **gcloud CLI** authenticated with a principal that has `roles/owner` or
   equivalent permissions on the target project.

## Quick Start

```bash
# 1. Clone and enter the terraform directory
cd terraform/

# 2. Copy the example tfvars and fill in your values
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your project_id, Oracle credentials, etc.

# 3. Initialise Terraform
terraform init

# 4. Review the execution plan
terraform plan

# 5. Apply
terraform apply
```

## Configuration

All input variables are documented in `variables.tf`.  Key settings:

| Variable | Default | Description |
|---|---|---|
| `project_id` | *(required)* | GCP project ID |
| `region` | `us-central1` | GCP region (supports `me-central1`, `me-central2` for Middle East) |
| `environment` | `dev` | One of `dev`, `staging`, `prod` |
| `oracle_host` | *(required)* | Oracle EBS hostname / IP |
| `oracle_port` | `1521` | Oracle listener port |
| `oracle_schemas` | `["APPS","AR","AP","GL","INV","PO"]` | Schemas to replicate |

## Labels

Every resource is tagged with a consistent set of labels:

```hcl
project     = "oracleforge"
environment = var.environment   # dev / staging / prod
managed_by  = "terraform"
```

Additional labels can be supplied via the `labels` variable.

## Safety

- **BigQuery datasets** have `delete_contents_on_destroy = false` to prevent
  accidental data loss during `terraform destroy`.
- **GCS buckets** have versioning enabled and `force_destroy = false` by
  default.
- **IAM bindings** use `google_project_iam_member` (additive) instead of
  `google_project_iam_binding` (authoritative) to avoid removing existing
  permissions.
- **Firewall** includes an explicit deny-all-ingress rule at the lowest
  priority.

## Remote State

For team use, uncomment the `backend "gcs"` block in `main.tf` and configure a
GCS bucket for remote state storage:

```hcl
backend "gcs" {
  bucket = "oracleforge-tfstate"
  prefix = "landing-zone"
}
```

## Destroying

```bash
# Preview what will be destroyed
terraform plan -destroy

# Destroy (BigQuery datasets will NOT lose data due to safety flag)
terraform destroy
```
