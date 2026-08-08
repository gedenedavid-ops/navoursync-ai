"""
NavourSync AI — ADK Native Pipeline
====================================
Wraps the three existing agents (00-VISION, 00-AUDITOR, 00-DISPATCH) as
Google ADK FunctionTools and exposes a single OrchestratorAgent that the
Streamlit UI and Agent Engine can invoke.

Architecture:
    Runner (ADK)
      └── orchestrator_agent  (google.adk.agents.Agent)
            ├── tool: classify_document      → VisionClassifierAgent
            ├── tool: audit_document         → AuditorAgent
            └── tool: generate_crew_notice   → DispatcherAgent
"""

from __future__ import annotations

import os
import json
import tempfile
import base64
from typing import Optional

from google.adk.agents import Agent
from google.adk.tools import FunctionTool
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from src.agents.classifier import VisionClassifierAgent, DocumentType
from src.agents.auditor import AuditorAgent
from src.agents.dispatcher import DispatcherAgent

# ─────────────────────────────────────────────────────────────────────────────
# Lazy singletons — created once, reused across calls
# ─────────────────────────────────────────────────────────────────────────────
_vision: Optional[VisionClassifierAgent] = None
_auditor: Optional[AuditorAgent] = None
_dispatcher: Optional[DispatcherAgent] = None


def _get_agents():
    global _vision, _auditor, _dispatcher
    if _vision is None:
        _vision     = VisionClassifierAgent()
        _auditor    = AuditorAgent()
        _dispatcher = DispatcherAgent()
    return _vision, _auditor, _dispatcher


# ─────────────────────────────────────────────────────────────────────────────
# Tool 1 — 00-VISION : classify a document from a local file path
# ─────────────────────────────────────────────────────────────────────────────
def classify_document(file_path: str) -> dict:
    """
    Classify a document image using the 00-VISION agent.

    Args:
        file_path: Absolute or relative path to a JPG/PNG image file.

    Returns:
        A dict with keys: document_type, confidence, detected_language, reasoning.
    """
    vision, _, _ = _get_agents()
    result = vision.classify(file_path)
    return result.model_dump()


# ─────────────────────────────────────────────────────────────────────────────
# Tool 2 — 00-AUDITOR : audit a document given its type and reference name
# ─────────────────────────────────────────────────────────────────────────────
def audit_document(file_path: str, document_type: str, reference_name: str = "") -> dict:
    """
    Perform a full compliance audit on a document using the 00-AUDITOR agent.

    Args:
        file_path:      Path to the JPG/PNG image file.
        document_type:  The document type string (e.g. 'cni_passport', 'rib_iban').
        reference_name: Full name of the crew member to cross-check against.

    Returns:
        A dict with keys: id_data, bank_data, transcribed_text,
        name_mismatch_detected, compliance_score, audit_notes.
    """
    _, auditor, _ = _get_agents()
    try:
        doc_type = DocumentType(document_type)
    except ValueError:
        doc_type = DocumentType.UNKNOWN
    result = auditor.audit(file_path, doc_type, reference_name=reference_name or None)
    return result.model_dump()


# ─────────────────────────────────────────────────────────────────────────────
# Tool 3 — 00-DISPATCH : generate a global compliance notice for a crew member
# ─────────────────────────────────────────────────────────────────────────────
def generate_crew_notice(
    audits_json: str,
    reference_name: str,
    production_title: str = "PRODUCTION",
) -> dict:
    """
    Generate a global HR compliance notice for one crew member covering all
    their documents, using the 00-DISPATCH agent.

    Args:
        audits_json:      JSON string — list of audit dicts, each with keys:
                          filename (str), doc_type (str), audit (dict).
        reference_name:   Full name of the crew member.
        production_title: Name of the film production.

    Returns:
        A dict with keys: recipient_name, requires_action, issues_found,
        decision, hr_note, email_subject, message_body, message_body_fr.
    """
    _, _, dispatcher = _get_agents()
    audits = json.loads(audits_json)
    # Re-hydrate audit dicts into AuditResult objects
    from src.agents.auditor import AuditResult
    hydrated = [
        {
            "filename": a["filename"],
            "doc_type": a["doc_type"],
            "audit":    AuditResult.model_validate(a["audit"]),
        }
        for a in audits
    ]
    result = dispatcher.generate_global_notice(
        audits=hydrated,
        reference_name=reference_name,
        production_title=production_title,
    )
    return result.model_dump()


# ─────────────────────────────────────────────────────────────────────────────
# ADK Agent — Orchestrator wrapping the 3 tools above
# ─────────────────────────────────────────────────────────────────────────────
ORCHESTRATOR_INSTRUCTION = """
You are the NavourSync AI Orchestrator for film production HR compliance.

Your role is to coordinate three specialized sub-agents to process a crew
member's administrative dossier:

1. Call classify_document(file_path) to identify each document type.
2. Call audit_document(file_path, document_type, reference_name) to extract
   structured data and verify compliance for each document.
3. Once all documents are audited, call generate_crew_notice(audits_json,
   reference_name, production_title) to produce the final HR notice.

Always process documents in order: classify → audit → notify.
Be deterministic and factual. Do not invent document data.
"""

orchestrator_agent = Agent(
    name="navoursync_orchestrator",
    model="gemini-2.5-flash",
    description=(
        "NavourSync AI multi-agent orchestrator for film crew HR compliance. "
        "Chains 00-VISION (classification), 00-AUDITOR (OCR + compliance), "
        "and 00-DISPATCH (notification) to process full crew dossiers."
    ),
    instruction=ORCHESTRATOR_INSTRUCTION,
    tools=[
        FunctionTool(classify_document),
        FunctionTool(audit_document),
        FunctionTool(generate_crew_notice),
    ],
)

# ─────────────────────────────────────────────────────────────────────────────
# Runner — for direct invocation (CLI / tests)
# ─────────────────────────────────────────────────────────────────────────────
APP_NAME    = "navoursync_ai"
USER_ID     = "hr_system"


def run_pipeline(message: str, session_id: str = "default") -> str:
    """
    Run the ADK orchestrator with a plain-text message.
    Returns the final text response from the agent.

    Example:
        run_pipeline("Process file data/samples/id.jpg for crew member KOUAKOU DAVID")
    """
    session_service = InMemorySessionService()
    session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
    )

    runner = Runner(
        agent=orchestrator_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    content = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=message)],
    )

    final_response = ""
    for event in runner.run(
        user_id=USER_ID,
        session_id=session_id,
        new_message=content,
    ):
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if part.text:
                    final_response += part.text

    return final_response
