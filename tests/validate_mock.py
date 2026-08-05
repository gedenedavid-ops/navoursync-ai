import ast, pathlib

# 1. Syntaxe
for fname in ("src/app.py", "src/schemas.py"):
    ast.parse(pathlib.Path(fname).read_text(encoding="utf-8"))
    print(f"{fname:<20} — syntaxe OK")

# 2. Imports schemas
from src.schemas import (
    DocumentType, DocumentClassificationResult,
    IDCardData, BankDetailsData, AuditResult,
    DispatchNotice, BankRibData,
)
print("src.schemas          — imports OK")
print("  BankRibData is BankDetailsData :", BankRibData is BankDetailsData)
print("  BANK_DETAILS  :", DocumentType.BANK_DETAILS)
print("  IDENTITY_CARD :", DocumentType.IDENTITY_CARD)

# 3. Mock scenarios
crew = "KOUAKOU DAVID"

fraud_audit = AuditResult(
    compliance_score=0.2,
    name_mismatch_detected=True,
    bank_data=BankRibData(
        account_holder_name="KOUASSI Jean",
        iban_or_account_num="FR7630006000011234567890189",
    ),
    audit_notes="Discordance : nom RIB KOUASSI Jean ne correspond pas a KOUAKOU DAVID.",
)

expired_audit = AuditResult(
    compliance_score=0.4,
    name_mismatch_detected=False,
    id_data=IDCardData(
        full_name=crew,
        document_number="ID-998822",
        is_expired=True,
        expiration_date="2022-01-15",
    ),
    audit_notes="La CNI est expiree depuis le 2022-01-15.",
)

ok_audit = AuditResult(
    compliance_score=1.0,
    name_mismatch_detected=False,
    bank_data=BankRibData(
        account_holder_name=crew,
        iban_or_account_num="FR7630006000011234567890189",
    ),
    audit_notes="Document parfaitement conforme.",
)

notice = DispatchNotice(
    recipient_name=crew,
    requires_action=True,
    issues_found=[fraud_audit.audit_notes],
    email_subject="[NavourSync AI] Action requise — Dossier BLOCKBUSTER_007",
    message_body=f"Bonjour {crew},\n\nUne anomalie a ete detectee.\n\n— Regie NavourSync AI",
)

print()
print(f"Mock Fraude   — score: {fraud_audit.compliance_score} | mismatch: {fraud_audit.name_mismatch_detected}")
print(f"Mock Expire   — score: {expired_audit.compliance_score} | expire: {expired_audit.id_data.is_expired}")
print(f"Mock Conforme — score: {ok_audit.compliance_score}")
print(f"DispatchNotice OK  — objet: {notice.email_subject}")
print()
print("=== TOUS LES SCENARIOS MOCK SONT VALIDES ===")
