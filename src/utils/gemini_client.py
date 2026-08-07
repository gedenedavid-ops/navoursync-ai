"""
Gemini client factory — supports both modes:

  • Vertex AI mode  (uses GCP billing credits, no API key needed)
    Set in .env:  USE_VERTEX_AI=true, GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION
    Auth locally: `gcloud auth application-default login`
    Auth on Streamlit Cloud: GOOGLE_APPLICATION_CREDENTIALS_JSON secret (service account JSON)

  • API key mode  (Google AI Studio, free tier / pay-as-you-go)
    Set in .env:  GEMINI_API_KEY=AIzaSy...
"""
import os
import json
import tempfile
from google import genai


def get_gemini_client() -> genai.Client:
    """
    Returns a configured google.genai.Client.

    Priority:
      1. Vertex AI if USE_VERTEX_AI=true (consumes GCP credits)
      2. API key fallback (GEMINI_API_KEY)
    """
    use_vertex = os.getenv("USE_VERTEX_AI", "false").lower() == "true"

    if use_vertex:
        project  = os.getenv("GOOGLE_CLOUD_PROJECT", "gen-lang-client-0731365913")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

        # Streamlit Cloud: service account JSON stored as a secret string
        sa_json = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON")
        if sa_json:
            # Write to a temp file so google-auth picks it up
            tmp = tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            )
            tmp.write(sa_json)
            tmp.flush()
            tmp.close()
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name

        return genai.Client(
            vertexai=True,
            project=project,
            location=location,
        )

    # Fallback — API key mode
    api_key = os.getenv("GEMINI_API_KEY", "")
    return genai.Client(api_key=api_key)
