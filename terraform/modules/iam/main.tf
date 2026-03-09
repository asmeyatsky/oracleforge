# ---------------------------------------------------------------------------
# IAM Module — Service Accounts and Project-Level IAM Bindings
# ---------------------------------------------------------------------------

# ── Service Accounts ────────────────────────────────────────────────────────

resource "google_service_account" "pipeline" {
  project      = var.project_id
  account_id   = "oracleforge-pipeline-${var.environment}"
  display_name = "OracleForge Pipeline (${var.environment})"
  description  = "Runs OracleForge data pipelines — BigQuery Data Editor and GCS Object Admin."
}

resource "google_service_account" "datastream" {
  project      = var.project_id
  account_id   = "oracleforge-datastream-${var.environment}"
  display_name = "OracleForge Datastream (${var.environment})"
  description  = "Manages Google Cloud Datastream resources for Oracle CDC replication."
}

resource "google_service_account" "viewer" {
  project      = var.project_id
  account_id   = "oracleforge-viewer-${var.environment}"
  display_name = "OracleForge Viewer (${var.environment})"
  description  = "Read-only access to OracleForge BigQuery datasets."
}

# ── Project-Level IAM Bindings ──────────────────────────────────────────────
#
# NOTE: google_project_iam_member is additive — it will NOT remove existing
# bindings.  This is the safest approach for shared projects.

# Pipeline SA → BigQuery Data Editor
resource "google_project_iam_member" "pipeline_bq_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.pipeline.email}"
}

# Pipeline SA → BigQuery Job User (needed to run queries / loads)
resource "google_project_iam_member" "pipeline_bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.pipeline.email}"
}

# Pipeline SA → Storage Object Admin
resource "google_project_iam_member" "pipeline_gcs_admin" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.pipeline.email}"
}

# Datastream SA → Datastream Admin
resource "google_project_iam_member" "datastream_admin" {
  project = var.project_id
  role    = "roles/datastream.admin"
  member  = "serviceAccount:${google_service_account.datastream.email}"
}

# Datastream SA → BigQuery Data Editor (writes CDC rows into bronze)
resource "google_project_iam_member" "datastream_bq_editor" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.datastream.email}"
}

# Viewer SA → BigQuery Data Viewer
resource "google_project_iam_member" "viewer_bq_viewer" {
  project = var.project_id
  role    = "roles/bigquery.dataViewer"
  member  = "serviceAccount:${google_service_account.viewer.email}"
}

# Viewer SA → BigQuery Job User (needed to run queries)
resource "google_project_iam_member" "viewer_bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.viewer.email}"
}
