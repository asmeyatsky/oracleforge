# ---------------------------------------------------------------------------
# Networking Module — VPC, Subnets, PSC, Firewall Rules
# ---------------------------------------------------------------------------

# ── VPC ─────────────────────────────────────────────────────────────────────

resource "google_compute_network" "vpc" {
  project                 = var.project_id
  name                    = "oracleforge-vpc-${var.environment}"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
  description             = "OracleForge VPC for ${var.environment} environment."
}

# ── Primary Subnet ──────────────────────────────────────────────────────────

resource "google_compute_subnetwork" "main" {
  project                  = var.project_id
  name                     = "oracleforge-subnet-${var.environment}"
  region                   = var.region
  network                  = google_compute_network.vpc.id
  ip_cidr_range            = var.subnet_cidr
  private_ip_google_access = true

  log_config {
    aggregation_interval = "INTERVAL_5_SEC"
    flow_sampling        = 0.5
    metadata             = "INCLUDE_ALL_METADATA"
  }
}

# ── Private Services Access (for AlloyDB, Cloud SQL, etc.) ──────────────────

resource "google_compute_global_address" "private_services_range" {
  project       = var.project_id
  name          = "oracleforge-psa-range-${var.environment}"
  purpose       = "VPC_PEERING"
  address_type  = "INTERNAL"
  prefix_length = split("/", var.psc_cidr)[1]
  address       = split("/", var.psc_cidr)[0]
  network       = google_compute_network.vpc.id
}

resource "google_service_networking_connection" "private_services" {
  network                 = google_compute_network.vpc.id
  service                 = "servicenetworking.googleapis.com"
  reserved_peering_ranges = [google_compute_global_address.private_services_range.name]
}

# ── Datastream Private Connection ───────────────────────────────────────────

resource "google_datastream_private_connection" "datastream" {
  project               = var.project_id
  location              = var.region
  display_name          = "oracleforge-datastream-pc-${var.environment}"
  private_connection_id = "oracleforge-ds-pc-${var.environment}"

  vpc_peering_config {
    vpc    = google_compute_network.vpc.id
    subnet = "10.1.0.0/29"
  }

  labels = var.labels
}

# ── Firewall Rules ──────────────────────────────────────────────────────────

# Allow internal communication within the VPC
resource "google_compute_firewall" "allow_internal" {
  project = var.project_id
  name    = "oracleforge-allow-internal-${var.environment}"
  network = google_compute_network.vpc.id

  direction = "INGRESS"
  priority  = 1000

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = [var.subnet_cidr]
  description   = "Allow all internal traffic within the OracleForge subnet."
}

# Allow Oracle database port from Datastream peered network
resource "google_compute_firewall" "allow_oracle_from_datastream" {
  project = var.project_id
  name    = "oracleforge-allow-oracle-ds-${var.environment}"
  network = google_compute_network.vpc.id

  direction = "INGRESS"
  priority  = 900

  allow {
    protocol = "tcp"
    ports    = ["1521", "1522"]
  }

  source_ranges = ["10.1.0.0/29"]
  description   = "Allow Datastream peered network to reach Oracle listener."
}

# Allow IAP for SSH (for troubleshooting VMs if any)
resource "google_compute_firewall" "allow_iap_ssh" {
  project = var.project_id
  name    = "oracleforge-allow-iap-ssh-${var.environment}"
  network = google_compute_network.vpc.id

  direction = "INGRESS"
  priority  = 1000

  allow {
    protocol = "tcp"
    ports    = ["22"]
  }

  # IAP forwarding range
  source_ranges = ["35.235.240.0/20"]
  description   = "Allow SSH via Identity-Aware Proxy."
}

# Deny all other ingress (explicit default-deny)
resource "google_compute_firewall" "deny_all_ingress" {
  project = var.project_id
  name    = "oracleforge-deny-all-ingress-${var.environment}"
  network = google_compute_network.vpc.id

  direction = "INGRESS"
  priority  = 65534

  deny {
    protocol = "all"
  }

  source_ranges = ["0.0.0.0/0"]
  description   = "Default deny all ingress traffic."
}
