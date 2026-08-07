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
        You are the '00-VISION' agent of NavourSync AI for a cinema production studio.
        Examine this document carefully and identify its exact category.

        Classification rules — read in order, stop at first match:
        1. cni_passport      : Shows a photo of a person's face + official ID number + birth/expiry dates. Government-issued identity document.
        2. rib_iban          : Contains an explicit IBAN string (e.g. FR76..., GB29...), BIC/SWIFT code, and a bank name. No photos of people.
        3. handwritten_request : The main content is handwritten text (cursive or print). May be on lined paper.
        4. image_rights_release : A printed form or contract relating to image rights, likeness, casting, or media release. Contains checkboxes, signature lines, or clauses about image/video usage. No IBAN.
        5. contract          : A typed/printed employment contract or work agreement with signatures.
        6. birth_certificate : Official birth record issued by civil registry.
        7. unknown           : Cannot be classified with confidence.

        IMPORTANT: if the document contains an IBAN number, classify it as rib_iban regardless of other content.
        If the document has signature lines and clauses about image/video rights but NO IBAN, classify it as image_rights_release.
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
