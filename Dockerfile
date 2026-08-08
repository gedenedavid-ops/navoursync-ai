FROM python:3.11-slim

# Évite les prompts interactifs apt
ENV DEBIAN_FRONTEND=noninteractive

# Variables Streamlit Cloud Run
ENV PORT=8080
ENV STREAMLIT_SERVER_PORT=8080
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# Dépendances système minimales
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code source
COPY . .

# Installe le package src en mode editable
RUN pip install --no-cache-dir -e .

EXPOSE 8080

# Sur Cloud Run, Vertex AI ADC est automatique — pas besoin de GOOGLE_APPLICATION_CREDENTIALS
CMD ["python", "-m", "streamlit", "run", "src/app.py", \
     "--server.port=8080", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
