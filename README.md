# OracleForge: Oracle EBS to GCP Modernization Accelerator

OracleForge is a high-performance modernization accelerator designed to automate the transition from on-premise Oracle E-Business Suite (EBS) or Fusion Cloud environments to a modern medallion architecture on Google Cloud Platform.

Built with **Hexagonal Architecture (Ports & Adapters)**, it ensures a modular, testable, and future-proof codebase as per the `skill2026.md` architectural mandates.

---

## 🚀 Key Features

### 🧠 Schema Intelligence Engine (SIE) - MCP Native
- **Table Classification**: Automated classification of EBS tables into GL, AP, and HCM modules.
- **Relationship Mapping**: Discovery of FK and implicit join relationships.
- **Flexfield Analysis**: Automated enumeration and mapping of Key Flexfields (KFF) and Descriptive Flexfields (DFF).
- **MCP Server**: Integrated Model Context Protocol (MCP) server for tool-based schema interrogation.

### 🌊 Automated Migration & CDC
- **Medallion Pipeline**: Orchestrated Extract-Load-Transform (ELT) from Oracle to BigQuery (Bronze/Silver/Gold layers).
- **CDC Orchestration**: Built-in support for Google Cloud Datastream to manage real-time change data capture.
- **Reconciliation & Certification**: Automated data validation and issuance of cryptographic migration certificates.

### 🛡️ Saudi PDPL & NDMO Compliance
- **PII Masking**: Automated detection and masking of sensitive data (Email, National ID, etc.).
- **Compliance Reporting**: Generation of audit-ready reports for SAMA, NDMO, and PDPL standards.
- **Region-specific Terraform**: Secure landing zone provisioning for `me-central2` (Dammam) and `me-west1` (Doha).

### 🤖 Agentic Finance Workflows (Vertex AI)
- **Scout Agent**: Interrogates Oracle schemas for undocumented customizations.
- **Architect Agent**: Proposes canonical BigQuery target schemas and partitioning.
- **Validator Agent**: Tests mappings with sample data to ensure type compatibility.
- **Documenter Agent**: Automatically updates Dataplex catalog and lineage documentation.

---

## 🛠️ Usage

### CLI Commands
OracleForge provides a rich CLI interface powered by `Typer` and `Rich`.

```bash
# Project Status
oracleforge status

# Schema Analysis
oracleforge sie classify --pattern "GL_%"
oracleforge sie flexfields GL_CODE_COMBINATIONS

# Migration
oracleforge migrate run GL --period "Jan-26" --org-id 101

# CDC Management
oracleforge cdc list
oracleforge cdc create GL

# Compliance
oracleforge compliance scan AP_INVOICES_ALL
oracleforge compliance report PDPL

# Multi-Agent Orchestration
oracleforge agents run AP --table AP_INVOICES_ALL

# Architectural Fitness Check
oracleforge fitness check
```

### Installation
```bash
pip install -e .
```

---

## ✅ Validation & Testing

Run the integration health check to verify connectivity to Oracle and GCP:

```bash
python tests/integration_test.py
```

To run the full test suite:
```bash
pytest tests/
```

---

*OracleForge v1.0 — Empowering seamless Oracle to GCP modernizations.*
