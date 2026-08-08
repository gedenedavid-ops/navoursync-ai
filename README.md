# NavourSync AI

> *"Elegance under pressure. Deterministic compliance for enterprise cinema."*

[![License: MIT](https://img.shields.io/badge/License-MIT-white.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Gemini 2.5 Flash](https://img.shields.io/badge/Gemini-2.5%20Flash-orange.svg)](https://deepmind.google/technologies/gemini/)
[![Google ADK](https://img.shields.io/badge/Google%20ADK-2.6.1-4285F4.svg)](https://google.github.io/adk-docs/)
[![Agent Engine](https://img.shields.io/badge/Vertex%20AI-Agent%20Engine-34A853.svg)](https://cloud.google.com/vertex-ai/docs/agent-engine)
[![ClickHouse Partner](https://img.shields.io/badge/Partner-ClickHouse%20Cloud-FFDD57.svg)](https://clickhouse.com)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-red.svg)](https://streamlit.io)
[![Hackathon](https://img.shields.io/badge/Hackathon-Agentic%20Cinema%202026-blue.svg)](https://devpost.com)

---

## What is NavourSync AI?

NavourSync AI is an **autonomous multi-agent HR compliance system** for the film and media production industry, built natively on the **Google Agent Development Kit (ADK)** and **Vertex AI Agent Engine**.

It replaces the manual process of verifying crew dossiers — automatically classifying documents, extracting data via OCR, detecting fraud, dispatching professional notifications — all powered by **Gemini 2.5 Flash** and persisted in **ClickHouse Cloud** (official hackathon partner) for real-time analytics.

> Built for the **Agentic Cinema: The Blockbuster Hackathon** — submission deadline: September 7, 2026.

---

## The Problem

Every film production requires each crew member — actors, technicians, stunt performers — to submit a complete administrative dossier before legally working on set:

| Document | Compliance Check |
|---|---|
| 🪪 National ID / Passport | Must not be expired on the shooting date |
| 🏦 RIB / IBAN bank statement | Account holder name must exactly match the ID card |
| 📝 Image rights release | Must be signed and complete |
| ✍️ Handwritten employment request | Must be legible and fully filled |

Without automation, the production manager checks everything manually — a time-consuming, error-prone process exposed to payroll fraud. NavourSync AI automates the entire verification pipeline in **under 10 seconds per dossier**.

---

## Key Features

- 🤖 **Google ADK native** — agents declared with `google.adk.agents.Agent` + `FunctionTool`, orchestrated by a single `OrchestratorAgent`
- 🔍 **Multi-modal document classification** — identifies 7 document types with confidence score (00-VISION)
- 📄 **Structured OCR extraction** — extracts name, document number, expiry date, IBAN at temperature=0.0 (zero hallucination)
- 🚨 **Anti-fraud cross-check** — detects when RIB account holder ≠ crew member reference name
- 📅 **Expiry validation** — automatically flags IDs and passports expired before shoot date
- ✉️ **Automated HR notices** — 00-DISPATCH generates decision badge (VALIDATED / PENDING / BLOCKED), internal HR note, and ready-to-send email in EN + FR
- 📊 **Real-time analytics** — every audit persisted in **ClickHouse Cloud** and surfaced live on the dashboard
- 🗂️ **Multi-member batch** — upload a full crew roster, each member gets an independent parallel audit
- ✍️ **Handwritten transcription** — converts handwritten employment requests to typed text
- 🔁 **Exponential backoff retry** — auto-retries on Gemini 429 / 503 with 5s → 10s → 20s → 40s schedule

---

## Architecture — Google ADK Multi-Agent Network

```
[ JPG / PNG Documents ]
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│   ADK OrchestratorAgent — navoursync_orchestrator        │
│   google.adk.agents.Agent · gemini-2.5-flash             │
│                                                          │
│   FunctionTool: classify_document()                      │
│   FunctionTool: audit_document()                         │
│   FunctionTool: generate_crew_notice()                   │
└──────────────┬──────────────────────────────────────────┘
               │ tool calls
       ┌───────┼───────────────────┐
       ▼       ▼                   ▼
┌──────────┐ ┌──────────────┐ ┌──────────────┐
│ 00-VISION│ │ 00-AUDITOR   │ │ 00-DISPATCH  │
│ temp=0.1 │ │ temp=0.0     │ │ temp=0.2     │
│ Classify │ │ OCR + Fraud  │ │ HR Notice    │
└──────────┘ └──────┬───────┘ └──────────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  00-ANALYTICS       │
         │  ClickHouse Cloud   │  ← Official Hackathon Partner
         │  Real-time metrics  │
         └─────────────────────┘
```

| Agent | ADK Role | Model | Temperature |
|---|---|---|---|
| **00-VISION** | `FunctionTool: classify_document` | `gemini-2.5-flash` | 0.1 |
| **00-AUDITOR** | `FunctionTool: audit_document` | `gemini-2.5-flash` | 0.0 |
| **00-DISPATCH** | `FunctionTool: generate_crew_notice` | `gemini-2.5-flash` | 0.2 |
| **00-ANALYTICS** | Persistent store | ClickHouse Cloud | — |

### Why `temperature=0.0` on 00-AUDITOR?

HR data (names, document numbers, expiry dates) requires **zero creativity**. Temperature 0.0 forces Gemini to always pick the most probable token — fully deterministic, hallucination-free output for legal compliance data.

---

## Tech Stack

| Layer | Technology | Notes |
|---|---|---|
| **Agent Framework** | Google ADK (`google-cloud-aiplatform[adk]`) v2.6.1 | Native ADK — no wrapper libraries |
| **AI Model** | Gemini 2.5 Flash via `google-genai` SDK | Multimodal, structured JSON output |
| **Cloud Backend** | Google Cloud Vertex AI Agent Engine | Serverless agent hosting |
| **Partner Database** | **ClickHouse Cloud** (`clickhouse-connect`) | Real-time audit analytics |
| **Data Validation** | Pydantic v2 | Deterministic JSON schemas |
| **Dashboard UI** | Streamlit | Deployed on Streamlit Community Cloud |
| **Auth** | Vertex AI ADC / Service Account | Production-grade GCP auth |
| **Runtime** | Python 3.10+ | — |

---

## ClickHouse Cloud — Partner Integration

NavourSync AI uses **ClickHouse Cloud** as the real-time analytics backend — an official partner of this hackathon.

Every document audit is immediately inserted into ClickHouse via `clickhouse-connect`:

```python
db_manager.log_audit(
    doc_type=doc_type.value,
    confidence=confidence,
    full_name=full_name,
    doc_num=doc_num,
    is_expired=audit.id_data.is_expired,
    mismatch=audit.name_mismatch_detected,
    score=audit.compliance_score,
    notes=audit.audit_notes,
)
```

The dashboard surfaces **4 live ClickHouse metrics** updated on every audit run:

| Metric | ClickHouse Query |
|---|---|
| Total processed | `count()` |
| Avg compliance | `round(avg(compliance_score), 3)` |
| Expired IDs | `countIf(is_expired = 1)` |
| RIB fraud alerts | `countIf(name_mismatch = 1)` |

---

## Dashboard Preview

James Bond 007 dark theme — obsidian black `#0A0A0B`, pure white titles, MI6 red `#E50914` for alerts.

| Screen | Description |
|---|---|
| **Studio Control Center** | 4 live ClickHouse metrics |
| **Crew Roster** | Dynamic multi-member form — add N crew members, each with 4 document slots |
| **Production Report** | Per-member compliance badge + ADK decision (VALIDATED / PENDING / BLOCKED) + HR note + email EN/FR |

---

## Project Structure

```
navoursync-ai/
├── app.py                    # Streamlit Cloud entrypoint
├── src/
│   ├── agents/
│   │   ├── adk_pipeline.py   # ← ADK OrchestratorAgent + 3 FunctionTools
│   │   ├── classifier.py     # 00-VISION — VisionClassifierAgent
│   │   ├── auditor.py        # 00-AUDITOR — AuditorAgent (temp=0.0)
│   │   └── dispatcher.py     # 00-DISPATCH — DispatcherAgent
│   ├── db/
│   │   └── client.py         # ClickHouseManager — log_audit, get_compliance_stats
│   ├── utils/
│   │   ├── gemini_client.py  # Vertex AI / API key factory
│   │   └── retry.py          # Exponential backoff on 429/503
│   ├── schemas.py            # Unified Pydantic exports
│   ├── app.py                # Streamlit production dashboard
│   └── main.py               # CLI pipeline runner
├── tests/
│   └── validate_mock.py      # Schema validation without API calls
└── requirements.txt
```

---

## Installation

```bash
git clone https://github.com/gedenedavid-ops/navoursync-ai.git
cd navoursync-ai
pip install -r requirements.txt
```

### Option A — Vertex AI (recommended, uses GCP credits)

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project gen-lang-client-0731365913
```

```env
USE_VERTEX_AI=true
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_CLOUD_LOCATION=us-central1
```

### Option B — API key (Google AI Studio)

```env
USE_VERTEX_AI=false
GEMINI_API_KEY=AIzaSy...
```

### ClickHouse credentials

```env
CLICKHOUSE_HOST=your_instance.clickhouse.cloud
CLICKHOUSE_PORT=8443
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=your_password
```

---

## Run

```bash
# Dashboard
python -m streamlit run src/app.py

# CLI pipeline
python -m src.main

# ADK pipeline direct
python -c "
from src.agents.adk_pipeline import run_pipeline
print(run_pipeline('Audit file data/samples/id.jpg for crew member KOUAKOU DAVID'))
"

# Schema validation (no API required)
python -m tests.validate_mock
```

---

## Hackathon Roadmap

| Week | Deliverables | Status |
|---|---|---|
| **Week 1** — Architecture & Core Agents | ADK agents, Pydantic schemas | ✅ Done |
| **Week 2** — ClickHouse Integration | Real-time audit persistence | ✅ Done |
| **Week 3** — Production Dashboard | Streamlit UI, Vertex AI auth | ✅ Done |
| **Week 4** — Demo Trailer | 3-min video, ElevenLabs voiceover | 🔲 In progress |
| **Week 5** — Devpost Submission | README, video link, live demo | 🔲 Upcoming |

**Deadline: September 7, 2026 @ 10:00 AM GMT-11**

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  Built with&nbsp;
  <a href="https://deepmind.google/technologies/gemini/">Google Gemini 2.5</a> ·
  <a href="https://google.github.io/adk-docs/">Google ADK</a> ·
  <a href="https://clickhouse.com">ClickHouse Cloud</a> ·
  <a href="https://streamlit.io">Streamlit</a> ·
  <a href="https://pydantic.dev">Pydantic v2</a>
</p>
