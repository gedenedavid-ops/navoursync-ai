import streamlit as st
import os
from PIL import Image
from dotenv import load_dotenv
from google.genai.errors import ClientError

from src.agents.classifier import VisionClassifierAgent
from src.agents.auditor import AuditorAgent
from src.agents.dispatcher import DispatcherAgent
from src.agents.adk_pipeline import orchestrator_agent          # ADK native
from src.db.client import ClickHouseManager

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NavourSync AI",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS — Zen, minimal, dark
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');

*, *::before, *::after { box-sizing: border-box; }

.stApp {
    background: #0A0A0B;
    color: #D0D0D0;
    font-family: 'Inter', -apple-system, sans-serif;
    font-size: 14px;
    line-height: 1.6;
}
section[data-testid="stSidebar"] {
    background: #0f0f10;
    border-right: 1px solid #1e1e22;
}
section[data-testid="stSidebar"] * { color: #8E8E93; }
section[data-testid="stSidebar"] strong { color: #FFFFFF; }

h1 { font-size: 20px !important; font-weight: 600 !important; color: #FFFFFF !important; letter-spacing: -0.3px; }
h2 { font-size: 13px !important; font-weight: 600 !important; color: #8E8E93 !important;
     letter-spacing: 1.5px; text-transform: uppercase; margin-top: 2rem !important; }
h3 { font-size: 15px !important; font-weight: 500 !important; color: #FFFFFF !important; }

/* Metrics */
div[data-testid="stMetric"] {
    background: #111113;
    border: 1px solid #1e1e22;
    border-radius: 6px;
    padding: 1rem 1.2rem;
}
div[data-testid="stMetricValue"] {
    font-size: 24px !important;
    font-weight: 600 !important;
    color: #FFFFFF !important;
    font-family: 'Inter', monospace;
}
div[data-testid="stMetricLabel"] {
    font-size: 11px !important;
    color: #555560 !important;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* Inputs */
div[data-testid="stTextInput"] input,
div[data-testid="stSelectbox"] div[data-baseweb="select"] {
    background: #111113 !important;
    color: #FFFFFF !important;
    border: 1px solid #1e1e22 !important;
    border-radius: 4px !important;
}
div[data-testid="stTextInput"] input:focus { border-color: #2C2C2E !important; }

/* File uploader */
section[data-testid="stFileUploadDropzone"] {
    background: #111113 !important;
    border: 1px dashed #1e1e22 !important;
    border-radius: 4px !important;
    padding: 8px !important;
}
section[data-testid="stFileUploadDropzone"] span { font-size: 12px !important; color: #555560 !important; }

/* Buttons */
.stButton > button {
    background: #E50914 !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 4px !important;
    font-weight: 500 !important;
    font-size: 13px !important;
    padding: 0.5rem 1.2rem !important;
    letter-spacing: 0.3px;
    transition: background 0.15s ease;
}
.stButton > button:hover { background: #c0070f !important; }
.stButton > button:disabled {
    background: #1e1e22 !important;
    color: #3a3a3f !important;
}

/* Secondary button style via markdown workaround */
button[kind="secondary"] {
    background: transparent !important;
    border: 1px solid #2C2C2E !important;
    color: #8E8E93 !important;
}

/* Member card */
.member-card {
    background: #111113;
    border: 1px solid #1e1e22;
    border-radius: 6px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
}
.member-index {
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 2px;
    color: #3a3a3f;
    text-transform: uppercase;
    margin-bottom: 8px;
}

/* Result badges */
.badge-ok  { display:inline-block; background:#0a2a12; color:#30D158; border:1px solid #30D158;
             font-size:10px; font-weight:700; letter-spacing:1px; padding:2px 8px; border-radius:2px; text-transform:uppercase; }
.badge-err { display:inline-block; background:#2a0608; color:#E50914; border:1px solid #E50914;
             font-size:10px; font-weight:700; letter-spacing:1px; padding:2px 8px; border-radius:2px; text-transform:uppercase; }

/* Dividers */
hr { border: none; border-top: 1px solid #1a1a1d; margin: 1.5rem 0; }

/* Alerts */
div[data-testid="stAlert"] {
    background: #111113 !important;
    border: 1px solid #1e1e22 !important;
    border-radius: 4px !important;
}

/* Expander */
details { background: #111113 !important; border: 1px solid #1e1e22 !important; border-radius: 4px !important; }
details summary { color: #FFFFFF !important; font-weight: 500; padding: 0.6rem 0.8rem; }

/* Code blocks */
.stCode { background: #0d0d0e !important; border: 1px solid #1e1e22 !important; }

/* Caption */
.stCaption { color: #3a3a3f !important; font-size: 12px !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-track { background: #0A0A0B; }
::-webkit-scrollbar-thumb { background: #1e1e22; border-radius: 2px; }

/* Hide streamlit branding */
#MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# System init
# ─────────────────────────────────────────────────────────────────────────────
# api_ready = True si Vertex AI mode OU si clé API valide fournie
_use_vertex = os.getenv("USE_VERTEX_AI", "false").lower() == "true"
_api_key    = os.getenv("GEMINI_API_KEY", "")
api_ready   = _use_vertex or (bool(_api_key) and _api_key != "your_gemini_api_key_here")


@st.cache_resource
def init_system():
    vision   = VisionClassifierAgent()
    auditor  = AuditorAgent()
    dispatch = DispatcherAgent()
    db = ClickHouseManager()
    db.connect()
    # ADK orchestrator pre-warmed (tools already bound at import)
    _ = orchestrator_agent
    return vision, auditor, dispatch, db


agent_vision, agent_auditor, agent_dispatch, db_manager = init_system()

# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### NavourSync AI")
    st.caption("v1.0.0 — Production")
    st.markdown("---")
    # Partner badge
    st.markdown(
        '<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">'
        '<span style="font-size:11px;color:#3a3a3f;letter-spacing:1px;text-transform:uppercase;">Partner</span>'
        '<span style="background:#FFDD57;color:#1a1a1a;font-size:10px;font-weight:700;'
        'padding:2px 8px;border-radius:2px;letter-spacing:0.5px;">ClickHouse Cloud</span>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.markdown("---")

    production_title = st.text_input("Production", "PRODUCTION_001", label_visibility="visible")

    st.markdown("---")
    st.markdown("**System**")

    if _use_vertex:
        gemini_status = "🟢 Gemini — Vertex AI"
    elif api_ready:
        gemini_status = "🟢 Gemini — API key"
    else:
        gemini_status = "🔴 Gemini — not configured"
    ch_status  = "🟢 ClickHouse — connected" if db_manager.client else "🟡 ClickHouse — offline"
    adk_status = f"🟢 ADK — {orchestrator_agent.name}"
    st.markdown(f"<small>{gemini_status}</small>", unsafe_allow_html=True)
    st.markdown(f"<small>{ch_status}</small>", unsafe_allow_html=True)
    st.markdown(f"<small>{adk_status}</small>", unsafe_allow_html=True)

    if not api_ready:
        st.markdown("---")
        st.warning("Set GEMINI_API_KEY or USE_VERTEX_AI=true in secrets")

# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(f"# {production_title}")
st.caption("HR Compliance — NavourSync AI")
st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# Metrics
# ─────────────────────────────────────────────────────────────────────────────
if db_manager.client:
    stats       = db_manager.get_compliance_stats()
    total       = stats.get("total_audits", 0)
    expired     = stats.get("expired_docs", 0)
    mismatches  = stats.get("mismatches", 0)
    avg_score   = stats.get("avg_compliance", 0.0)
    score_label = f"{avg_score * 100:.1f}%" if total else "—"
else:
    total, expired, mismatches, score_label = "—", "—", "—", "—"

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total processed",    total)
c2.metric("Avg compliance",     score_label)
c3.metric("Expired IDs",        expired,    delta_color="inverse")
c4.metric("RIB fraud alerts",   mismatches, delta_color="inverse")

st.markdown("---")

# ─────────────────────────────────────────────────────────────────────────────
# Crew Roster — dynamic multi-member form
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("## Crew Roster")

ROLES = [
    "Actor", "Supporting Actor", "Stunt Performer",
    "Director of Photography", "Camera Operator",
    "Sound Engineer", "Director", "Producer",
    "Costume Designer", "Set Designer", "Other",
]

DOC_LABELS = {
    "id":       ("🪪", "ID Card / Passport"),
    "rib":      ("🏦", "RIB / Bank Statement"),
    "rights":   ("📝", "Image Rights Release"),
    "request":  ("✍️",  "Employment Request"),
}

# Initialize session state for crew list
if "crew_count" not in st.session_state:
    st.session_state.crew_count = 1

# Add / remove member buttons
col_add, col_reset, _ = st.columns([1, 1, 5])
with col_add:
    if st.button("+ Add member"):
        st.session_state.crew_count += 1
with col_reset:
    if st.button("Clear all"):
        st.session_state.crew_count = 1
        for key in list(st.session_state.keys()):
            if key.startswith("member_"):
                del st.session_state[key]
        st.rerun()

st.markdown("")

# Render one card per crew member
crew_data = []

for i in range(st.session_state.crew_count):
    with st.container():
        st.markdown(
            f'<div class="member-index">Member {i + 1:02d}</div>',
            unsafe_allow_html=True,
        )
        col_name, col_role = st.columns([2, 2])
        with col_name:
            name = st.text_input(
                "Full name",
                key=f"member_{i}_name",
                placeholder="e.g. KOUAKOU DAVID",
                label_visibility="collapsed",
            )
        with col_role:
            role = st.selectbox(
                "Role",
                ROLES,
                key=f"member_{i}_role",
                label_visibility="collapsed",
            )

        # Document uploaders — 2 columns × 2 rows
        col_a, col_b = st.columns(2)
        uploads = {}
        doc_keys = list(DOC_LABELS.items())

        for j, (doc_key, (icon, label)) in enumerate(doc_keys):
            col = col_a if j % 2 == 0 else col_b
            with col:
                uploads[doc_key] = st.file_uploader(
                    f"{icon} {label}",
                    type=["jpg", "jpeg", "png"],
                    key=f"member_{i}_{doc_key}",
                    label_visibility="visible",
                )

        crew_data.append({
            "index": i,
            "name":  name,
            "role":  role,
            "files": {k: v for k, v in uploads.items() if v is not None},
        })

        st.markdown("<hr style='margin:1rem 0 1.2rem;'>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# Validation & audit trigger
# ─────────────────────────────────────────────────────────────────────────────
ready_members = [m for m in crew_data if m["name"].strip() and m["files"]]
total_docs    = sum(len(m["files"]) for m in ready_members)

if not api_ready:
    st.error("Gemini API key not configured — audits disabled.")
elif not ready_members:
    st.info("Add at least one crew member with a name and one document to run an audit.")
else:
    st.caption(f"{len(ready_members)} member(s) · {total_docs} document(s) ready")
    run_audit = st.button(
        f"Run compliance audit — {len(ready_members)} member(s)",
        disabled=not api_ready,
    )

    if run_audit:

        # ── Core pipeline for a single file ──────────────────────────────────
        def _audit_file(uf, reference_name):
            """00-VISION + 00-AUDITOR on one file. Returns (audit, doc_type, confidence)."""
            temp_path = os.path.join("data", "samples", uf.name)
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            with open(temp_path, "wb") as f:
                f.write(uf.getbuffer())
            try:
                classification = agent_vision.classify(temp_path)
                doc_type       = classification.document_type
                confidence     = classification.confidence
                audit          = agent_auditor.audit(
                    temp_path, doc_type, reference_name=reference_name
                )
                return audit, doc_type, confidence
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        # ── Process each member ───────────────────────────────────────────────
        all_member_results = []

        progress = st.progress(0, text="Starting audit…")
        total_steps = total_docs + len(ready_members)  # docs + dispatch calls
        step = 0

        for member in ready_members:
            name    = member["name"].strip()
            files   = member["files"]
            audits  = []
            error   = None

            for doc_key, uf in files.items():
                step += 1
                progress.progress(
                    step / total_steps,
                    text=f"{name} — analysing {DOC_LABELS[doc_key][1]}…",
                )
                try:
                    audit, doc_type, confidence = _audit_file(uf, name)
                except ClientError as e:
                    error = f"Gemini API error: {e.message}"
                    break
                except Exception as e:
                    error = str(e)
                    break

                # Persist to ClickHouse
                full_name = (
                    audit.id_data.full_name if audit.id_data
                    else (audit.bank_data.account_holder_name if audit.bank_data else name)
                )
                doc_num = (
                    audit.id_data.document_number if audit.id_data
                    else (audit.bank_data.iban_or_account_num if audit.bank_data else "")
                )
                db_manager.log_audit(
                    doc_type=doc_type.value,
                    confidence=confidence,
                    full_name=full_name,
                    doc_num=doc_num,
                    is_expired=audit.id_data.is_expired if audit.id_data else False,
                    mismatch=audit.name_mismatch_detected,
                    score=audit.compliance_score,
                    notes=audit.audit_notes,
                )
                audits.append({
                    "filename": uf.name,
                    "doc_type": doc_type.value,
                    "audit":    audit,
                })

            # Global dispatch notice for this member
            global_notice = None
            if audits and not error:
                step += 1
                progress.progress(
                    step / total_steps,
                    text=f"{name} — generating notification…",
                )
                try:
                    global_notice = agent_dispatch.generate_global_notice(
                        audits=audits,
                        reference_name=name,
                        production_title=production_title,
                    )
                except Exception as e:
                    st.error(f"Failed to generate notification for {name}: {str(e)}")

            all_member_results.append({
                "name":    name,
                "role":    member["role"],
                "audits":  audits,
                "notice":  global_notice,
                "error":   error,
            })

        progress.progress(1.0, text="Done.")
        st.session_state["last_results"] = all_member_results

    # ── Display results (persisted in session state) ──────────────────────────
    if "last_results" in st.session_state:
        results = st.session_state["last_results"]

        st.markdown("---")
        st.markdown("## Production Report")

        # ── Summary table ─────────────────────────────────────────────────────
        def _has_real_anomaly(audits):
            """True only for genuine issues: expired ID or RIB name fraud."""
            for a in audits:
                audit = a["audit"]
                if audit.id_data and audit.id_data.is_expired:
                    return True
                # mismatch only counts as fraud when it's on a bank document
                if audit.bank_data and audit.name_mismatch_detected:
                    return True
            return False

        for res in results:
            if res["error"] or not res["audits"]:
                continue
            score = sum(a["audit"].compliance_score for a in res["audits"]) / len(res["audits"])
            anomaly = _has_real_anomaly(res["audits"])
            badge = (
                '<span class="badge-err">Incomplete</span>'
                if anomaly else
                '<span class="badge-ok">Compliant</span>'
            )
            st.markdown(
                f"{badge} &nbsp; **{res['name']}** &nbsp;"
                f"<span style='color:#555560;font-size:12px;'>{res['role']}</span> &nbsp;"
                f"<span style='color:#8E8E93;'>{score * 100:.0f}%</span>",
                unsafe_allow_html=True,
            )

        st.markdown("---")

        # ── Per-member detailed report ─────────────────────────────────────────
        for res in results:
            name = res["name"]

            if res["error"]:
                with st.expander(f"⚠  {name} — Error", expanded=True):
                    st.error(res["error"])
                continue

            if not res["audits"]:
                continue

            score   = sum(a["audit"].compliance_score for a in res["audits"]) / len(res["audits"])
            anomaly = _has_real_anomaly(res["audits"])
            icon = "🔴" if anomaly else "🟢"

            with st.expander(
                f"{icon}  {name}  ·  {res['role']}  ·  {score * 100:.0f}%",
                expanded=bool(anomaly),
            ):
                # Per-document breakdown
                for item in res["audits"]:
                    audit = item["audit"]
                    # doc-level anomaly: expired ID or RIB fraud only
                    doc_anomaly = bool(
                        (audit.id_data and audit.id_data.is_expired) or
                        (audit.bank_data and audit.name_mismatch_detected)
                    )
                    st.markdown(
                        f"**{item['filename']}** &nbsp;"
                        f"<span style='color:#555560;font-size:11px;'>{item['doc_type']}</span>",
                        unsafe_allow_html=True,
                    )

                    if audit.id_data:
                        st.markdown(f"Name: `{audit.id_data.full_name}` · "
                                    f"N° `{audit.id_data.document_number}` · "
                                    f"Expiry `{audit.id_data.expiration_date}`")
                        if audit.id_data.is_expired:
                            st.markdown(
                                '<span style="color:#E50914;font-size:12px;">⚠ Expired document</span>',
                                unsafe_allow_html=True,
                            )

                    if audit.bank_data:
                        st.markdown(f"Holder: `{audit.bank_data.account_holder_name}` · "
                                    f"IBAN: `{audit.bank_data.iban_or_account_num}`")
                        if audit.name_mismatch_detected:
                            st.markdown(
                                f'<span style="color:#E50914;font-size:12px;">'
                                f'⚠ Name mismatch — "{audit.bank_data.account_holder_name}" '
                                f'≠ "{name}"</span>',
                                unsafe_allow_html=True,
                            )

                    if audit.transcribed_text:
                        st.code(audit.transcribed_text, language=None)

                    if doc_anomaly:
                        st.caption(audit.audit_notes)

                    st.markdown("<hr style='margin:0.6rem 0;border-color:#1a1a1d;'>",
                                unsafe_allow_html=True)

                # ── Global dispatch notification ───────────────────────────
                if res["notice"]:
                    notice = res["notice"]

                    st.markdown("<hr style='margin:0.8rem 0;border-color:#1a1a1d;'>",
                                unsafe_allow_html=True)

                    # 1. Badge décision
                    decision_colors = {
                        "VALIDATED": ("#0a2a12", "#30D158"),
                        "PENDING":   ("#1a1500", "#FFD60A"),
                        "BLOCKED":   ("#2a0608", "#E50914"),
                    }
                    bg, fg = decision_colors.get(notice.decision, ("#1e1e22", "#8E8E93"))
                    st.markdown(
                        f'<span style="display:inline-block;background:{bg};color:{fg};'
                        f'border:1px solid {fg};font-size:11px;font-weight:700;'
                        f'letter-spacing:1.5px;padding:3px 10px;border-radius:2px;'
                        f'text-transform:uppercase;">{notice.decision}</span>',
                        unsafe_allow_html=True,
                    )
                    st.markdown("")

                    # 2. Note interne HR
                    st.markdown(
                        '<span style="font-size:10px;font-weight:700;letter-spacing:1.5px;'
                        'color:#3a3a3f;text-transform:uppercase;">Internal HR Note</span>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f'<div style="background:#0d0d0e;border:1px solid #1e1e22;'
                        f'border-radius:4px;padding:0.7rem 1rem;font-size:13px;'
                        f'color:#8E8E93;font-style:italic;">{notice.hr_note}</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown("")

                    # 3. Issues list (si anomalies)
                    if notice.requires_action and notice.issues_found:
                        for issue in notice.issues_found:
                            st.markdown(
                                f'<span style="color:#E50914;font-size:12px;">⚠ {issue}</span>',
                                unsafe_allow_html=True,
                            )
                        st.markdown("")

                    # 4. Email EN / FR avec onglets
                    tab_en, tab_fr = st.tabs(["📧 Email (EN)", "📧 Message (FR)"])
                    with tab_en:
                        st.markdown(f"**{notice.email_subject}**")
                        st.code(notice.message_body, language=None)
                    with tab_fr:
                        st.markdown(f"**{notice.email_subject}**")
                        st.code(notice.message_body_fr, language=None)
