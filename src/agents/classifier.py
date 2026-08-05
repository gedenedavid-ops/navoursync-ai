import os
from enum import Enum
from pydantic import BaseModel, Field
from google import genai
from google.genai import types


# 1. Catégories strictes de documents de production/casting
class DocumentType(str, Enum):
    IDENTITY_CARD = "cni_passport"
    BANK_DETAILS = "rib_iban"
    EMPLOYMENT_CONTRACT = "contract"
    IMAGE_RIGHTS = "image_rights_release"
    HANDWRITTEN_REQUEST = "handwritten_request"
    BIRTH_CERTIFICATE = "birth_certificate"
    UNKNOWN = "unknown"


# 2. Schéma de sortie structuré pour le pipeline
class DocumentClassificationResult(BaseModel):
    document_type: DocumentType = Field(description="Le type exact du document identifié")
    confidence: float = Field(description="Score de confiance entre 0.0 et 1.0")
    detected_language: str = Field(description="Langue principale détectée dans le document")
    reasoning: str = Field(description="Explication concise justifiant le choix")


class VisionClassifierAgent:
    def __init__(self, api_key: str = None):
        self.client = genai.Client(api_key=api_key or os.getenv("GEMINI_API_KEY"))
        # Utilisation du modèle Gemini 2.5 Flash pour une classification rapide et précise
        self.model = "gemini-2.5-flash"

    def classify(self, file_path: str, mime_type: str = "image/jpeg") -> DocumentClassificationResult:
        """Analyse un fichier local et renvoie sa classification structurée."""

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Fichier introuvable : {file_path}")

        with open(file_path, "rb") as f:
            file_bytes = f.read()

        prompt = """
        Tu es l'agent '00-VISION' de NavourSync AI pour un studio de cinéma.
        Examine ce document et identifie sa catégorie exacte parmi les choix autorisés.
        Fais très attention aux détails caractéristiques :
        - CNI / Passeport : Photos d'identité, numéros officiels, dates de naissance/expiration.
        - RIB : Présence explicite d'IBAN, code BIC/SWIFT, nom de banque.
        - Demande manuscrite : Écriture faite à la main.
        - Droit à l'image : Formulaire de cession de droit à l'image / casting.
        """

        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                prompt
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=DocumentClassificationResult,
                temperature=0.1,  # Faible température pour un comportement déterministe
            )
        )

        return DocumentClassificationResult.model_validate_json(response.text)
