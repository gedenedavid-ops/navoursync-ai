import os
from typing import Optional
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from src.agents.classifier import DocumentType


# 1. Modèles Pydantic pour structurer les données extraites
class IDCardData(BaseModel):
    full_name: str = Field(description="Nom et prénoms complets tels qu'inscrits sur la CNI")
    document_number: str = Field(description="Numéro officiel de la CNI ou du passeport")
    expiration_date: str = Field(description="Date d'expiration au format YYYY-MM-DD")
    is_expired: bool = Field(description="True si le document est périmé, sinon False")


class BankDetailsData(BaseModel):
    account_holder_name: str = Field(description="Nom complet du titulaire du compte bancaire")
    iban_or_account_num: str = Field(description="Numéro IBAN ou numéro de compte bancaire complet")
    bank_name: Optional[str] = Field(default=None, description="Nom de la banque si disponible")


class AuditResult(BaseModel):
    id_data: Optional[IDCardData] = None
    bank_data: Optional[BankDetailsData] = None
    transcribed_text: Optional[str] = Field(default=None, description="Transcription si texte manuscrit")
    name_mismatch_detected: bool = Field(
        description="True si le nom du RIB ne correspond pas à la CNI", default=False
    )
    compliance_score: float = Field(description="Score global de conformité entre 0.0 et 1.0")
    audit_notes: str = Field(description="Résumé court des anomalies ou de la conformité")


class AuditorAgent:
    def __init__(self, api_key: str = None):
        self.client = genai.Client(api_key=api_key or os.getenv("GEMINI_API_KEY"))
        # Gemini 2.5 Flash excelle dans la structuration OCR rapide
        self.model = "gemini-2.5-flash"

    def audit(
        self,
        file_path: str,
        doc_type: DocumentType,
        reference_name: Optional[str] = None,
    ) -> AuditResult:
        """Audite un document spécifique et extrait les métadonnées de conformité."""

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Fichier introuvable : {file_path}")

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        prompt = f"""
        You are the '00-AUDITOR' agent of NavourSync AI.
        The document has been identified as: {doc_type.value}.
        Your mission:
        1. Extract all mandatory text fields rigorously.
        2. If this is an ID card or passport, check whether the expiry date has passed relative to today (August 2026).
        3. If a reference name is provided ({reference_name or 'N/A'}), verify whether the name on the document matches.
           IMPORTANT: treat first name / last name in reverse order as a MATCH (e.g. "Damon Salvatorr" == "Salvatorr Damon").
           Only flag name_mismatch_detected=true if the names are genuinely different people, not just reversed.
        4. If this is a handwritten request, transcribe the full text accurately.
        """

        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                types.Part.from_bytes(data=file_bytes, mime_type="image/jpeg"),
                prompt,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AuditResult,
                temperature=0.0,  # Déterminisme absolu pour les données RH
            ),
        )

        return AuditResult.model_validate_json(response.text)
