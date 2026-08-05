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
        Tu es l'agent '00-AUDITOR' de NavourSync AI.
        Le document ci-joint a été identifié comme : {doc_type.value}.
        Ta mission :
        1. Extraire rigoureusement toutes les informations textuelles obligatoires.
        2. Si c'est une CNI, vérifie si la date d'expiration est dépassée par rapport à aujourd'hui (Août 2026).
        3. Si un nom de référence ({reference_name or 'N/A'}) est fourni, vérifie scrupuleusement si le nom extrait du RIB/Document correspond EXACTEMENT.
        4. Si c'est une demande manuscrite, transcris l'intégralité du texte avec précision.
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
