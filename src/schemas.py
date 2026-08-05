"""
src/schemas.py
Point d'entrée unifié pour tous les modèles Pydantic et enums du projet.
Importez depuis ici dans app.py et les scripts externes pour éviter
les imports circulaires entre agents.
"""

# Classifier
from src.agents.classifier import DocumentType, DocumentClassificationResult  # noqa: F401

# Auditor
from src.agents.auditor import (  # noqa: F401
    IDCardData,
    BankDetailsData,
    AuditResult,
)

# Dispatcher
from src.agents.dispatcher import DispatchNotice  # noqa: F401

# Alias pratiques utilisés dans le mode Mock de app.py
BankRibData = BankDetailsData  # rétrocompatibilité avec le code de démo
