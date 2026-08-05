import os
from dotenv import load_dotenv
from google.genai.errors import ClientError
from src.agents.classifier import VisionClassifierAgent
from src.agents.auditor import AuditorAgent
from src.agents.dispatcher import DispatcherAgent
from src.db.client import ClickHouseManager

load_dotenv()


def main():
    print("NAVOURSYNC AI -- PIPELINE COMPLET (AGENTS 1..3 + CLICKHOUSE)")
    print("-" * 60)

    # Vérification précoce de la clé API
    if not os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") == "your_gemini_api_key_here":
        print("[ERREUR] GEMINI_API_KEY manquante ou non configuree dans .env")
        print("         Generez une cle sur https://aistudio.google.com/app/apikey")
        return

    # Initialisation
    agent_vision = VisionClassifierAgent()
    agent_auditor = AuditorAgent()
    agent_dispatcher = DispatcherAgent()
    db = ClickHouseManager()
    db.connect()

    sample_file = "data/samples/test.jpg"
    reference_person = "KOUAKOU DAVID"

    if not os.path.exists(sample_file):
        print(f"[WARN] Depose une image de test dans : {sample_file}")
        return

    try:
        # 1. Classification (00-VISION)
        print("\n[1/4] Agent 00-VISION : Classification...")
        classification = agent_vision.classify(sample_file)
        print(f"  Type     : {classification.document_type.value}")
        print(f"  Confiance: {classification.confidence * 100:.1f}%")

        # 2. Audit (00-AUDITOR)
        print("\n[2/4] Agent 00-AUDITOR : Audit & Detections...")
        audit = agent_auditor.audit(
            file_path=sample_file,
            doc_type=classification.document_type,
            reference_name=reference_person,
        )
        print(f"  Conformite : {audit.compliance_score * 100:.0f}%")
        print(f"  Mismatch   : {'[ALERTE] OUI' if audit.name_mismatch_detected else 'OK'}")
        if audit.id_data:
            print(f"  Nom CNI    : {audit.id_data.full_name}")
            print(f"  Perime     : {'[KO] OUI' if audit.id_data.is_expired else '[OK] NON'}")
        if audit.bank_data:
            print(f"  Titulaire  : {audit.bank_data.account_holder_name}")
            print(f"  IBAN       : {audit.bank_data.iban_or_account_num}")

        # 3. Dispatch & Relance (00-DISPATCH)
        print("\n[3/4] Agent 00-DISPATCH : Generation de la notification...")
        notice = agent_dispatcher.generate_notice(
            audit=audit,
            doc_type=classification.document_type,
            reference_name=reference_person,
        )
        print(f"  Action requise : {'[ALERTE] OUI' if notice.requires_action else 'OK - Aucune action'}")
        if notice.issues_found:
            for issue in notice.issues_found:
                print(f"  [!] {issue}")
        print(f"  Objet Email    : {notice.email_subject}")
        print(f"\n--- Message ---\n{notice.message_body}\n---------------")

        # 4. Persistance ClickHouse
        print("\n[4/4] Log dans ClickHouse...")
        full_name = (
            audit.id_data.full_name if audit.id_data
            else (audit.bank_data.account_holder_name if audit.bank_data else reference_person)
        )
        doc_num = (
            audit.id_data.document_number if audit.id_data
            else (audit.bank_data.iban_or_account_num if audit.bank_data else "")
        )
        is_expired = audit.id_data.is_expired if audit.id_data else False

        db.log_audit(
            doc_type=classification.document_type.value,
            confidence=classification.confidence,
            full_name=full_name,
            doc_num=doc_num,
            is_expired=is_expired,
            mismatch=audit.name_mismatch_detected,
            score=audit.compliance_score,
            notes=audit.audit_notes,
        )

        print("\nPipeline multi-agents complet execute avec succes !")

    except ClientError as e:
        print(f"[ERREUR API Gemini] {e.status_code} — {e.message}")
    except Exception as e:
        print(f"[ERREUR] {e}")


if __name__ == "__main__":
    main()
