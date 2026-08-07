import os
from typing import List, Literal
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

    # ── Nouveau : avis de décision ──────────────────────────────────────────
    decision: Literal["VALIDATED", "PENDING", "BLOCKED"] = Field(
        description=(
            "VALIDATED = all documents compliant, crew member cleared to work. "
            "PENDING = minor issues, documents need correction but not blocking. "
            "BLOCKED = critical fraud or expired ID, crew member cannot work until resolved."
        )
    )

    # ── Nouveau : note interne HR (confidentielle, pour le régisseur) ───────
    hr_note: str = Field(
        description=(
            "Short internal HR note (2-4 sentences) summarising the audit outcome "
            "for the production manager. Confidential — not sent to the crew member. "
            "Mention document numbers, expiry dates, and any fraud flags explicitly."
        )
    )

    # ── Email à envoyer (EN) ────────────────────────────────────────────────
    email_subject: str = Field(description="Professional email subject line in English")
    message_body: str = Field(description="Full professional email body in English covering all documents")

    # ── Message à envoyer (FR) ──────────────────────────────────────────────
    message_body_fr: str = Field(
        description="Same professional message translated into French, same structure and tone"
    )


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

INSTRUCTIONS — produce all four outputs below:

1. DECISION (choose exactly one):
   - VALIDATED  : every document is compliant and valid → crew member is cleared to work
   - PENDING    : at least one document has a minor issue (low confidence, missing field) but no fraud or expiry
   - BLOCKED    : at least one document is expired OR a RIB name mismatch was detected (potential bank fraud)

2. HR NOTE (internal, confidential, for the production manager only):
   - 2 to 4 sentences maximum
   - Mention document numbers, expiry dates, and exact nature of any fraud flag
   - Neutral, factual tone — no pleasantries

3. EMAIL (in English, to send to the crew member):
   - Professional subject line
   - If VALIDATED  : warm confirmation, list all validated documents
   - If PENDING    : polite but firm, list each issue, give 48-hour deadline to resubmit
   - If BLOCKED    : serious tone, specify blocked reason, instruct to contact HR immediately
   - Sign off as "NavourSync HR Compliance — {production_title}"

4. MESSAGE FR (exact same email translated into French, identical structure and tone)
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
