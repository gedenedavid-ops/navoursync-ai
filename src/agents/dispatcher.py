import os
from typing import List
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from src.agents.auditor import AuditResult
from src.agents.classifier import DocumentType


# 1. Schéma de sortie pour le message de relance
class DispatchNotice(BaseModel):
    recipient_name: str = Field(description="Nom du membre de l'équipe / casting concerné")
    requires_action: bool = Field(description="True si une action est requise de la part du membre")
    issues_found: List[str] = Field(description="Liste claire des problèmes détectés (ex: CNI périmée)")
    email_subject: str = Field(description="Objet de l'email officiel de relance")
    message_body: str = Field(description="Corps du message rédigé avec professionnalisme (Email / SMS)")


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
        """Génère un avis de conformité ou une relance selon les anomalies détectées."""

        prompt = f"""
        Tu es l'agent '00-DISPATCH' de NavourSync AI pour la régie d'un tournage de cinéma.
        Examine le résultat d'audit ci-dessous pour le membre d'équipe : {reference_name}.

        Résultat Audit :
        - Type de document    : {doc_type.value}
        - Score de conformité : {audit.compliance_score}
        - Nom Discordant (RIB vs CNI) : {audit.name_mismatch_detected}
        - Notes d'audit       : {audit.audit_notes}

        Si le dossier présente des anomalies (score < 1.0, document périmé, ou nom discordant),
        génère une relance claire et polie mais ferme pour demander la bonne pièce.
        Si le dossier est 100% conforme, génère un message de confirmation de validation.
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
