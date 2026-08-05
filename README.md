# NavourSync AI

> *"Elegance under pressure. Deterministic compliance for enterprise cinema."*

[![License: MIT](https://img.shields.io/badge/License-MIT-white.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Powered by Gemini](https://img.shields.io/badge/Powered%20by-Gemini%202.5-orange.svg)](https://deepmind.google/technologies/gemini/)
[![ClickHouse](https://img.shields.io/badge/Database-ClickHouse-yellow.svg)](https://clickhouse.com)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-red.svg)](https://streamlit.io)
[![Hackathon](https://img.shields.io/badge/Hackathon-Google%20×%20ClickHouse%202026-blue.svg)](https://devpost.com)

---

## What is NavourSync AI?

NavourSync AI is an **autonomous multi-agent HR compliance system** for the film and media production industry. It replaces the manual process of verifying crew dossiers by automatically classifying documents, extracting data via OCR, detecting fraud, and dispatching professional notifications — all powered by **Google Gemini 2.5** and persisted in **ClickHouse Cloud** for real-time analytics.

> Think of it as a tireless HR officer that processes any crew document in under 10 seconds, detects expired IDs, catches bank fraud attempts, and sends the right email automatically.

Built for the **Agentic Cinema: The Blockbuster Hackathon** — submission deadline: September 7, 2026.

---

## The Problem

Every film production requires each crew member (actors, technicians, stunt performers) to submit a complete administrative dossier before they can legally work on set:

| Document | Compliance Check |
|---|---|
| 🪪 National ID / Passport | Must not be expired on the shooting date |
| 🏦 RIB / IBAN bank statement | Account holder name must exactly match the ID card |
| 📝 Image rights release | Must be signed |
| ✍️ Handwritten employment request | Must be legible and complete |

Without automation, the production manager checks everything manually — a time-consuming, error-prone process exposed to payroll fraud. NavourSync AI automates the entire verification pipeline.

---

## Key Features

- 🔍 **Multi-modal document classification** — identifies 7 document types from a photo with confidence score
- 📄 **Structured OCR extraction** — extracts name, document number, expiry date, IBAN with zero hallucination (temperature=0.0)
- 🚨 **Anti-fraud cross-check** — instantly detects when the RIB account holder ≠ the crew member on file
- 📅 **Expiry validation** — automatically flags IDs and passports expired before the shoot date
- ✉️ **Automated notifications** — 00-DISPATCH generates a ready-to-send professional email for every anomaly
- 📊 **Real-time analytics** — every audit is persisted in ClickHouse Cloud and surfaced on the dashboard
- 🗂️ **Batch processing** — drop an entire dossier (CNI + RIB + contract) in one go and audit all files at once
- ✍️ **Handwritten transcription** — converts handwritten employment requests to typed text

---

## Architecture — 4 Autonomous Gemini Agents

```
[ Document: JPG / PNG ]
           │
           ▼
┌─────────────────────────────────┐
│   AGENT 1 : 00-VISION           │  gemini-2.5-flash · temp=0.1
│   Multi-modal Classifier        │  Identifies document type + confidence score
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│   AGENT 2 : 00-AUDITOR          │  gemini-2.5-flash · temp=0.0
│   OCR & Compliance Engine       │  Extracts fields, checks expiry, cross-checks names
└────────────────┬────────────────┘
                 │
       ┌─────────┴──────────┐
       ▼                    ▼
  [Anomaly]            [Compliant]
       │                    │
       ▼                    ▼
┌─────────────────┐  ┌──────────────────────┐
│  AGENT 3        │  │  AGENT 4             │
│  00-DISPATCH    │  │  00-ANALYTICS        │
│  Notifications  │  │  ClickHouse Pipeline │
└─────────────────┘  └──────────────────────┘
```

| Agent | Model | Role |
|---|---|---|
| **00-VISION** | `gemini-2.5-flash` | Classifies documents into 7 categories with a confidence score |
| **00-AUDITOR** | `gemini-2.5-flash` | Deterministic OCR, expiry check, anti-fraud name cross-check |
| **00-DISPATCH** | `gemini-2.5-flash` | Generates professional email for anomalies or validation confirmation |
| **00-ANALYTICS** | ClickHouse | Persists all audit results for real-time compliance dashboards |

### Why `temperature=0.0` on 00-AUDITOR?

HR data (names, document numbers, expiry dates) requires **zero creativity**. Setting temperature to 0.0 forces Gemini to always pick the most probable token — fully deterministic output. Any "creativity" on an ID number would be a hallucination.

---

## Tech Stack

| Layer | Technology | Version |
|---|---|---|
| AI Agents | `google-genai` SDK — Gemini 2.5 Flash | 2.16.0 |
| Cloud Orchestration | Google Cloud Vertex AI Agent Engine | — |
| Data Validation | Pydantic v2 — deterministic JSON schemas | 2.12.5 |
| Analytics Database | ClickHouse Cloud (`clickhouse-connect`) | 1.6.0 |
| Dashboard UI | Streamlit | 1.60.0 |
| Runtime | Python 3.10+ | — |

---

## Dashboard Preview

The dashboard runs on a **James Bond 007 dark theme** — obsidian black `#0A0A0B`, pure white titles, MI6 red `#E50914` for alerts.

**3 screens in one interface:**

| Screen | Description |
|---|---|
| **Studio Control Center** | 4 live ClickHouse metrics: documents processed, average compliance, expired IDs, RIB fraud alerts |
| **Live Dropzone** | Drag & drop one or multiple files — agents execute and log in real time |
| **Audit Report** | Color-coded expandable panels per file (🔴 anomaly auto-expanded, 🟢 compliant collapsed) |

---

## Project Structure

```
navoursync-ai/
├── src/
│   ├── agents/
│   │   ├── classifier.py     # Agent 00-VISION — VisionClassifierAgent
│   │   ├── auditor.py        # Agent 00-AUDITOR — AuditorAgent + Pydantic models
│   │   └── dispatcher.py     # Agent 00-DISPATCH — DispatcherAgent
│   ├── db/
│   │   └── client.py         # ClickHouseManager — connect, log_audit, get_compliance_stats
│   ├── schemas.py            # Unified Pydantic model exports
│   ├── app.py                # Streamlit production dashboard
│   └── main.py               # CLI pipeline runner
├── data/
│   └── samples/              # Local test documents (gitignored)
├── tests/
│   └── validate_mock.py      # Schema validation without API calls
├── .env                      # API credentials — never commit
├── requirements.txt
└── README.md
```

---

## Installation

**1. Clone the repository**
```bash
git clone https://github.com/your-username/navoursync-ai.git
cd navoursync-ai
```

**2. Create and activate a virtual environment**
```bash
python -m venv venv
source venv/bin/activate      # macOS / Linux
venv\Scripts\activate         # Windows
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Configure environment variables**

Create a `.env` file at the project root:
```env
# Gemini API — https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# ClickHouse Cloud
CLICKHOUSE_HOST=your_instance.clickhouse.cloud
CLICKHOUSE_PORT=8443
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=your_password
CLICKHOUSE_DB=default
```

**5. Verify ClickHouse connection**
```bash
python -c "
from dotenv import load_dotenv; load_dotenv()
from src.db.client import ClickHouseManager
db = ClickHouseManager(); db.connect()
"
```

Expected output:
```
[ClickHouse] Connexion etablie avec succes.
[ClickHouse] Table document_audits prete.
```

---

## Run the Dashboard

```bash
python -m streamlit run src/app.py
```

Open **http://localhost:8501** in your browser.

### How to use

1. **Sidebar** — Enter the production name and the crew member's full reference name (exactly as it appears on their ID card)
2. **Dropzone** — Upload one or more documents (JPG/PNG): ID card, RIB, contract, image rights form
3. **Click RUN COMPLIANCE AUDIT** — the 3 Gemini agents execute sequentially per file, with live logs
4. **Read the report** — each file gets a color-coded expandable panel:
   - 🔴 **Red** (auto-expanded) — anomaly detected: expired ID, name mismatch, or other issue
   - 🟢 **Green** — fully compliant, cleared for the shoot
5. **00-DISPATCH notification** — a ready-to-send professional email is generated at the bottom of each anomaly panel

### What gets detected

| Check | Trigger | Output |
|---|---|---|
| Document type | Any uploaded file | Category + confidence % |
| Expired document | Expiry date < today | `⚠ EXPIRED DOCUMENT` in red |
| RIB name mismatch | RIB holder ≠ reference name | `⚠ RIB NAME ... DOES NOT MATCH` in red |
| Handwritten text | Handwritten request detected | Full transcription in text block |
| Low compliance | Any anomaly combination | Score below 100% + dispatch email |

---

## Run the CLI Pipeline

```bash
python -m src.main
```

---

## Run Schema Validation

```bash
python -m tests.validate_mock
```

---

## ClickHouse Schema

```sql
CREATE TABLE IF NOT EXISTS document_audits (
    audit_id         UUID     DEFAULT generateUUIDv4(),
    timestamp        DateTime DEFAULT now(),
    document_type    String,           -- 'cni_passport', 'rib_iban', 'contract'…
    confidence       Float32,          -- 00-VISION confidence score (0.0–1.0)
    full_name        String,           -- Extracted by 00-AUDITOR
    document_number  String,           -- ID number or IBAN
    is_expired       UInt8,            -- 1 = expired, 0 = valid
    name_mismatch    UInt8,            -- 1 = fraud alert, 0 = OK
    compliance_score Float32,          -- 00-AUDITOR overall score (0.0–1.0)
    audit_notes      String            -- Human-readable audit summary
) ENGINE = MergeTree()
ORDER BY (timestamp, document_type);
```

---

## Hackathon Roadmap

| Week | Dates | Status |
|---|---|---|
| **Week 1** — Architecture & Core Agents | Aug 1–7 | ✅ Done |
| **Week 2** — ClickHouse Integration | Aug 8–14 | ✅ Done |
| **Week 3** — Production Dashboard | Aug 15–22 | ✅ Done |
| **Week 4** — Demo Trailer (3 min video) | Aug 23–31 | 🔲 Upcoming |
| **Week 5** — Devpost Submission | Sep 1–7 | 🔲 Upcoming |

**Deadline: September 7, 2026 @ 10:00 AM GMT-11**

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <sub>Built with Google Gemini · ClickHouse · Streamlit · Pydantic · Python</sub>
</p>
