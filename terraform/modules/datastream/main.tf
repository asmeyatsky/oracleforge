# ---------------------------------------------------------------------------
# Datastream Module — Oracle CDC → BigQuery
# ---------------------------------------------------------------------------
# Creates connection profiles for the Oracle source and BigQuery destination,
# then wires them together with a Datastream stream configured for CDC.
# ---------------------------------------------------------------------------

# ── Oracle Source Connection Profile ────────────────────────────────────────

resource "google_datastream_connection_profile" "oracle_source" {
  project               = var.project_id
  location              = var.region
  display_name          = "oracleforge-oracle-source-${var.environment}"
  connection_profile_id = "oracleforge-oracle-src-${var.environment}"

  oracle_profile {
    hostname = var.oracle_host
    port     = var.oracle_port
    username = var.oracle_username
    password = var.oracle_password
    database_service = var.oracle_database
  }

  private_connectivity {
    private_connection = var.private_connection_id
  }

  labels = var.labels
}

# ── BigQuery Destination Connection Profile ────────────────────────────────

resource "google_datastream_connection_profile" "bigquery_dest" {
  project               = var.project_id
  location              = var.region
  display_name          = "oracleforge-bigquery-dest-${var.environment}"
  connection_profile_id = "oracleforge-bq-dest-${var.environment}"

  bigquery_profile {}

  labels = var.labels
}

# ── Datastream Stream (Oracle → BigQuery CDC) ──────────────────────────────

resource "google_datastream_stream" "oracle_to_bigquery" {
  project     = var.project_id
  location    = var.region
  display_name = "oracleforge-cdc-${var.environment}"
  stream_id    = "oracleforge-cdc-${var.environment}"

  desired_state = "NOT_STARTED"

  source_config {
    source_connection_profile = google_datastream_connection_profile.oracle_source.id

    oracle_source_config {
      max_concurrent_cdc_tasks  = 5
      max_concurrent_backfill_tasks = 2

      dynamic "include_objects" {
        for_each = [1] # single block
        content {
          dynamic "oracle_schemas" {
            for_each = var.oracle_schemas
            content {
              schema = oracle_schemas.value
            }
          }
        }
      }
    }
  }

  destination_config {
    destination_connection_profile = google_datastream_connection_profile.bigquery_dest.id

    bigquery_destination_config {
      data_freshness = "900s"

      single_target_dataset {
        dataset_id = "${var.project_id}:${var.bronze_dataset_id}"
      }
    }
  }

  backfill_all {}

  labels = var.labels
}
