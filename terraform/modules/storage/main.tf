# ---------------------------------------------------------------------------
# Cloud Storage Module — Raw, Staging, and Archive Buckets
# ---------------------------------------------------------------------------

# ── Raw Exports Bucket ──────────────────────────────────────────────────────

resource "google_storage_bucket" "raw" {
  project  = var.project_id
  name     = "${var.project_id}-oracleforge-raw-${var.environment}"
  location = var.region

  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  force_destroy               = var.force_destroy

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = var.archive_age_days
    }
    action {
      type          = "SetStorageClass"
      storage_class = "ARCHIVE"
    }
  }

  lifecycle_rule {
    condition {
      age = var.delete_age_days
    }
    action {
      type = "Delete"
    }
  }

  labels = merge(var.labels, { bucket_purpose = "raw-exports" })
}

# ── Staging Bucket ──────────────────────────────────────────────────────────

resource "google_storage_bucket" "staging" {
  project  = var.project_id
  name     = "${var.project_id}-oracleforge-staging-${var.environment}"
  location = var.region

  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  force_destroy               = var.force_destroy

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = var.archive_age_days
    }
    action {
      type          = "SetStorageClass"
      storage_class = "ARCHIVE"
    }
  }

  lifecycle_rule {
    condition {
      age = var.delete_age_days
    }
    action {
      type = "Delete"
    }
  }

  labels = merge(var.labels, { bucket_purpose = "staging" })
}

# ── Archive Bucket ──────────────────────────────────────────────────────────

resource "google_storage_bucket" "archive" {
  project  = var.project_id
  name     = "${var.project_id}-oracleforge-archive-${var.environment}"
  location = var.region

  storage_class               = "ARCHIVE"
  uniform_bucket_level_access = true
  force_destroy               = var.force_destroy

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = var.delete_age_days
    }
    action {
      type = "Delete"
    }
  }

  labels = merge(var.labels, { bucket_purpose = "archive" })
}

# ── IAM: Grant pipeline SA object-admin on raw & staging ───────────────────

resource "google_storage_bucket_iam_member" "pipeline_raw" {
  bucket = google_storage_bucket.raw.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.pipeline_sa_email}"
}

resource "google_storage_bucket_iam_member" "pipeline_staging" {
  bucket = google_storage_bucket.staging.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.pipeline_sa_email}"
}

resource "google_storage_bucket_iam_member" "pipeline_archive" {
  bucket = google_storage_bucket.archive.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${var.pipeline_sa_email}"
}
