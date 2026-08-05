import streamlit as st
import os
from PIL import Image
from dotenv import load_dotenv
from google.genai.errors import ClientError

from src.agents.classifier import VisionClassifierAgent
from src.agents.auditor import AuditorAgent
from src.agents.dispatcher import DispatcherAgent
from src.db.client import ClickHouseManager

load_dotenv()

# -----------------------------------------------------------------------------
# Page config & CSS — James Bond 007 Style
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="NavourSync AI — Studio Control",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
.stApp {
    background-color: #0A0A0B;
    color: #E0E0E0;
    font-family: 'Inter', -apple-system, sans-serif;
}
section[data-testid="stSidebar"] {
    background-color: #121215;
    border-right: 1px solid #2C2C2E;
}
h1, h2, h3, h4 {
    color: #FFFFFF !important;
    font-weight: 600;
    letter-spacing: -0.5px;
}
div[data-testid="stMetricValue"] {
    font-family: 'JetBrains Mono', monospace;
    color: #FFFFFF !important;
}
div[data-testid="stMetricLabel"] {
    color: #8E8E93 !important;
    font-size: 11px !important;
    text-transform: uppercase;
    letter-spacing: 1px;
}
div[data-testid="stMetric"] {
    background-color: #121215;
    border: 1px solid #2C2C2E;
    border-radius: 4px;
    padding: 1rem 1.2rem;
}
.stButton > button {
    background-color: #E50914 !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 3px !important;
    font-weight: 600 !important;
    letter-spacing: 0.5px;
    padding: 0.6rem 1.4rem !important;
    width: 100%;
}
.stButton > button:hover { background-color: #B20710 !important; }
.stButton > button:disabled {
    background-color: #3a3a3e !important;
    color: #8E8E93 !important;
    cursor: not-allowed !important;
}
section[data-testid="stFileUploadDropzone"] {
    background-color: #121215 !important;
    border: 1px dashed #2C2C2E !important;
}
div[data-testid="stTextInput"] input {
    background-color: #1A1A1E !important;
    color: #FFFFFF !important;
    border: 1px solid #2C2C2E !important;
}
div[data-testid="stAlert"] {
    background-color: #1A1A1E !important;
    border: 1px solid #2C2C2E !important;
    color: #FFFFFF !important;
}
hr { border-color: #2C2C2E !important; }
.stCaption { color: #8E8E93 !important; }
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #0A0A0B; }
::-webkit-scrollbar-thumb { background: #2C2C2E; border-radius: 2px; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Validation clé API au démarrage
# -----------------------------------------------------------------------------
api_key = os.getenv("GEMINI_API_KEY", "")
api_ready = bool(api_key) and api_key != "your_gemini_api_key_here"


# -----------------------------------------------------------------------------
# Initialisation agents & DB — une seule fois par session (cache_resource)
# -----------------------------------------------------------------------------
@st.cache_resource
def init_system():
    vision   = VisionClassifierAgent()
    auditor  = AuditorAgent()
    dispatch = DispatcherAgent()
    db = ClickHouseManager()
    db.connect()
    return vision, auditor, dispatch, db


agent_vision, agent_auditor, agent_dispatch, db_manager = init_system()


# -----------------------------------------------------------------------------
# Sidebar
# -----------------------------------------------------------------------------
st.sidebar.markdown("## NAVOURSYNC AI")
st.sidebar.markdown("`v1.0.0 — PRODUCTION`")
st.sidebar.markdown("---")

st.sidebar.markdown("#### Production Settings")
production_title = st.sidebar.text_input("Production Name", "PRODUCTION_001")
crew_member_ref  = st.sidebar.text_input("Crew Member Reference (full name)", "")

st.sidebar.markdown("---")
st.sidebar.markdown("#### System Status")

st.sidebar.markdown(
    f"{'🟢' if api_ready else '🔴'} **Gemini API** : {'Connected' if api_ready else 'API key missing — check .env'}"
)
st.sidebar.markdown(
    f"{'🟢' if db_manager.client else '🟡'} **ClickHouse** : {'Connected' if db_manager.client else 'Offline — audits not persisted'}"
)

if not api_ready:
    st.sidebar.error("GEMINI_API_KEY not configured. Set it in .env to run live audits.")


# -----------------------------------------------------------------------------
# Screen 1 — Studio Control Center (live ClickHouse metrics)
# -----------------------------------------------------------------------------
st.title("Studio Control Center")
st.caption(
    f"Real-time crew compliance dashboard — Production: **{production_title}**"
)
st.markdown("---")

if db_manager.client:
    stats       = db_manager.get_compliance_stats()
    total       = stats.get("total_audits", 0)
    expired     = stats.get("expired_docs", 0)
    mismatches  = stats.get("mismatches", 0)
    avg_score   = stats.get("avg_compliance", 0.0)
    score_label = f"{avg_score * 100:.1f}%" if total else "—"
else:
    total, expired, mismatches, score_label = "—", "—", "—", "—"

m1, m2, m3, m4 = st.columns(4)
m1.metric("Documents Processed", total)
m2.metric("Average Compliance",  score_label)
m3.metric("Expired IDs",         expired,    delta_color="inverse")
m4.metric("RIB Fraud Alerts",    mismatches, delta_color="inverse")

st.markdown("---")


# -----------------------------------------------------------------------------
# Screen 2 — Live Dropzone (multi-file)
# -----------------------------------------------------------------------------
st.subheader("Dropzone — Live Document Analysis")

col_upload, col_results = st.columns([1, 1], gap="large")

with col_upload:
    uploaded_files = st.file_uploader(
        "Drop one or more documents (ID card, RIB, Contract, Image rights…)",
        type=["jpg", "jpeg", "png"],
        accept_multiple_files=True,
        disabled=not api_ready,
    )

    if uploaded_files:
        st.markdown(f"**{len(uploaded_files)} file(s) loaded:**")
        for uf in uploaded_files:
            st.image(Image.open(uf), caption=uf.name, width="stretch")

with col_results:
    st.markdown("#### Multi-Agent Live Analysis")

    if not api_ready:
        st.error("Gemini API key missing. Configure GEMINI_API_KEY in .env to enable live audits.")

    elif not crew_member_ref.strip():
        st.warning("Enter the crew member's full name in the sidebar before running the audit.")

    elif not uploaded_files:
        st.info("Waiting for document(s) in the Dropzone.")

    else:
        if st.button("RUN COMPLIANCE AUDIT"):

            def _run_pipeline(uf):
                """Process a single file through the full 3-agent pipeline.
                Returns (audit, notice, doc_type, confidence).
                Raises on Gemini or unexpected errors.
                """
                temp_path = os.path.join("data", "samples", uf.name)
                os.makedirs(os.path.dirname(temp_path), exist_ok=True)
                with open(temp_path, "wb") as f:
                    f.write(uf.getbuffer())

                try:
                    st.write(f"**[00-VISION]** `{uf.name}` — Classifying…")
                    classification = agent_vision.classify(temp_path)
                    doc_type = classification.document_type
                    confidence = classification.confidence
                    st.write(f"→ `{doc_type.value}` — Confidence: {confidence * 100:.1f}%")

                    st.write(f"**[00-AUDITOR]** `{uf.name}` — OCR & Compliance check…")
                    audit = agent_auditor.audit(
                        temp_path, doc_type, reference_name=crew_member_ref.strip()
                    )
                    st.write(f"→ Compliance score: `{audit.compliance_score * 100:.0f}%`")

                    st.write(f"**[00-DISPATCH]** `{uf.name}` — Generating notification…")
                    notice = agent_dispatch.generate_notice(
                        audit, doc_type, reference_name=crew_member_ref.strip()
                    )

                    return audit, notice, doc_type, confidence

                finally:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)

            # ── Process all files ──────────────────────────────────────────
            all_results = []

            with st.status(
                f"Processing {len(uploaded_files)} file(s)…", expanded=True
            ) as status:
                pipeline_ok = True
                for i, uf in enumerate(uploaded_files, 1):
                    st.markdown(f"---\n**File {i}/{len(uploaded_files)} — `{uf.name}`**")
                    try:
                        audit, notice, doc_type, confidence = _run_pipeline(uf)
                    except ClientError as e:
                        st.error(f"Gemini API error on `{uf.name}`: {e.message}")
                        pipeline_ok = False
                        break
                    except Exception as e:
                        st.error(f"Unexpected error on `{uf.name}`: {e}")
                        pipeline_ok = False
                        break

                    # Persist to ClickHouse
                    full_name = (
                        audit.id_data.full_name if audit.id_data
                        else (audit.bank_data.account_holder_name if audit.bank_data else crew_member_ref)
                    )
                    doc_num = (
                        audit.id_data.document_number if audit.id_data
                        else (audit.bank_data.iban_or_account_num if audit.bank_data else "")
                    )
                    is_expired = audit.id_data.is_expired if audit.id_data else False

                    db_manager.log_audit(
                        doc_type=doc_type.value,
                        confidence=confidence,
                        full_name=full_name,
                        doc_num=doc_num,
                        is_expired=is_expired,
                        mismatch=audit.name_mismatch_detected,
                        score=audit.compliance_score,
                        notes=audit.audit_notes,
                    )

                    all_results.append({
                        "file":    uf.name,
                        "audit":   audit,
                        "notice":  notice,
                        "doc_type": doc_type,
                    })

                if pipeline_ok:
                    status.update(
                        label=f"{len(all_results)} file(s) processed successfully.",
                        state="complete",
                        expanded=False,
                    )
                else:
                    status.update(
                        label="Pipeline stopped — see error above.",
                        state="error",
                        expanded=True,
                    )

            # ----------------------------------------------------------------
            # Screen 3 — Audit Report (one expander per file)
            # ----------------------------------------------------------------
            if all_results:
                st.markdown("---")
                st.markdown("#### Audit Report")

                for res in all_results:
                    audit  = res["audit"]
                    notice = res["notice"]
                    fname  = res["file"]
                    anomaly = audit.name_mismatch_detected or (
                        audit.id_data and audit.id_data.is_expired
                    )

                    with st.expander(
                        f"{'🔴' if anomaly else '🟢'}  {fname} — Score: {audit.compliance_score * 100:.0f}%",
                        expanded=anomaly,
                    ):
                        if anomaly:
                            st.error(f"ANOMALY DETECTED — Compliance score: {audit.compliance_score * 100:.0f}%")
                        else:
                            st.success(f"COMPLIANT — Compliance score: {audit.compliance_score * 100:.0f}%")

                        if audit.id_data:
                            st.markdown(f"**Full Name (ID):** {audit.id_data.full_name}")
                            st.markdown(f"**Document Number:** `{audit.id_data.document_number}`")
                            st.markdown(f"**Expiry Date:** {audit.id_data.expiration_date}")
                            if audit.id_data.is_expired:
                                st.markdown(
                                    '<span style="color:#E50914;font-weight:700;">⚠ EXPIRED DOCUMENT</span>',
                                    unsafe_allow_html=True,
                                )

                        if audit.bank_data:
                            st.markdown(f"**RIB Holder:** {audit.bank_data.account_holder_name}")
                            st.markdown(f"**IBAN:** `{audit.bank_data.iban_or_account_num}`")
                            if audit.name_mismatch_detected:
                                st.markdown(
                                    f'<span style="color:#E50914;font-weight:700;">'
                                    f'⚠ RIB NAME "{audit.bank_data.account_holder_name}" '
                                    f'DOES NOT MATCH "{crew_member_ref.strip()}"'
                                    f'</span>',
                                    unsafe_allow_html=True,
                                )

                        if audit.transcribed_text:
                            st.markdown("**Handwritten Transcription:**")
                            st.code(audit.transcribed_text, language=None)

                        st.markdown(f"*Audit notes:* {audit.audit_notes}")

                        st.markdown("---")
                        st.markdown("**00-DISPATCH Notification**")
                        if notice.requires_action:
                            for issue in notice.issues_found:
                                st.markdown(
                                    f'<span style="color:#E50914;">⚠ {issue}</span>',
                                    unsafe_allow_html=True,
                                )
                        st.markdown(f"**Subject:** {notice.email_subject}")
                        st.code(notice.message_body, language=None)
