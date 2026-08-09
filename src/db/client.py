import os
import clickhouse_connect


class ClickHouseManager:
    def __init__(self):
        self.host = os.getenv("CLICKHOUSE_HOST", "localhost")
        self.port = int(os.getenv("CLICKHOUSE_PORT", "8123"))
        self.user = os.getenv("CLICKHOUSE_USER", "default")
        self.password = os.getenv("CLICKHOUSE_PASSWORD", "")
        # Accept both CLICKHOUSE_DATABASE (Cloud Run) and CLICKHOUSE_DB (legacy)
        self.database = (
            os.getenv("CLICKHOUSE_DATABASE")
            or os.getenv("CLICKHOUSE_DB")
            or "default"
        )
        self.client = None

    def connect(self):
        """Etablit la connexion avec l'instance ClickHouse."""
        try:
            self.client = clickhouse_connect.get_client(
                host=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                database=self.database,
                secure=True,
            )
            print("[ClickHouse] Connexion etablie avec succes.")
            self._init_db()
        except Exception as e:
            print(f"[ClickHouse] Mode Offline — connexion impossible : {e}")

    def _init_db(self):
        """Cree la table analytique si elle n'existe pas."""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS document_audits (
            audit_id     UUID DEFAULT generateUUIDv4(),
            timestamp    DateTime DEFAULT now(),
            document_type String,
            confidence   Float32,
            full_name    String,
            document_number String,
            is_expired   UInt8,
            name_mismatch UInt8,
            compliance_score Float32,
            audit_notes  String
        ) ENGINE = MergeTree()
        ORDER BY (timestamp, document_type);
        """
        if self.client:
            self.client.command(create_table_query)
            print("[ClickHouse] Table document_audits prete.")

    def log_audit(
        self,
        doc_type: str,
        confidence: float,
        full_name: str,
        doc_num: str,
        is_expired: bool,
        mismatch: bool,
        score: float,
        notes: str,
    ):
        """Insere un rapport d'audit dans ClickHouse."""
        import clickhouse_connect
        try:
            client = clickhouse_connect.get_client(
                host=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                database=self.database,
                secure=True,
            )
        except Exception as e:
            print(f"[ClickHouse] Non connecte — enregistrement ignore. Erreur: {e}")
            return

        row = [
            doc_type,
            confidence,
            full_name or "",
            doc_num or "",
            1 if is_expired else 0,
            1 if mismatch else 0,
            score,
            notes,
        ]

        try:
            client.insert(
                "document_audits",
                [row],
                column_names=[
                    "document_type",
                    "confidence",
                    "full_name",
                    "document_number",
                    "is_expired",
                    "name_mismatch",
                    "compliance_score",
                    "audit_notes",
                ],
            )
            print("[ClickHouse] Audit sauvegarde.")
        finally:
            client.close()

    def get_compliance_stats(self) -> dict:
        """Retourne les metriques de conformite globales depuis ClickHouse.
        Utilise un client frais pour eviter les erreurs de concurrence Streamlit.
        """
        if not self.client:
            return {}

        import clickhouse_connect
        reader = clickhouse_connect.get_client(
            host=self.host,
            port=self.port,
            username=self.user,
            password=self.password,
            database=self.database,
            secure=True,
        )
        try:
            result = reader.query("""
                SELECT
                    count()                          AS total_audits,
                    countIf(is_expired = 1)          AS expired_docs,
                    countIf(name_mismatch = 1)       AS mismatches,
                    round(avg(compliance_score), 3)  AS avg_compliance
                FROM document_audits
            """)
            row = result.first_row
            return {
                "total_audits":   row[0],
                "expired_docs":   row[1],
                "mismatches":     row[2],
                "avg_compliance": row[3],
            }
        finally:
            reader.close()
