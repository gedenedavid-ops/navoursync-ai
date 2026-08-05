import os
from typing import List
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from src.agents.auditor import AuditResult
from src.agents.classifier import DocumentType


# 1. Schéma de sortie pour le message de relance
class DispatchNotice(BaseModel):
    recipient_name: str = Field(description="Full name of the crew member")
    requires_action: bool = Field(description="True if action is required from the crew member")
    issues_found: List[str] = Field(description="Exhaustive list of all issues detected across all documents")
    email_subject: str = Field(description="Professional email subject line")
    message_body: str = Field(description="Full professional email body covering all documents in the dossier")


class DispatcherAgent:
    def __init__(self, api_key: str = None):
        self.client = genai.Client(api_key=api_key or os.getenv("GEMINI_API_KEY"))
        self.model = "gemini-2.5-flash"

    def generate_notice(
        self,
        audit: AuditResult,
        doc_type: DocumentType,
        reference_name: str,
    ) -> DispatchNotice:
        """Génère un avis pour un seul document (gardé pour compatibilité CLI)."""

        prompt = f"""
        You are the '00-DISPATCH' agent of NavourSync AI for a film production.
        Review the audit result below for crew member: {reference_name}.

        Audit Result:
        - Document type    : {doc_type.value}
        - Compliance score : {audit.compliance_score}
        - Name mismatch    : {audit.name_mismatch_detected}
        - Audit notes      : {audit.audit_notes}

        If anomalies exist (score < 1.0, expired document, or name mismatch),
        generate a clear, polite but firm reminder to submit the correct document.
        If fully compliant, generate a validation confirmation message.
        """

        response = self.client.models.generate_content(
            model=self.model,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=DispatchNotice,
                temperature=0.2,
            ),
        )

        return DispatchNotice.model_validate_json(response.text)

    def generate_global_notice(
        self,
        audits: List[dict],
        reference_name: str,
        production_title: str,
    ) -> DispatchNotice:
        """Génère UNE SEULE notification globale couvrant l'intégralité du dossier.

        audits: liste de dicts {"filename": str, "doc_type": str, "audit": AuditResult}
        """

        # Construit un résumé structuré de tous les documents
        docs_summary = ""
        for i, item in enumerate(audits, 1):
            a = item["audit"]
            anomaly = a.name_mismatch_detected or (a.id_data and a.id_data.is_expired)
            docs_summary += f"""
  Document {i} — {item['filename']} ({item['doc_type']}):
    - Compliance score : {a.compliance_score * 100:.0f}%
    - Status           : {'⚠ ANOMALY' if anomaly else '✓ COMPLIANT'}
    - Notes            : {a.audit_notes}"""
            if a.id_data:
                docs_summary += f"""
    - ID Name          : {a.id_data.full_name}
    - ID Number        : {a.id_data.document_number}
    - Expiry           : {a.id_data.expiration_date} {'[EXPIRED]' if a.id_data.is_expired else '[VALID]'}"""
            if a.bank_data:
                docs_summary += f"""
    - RIB Holder       : {a.bank_data.account_holder_name}
    - IBAN             : {a.bank_data.iban_or_account_num}
    - Name match       : {'⚠ MISMATCH' if a.name_mismatch_detected else '✓ MATCH'}"""

        global_score = sum(item["audit"].compliance_score for item in audits) / len(audits)
        has_anomaly = any(
            item["audit"].name_mismatch_detected or
            (item["audit"].id_data and item["audit"].id_data.is_expired)
            for item in audits
        )

        prompt = f"""
You are the '00-DISPATCH' agent of NavourSync AI, an HR compliance system for film productions.

You have just completed a full dossier audit for crew member: {reference_name}
Production: {production_title}
Overall compliance score: {global_score * 100:.0f}%

Here is the detailed audit of each document in their dossier:
{docs_summary}

INSTRUCTIONS:
- Write ONE single professional email that covers ALL documents in the dossier.
- If there are anomalies, list every issue clearly and specify which document it concerns.
- Be firm but polite. Give a 48-hour deadline to resubmit corrected documents.
- If all documents are compliant, write a warm validation confirmation.
- The email must feel like it comes from a professional production HR department.
- Do NOT write a separate email per document — this must be ONE unified message.
"""

        response = self.client.models.generate_content(
            model=self.model,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=DispatchNotice,
                temperature=0.2,
            ),
        )

        return DispatchNotice.model_validate_json(response.text)
