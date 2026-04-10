import os
import json
import streamlit as st
import pandas as pd

from utils import validate_dataframe, substitute_template, COUNTRY_CODES
from whatsapp_sender import WhatsAppSender

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

def _load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def _save_config(data: dict):
    existing = _load_config()
    existing.update(data)
    with open(CONFIG_FILE, "w") as f:
        json.dump(existing, f)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Aurasutra",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Brand CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.aura-header { text-align:center; padding:2rem 0 0.5rem 0; }
.aura-title {
    font-size:3.2rem; font-weight:900; letter-spacing:0.18em;
    background:linear-gradient(90deg,#C9A84C,#f0d080,#C9A84C);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent; background-clip:text;
}
.aura-tagline { font-size:1.05rem; color:#b89cdd; letter-spacing:0.08em; margin-top:-0.4rem; }
.aura-divider { border:none; border-top:1px solid #C9A84C44; margin:1.2rem 0 1.8rem 0; }
.section-label {
    font-size:0.75rem; font-weight:700; letter-spacing:0.12em;
    color:#C9A84C; text-transform:uppercase; margin-bottom:0.3rem;
}
.preview-box {
    background:#2D1B4E; border-left:3px solid #C9A84C; border-radius:6px;
    padding:1rem 1.2rem; font-size:0.95rem; white-space:pre-wrap;
    word-break:break-word; color:#F0E6FF;
}
#MainMenu {visibility:hidden;} footer {visibility:hidden;}
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="aura-header">
    <div class="aura-title">AURASUTRA</div>
    <div class="aura-tagline">Personalized WhatsApp Outreach &nbsp;•&nbsp; Cold Messaging, Automated</div>
</div>
<hr class="aura-divider"/>
""", unsafe_allow_html=True)

with st.expander("About Aurasutra"):
    st.text_area(
        "brand_note", label_visibility="collapsed",
        value="Aurasutra automates personalized WhatsApp outreach for healthcare businesses. "
              "Upload contacts, craft your message, and reach every clinic — fast, personal, zero manual effort.",
        height=80, key="system_prompt",
    )

st.markdown("<br/>", unsafe_allow_html=True)

# ── Session state init ────────────────────────────────────────────────────────
_cfg     = _load_config()
_cc_opts = list(COUNTRY_CODES.keys())
for key, default in [
    ("country_label", _cfg.get("country_label", _cc_opts[0])),
    ("wait_time",     _cfg.get("wait_time", 30)),
    ("inter_delay",   _cfg.get("inter_delay", 5)),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Section 01 — Configuration ───────────────────────────────────────────────
st.markdown('<div class="section-label">01 — Configuration</div>', unsafe_allow_html=True)
cfg_col1, cfg_col2 = st.columns(2)

with cfg_col1:
    country_label = st.selectbox(
        "Default country code (for 10-digit numbers in your contacts)",
        options=_cc_opts, key="country_label",
    )
    _save_config({"country_label": country_label})
    default_cc = COUNTRY_CODES[country_label]

with cfg_col2:
    wait_time = st.number_input(
        "Wait time per message (seconds)",
        min_value=10, max_value=60, value=int(st.session_state["wait_time"]),
        help="Time to wait for each chat to load before sending.",
    )
    inter_delay = st.number_input(
        "Delay between messages (seconds)",
        min_value=2, max_value=60, value=int(st.session_state["inter_delay"]),
        help="Pause between sends to avoid WhatsApp rate-limits.",
    )
    _save_config({"wait_time": wait_time, "inter_delay": inter_delay})

st.markdown("---")

# ── Section 02 — Contacts ─────────────────────────────────────────────────────
st.markdown('<div class="section-label">02 — Contacts</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Upload contacts file", type=["csv", "xlsx", "xls"],
    help="Required columns: mobile, name, clinic_name, location",
)

df = None
if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file, skipinitialspace=True)
        else:
            df = pd.read_excel(uploaded_file, engine="openpyxl")

        df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
        for col in df.select_dtypes(include=["object", "str"]).columns:
            df[col] = df[col].astype(str).str.strip()

        is_valid, errors = validate_dataframe(df)
        if not is_valid:
            for err in errors:
                st.error(err)
            df = None
        else:
            st.success(f"Loaded **{len(df)}** contacts.")
            st.dataframe(df.head(5), width="stretch")
            mc1, mc2 = st.columns(2)
            mc1.metric("Total Contacts", len(df))
            mc2.metric("Columns", ", ".join(df.columns.tolist()))
    except Exception as exc:
        st.error(f"Could not read file: {exc}")
        df = None
else:
    st.caption("No file uploaded yet — download the sample to get started.")
    with open("sample_contacts.csv", "rb") as f:
        st.download_button("Download sample_contacts.csv", data=f,
                           file_name="sample_contacts.csv", mime="text/csv")

st.markdown("---")

# ── Section 03 — Message Template ────────────────────────────────────────────
st.markdown('<div class="section-label">03 — Message Template</div>', unsafe_allow_html=True)

template = st.text_area(
    "Write your message template", height=200, key="template",
    value=(
        "Hi {name},\n\n"
        "I came across {clinic_name} in {location} and wanted to reach out personally.\n\n"
        "We help clinics like yours grow their patient base through smart digital outreach. "
        "Would love to connect and explore if there's a fit.\n\n"
        "— Aurasutra Team"
    ),
)
st.caption("Placeholders: `{name}` `{clinic_name}` `{location}` — any column from your file works.")

st.markdown("---")

# ── Section 04 — Preview ──────────────────────────────────────────────────────
st.markdown('<div class="section-label">04 — Preview</div>', unsafe_allow_html=True)

if st.button("Preview for First Contact", disabled=(df is None)):
    rendered = substitute_template(template, df.iloc[0].to_dict())
    st.markdown(f'<div class="preview-box">{rendered}</div>', unsafe_allow_html=True)
    st.caption(f"Character count: {len(rendered)}")
elif df is None:
    st.caption("Upload contacts first to enable preview.")

st.markdown("---")

# ── Section 05 — Send ─────────────────────────────────────────────────────────
st.markdown('<div class="section-label">05 — Send</div>', unsafe_allow_html=True)

st.info(
    "When you click **Send**:\n"
    "1. WhatsApp Web will open (in headless mode on cloud)\n"
    "2. If not logged in, a QR code will appear below — scan it with your WhatsApp mobile app\n"
    "3. Messages will start sending automatically\n"
    "4. ⚠️ On Streamlit Cloud, you'll need to scan the QR code each time (sessions don't persist)"
)

send_ready = df is not None and template.strip() != ""

if st.button("SEND TO ALL CONTACTS", type="primary", disabled=not send_ready):
    sender = WhatsAppSender(
        wait_time=int(wait_time),
        inter_message_delay=int(inter_delay),
        default_cc=default_cc,
        qr_timeout=90,
    )

    progress_bar        = st.progress(0.0)
    status_text         = st.empty()
    qr_code_placeholder = st.empty()
    results_placeholder = st.empty()
    all_results         = []

    def on_progress(done, total, result):
        all_results.append(result)
        progress_bar.progress(done / total)
        icon = "✅" if result["status"] == "sent" else "❌"
        status_text.markdown(
            f"{icon} **{done}/{total}** — {result['contact']} ({result['number']})"
            + (f" — `{result['error']}`" if result.get("error") else "")
        )
        results_placeholder.dataframe(
            pd.DataFrame(all_results)[["contact", "number", "status", "error"]],
            width="stretch",
        )
    
    def on_qr_code(screenshot_path):
        """Display QR code screenshot for scanning"""
        qr_code_placeholder.image(screenshot_path, caption="Scan this QR code with your WhatsApp mobile app", width=400)

    sender.send_batch(
        df, template,
        progress_callback=on_progress,
        status_cb=lambda msg: status_text.info(msg),
        qr_callback=on_qr_code,
    )

    results_df = pd.DataFrame(all_results)
    st.markdown("### Sending Complete")
    sc1, sc2 = st.columns(2)
    sc1.metric("Sent",   int((results_df["status"] == "sent").sum()))
    sc2.metric("Failed", int((results_df["status"] == "failed").sum()))

    st.download_button(
        "Download Send Report (CSV)",
        data=results_df.to_csv(index=False).encode("utf-8"),
        file_name="aurasutra_report.csv",
        mime="text/csv",
    )

elif df is None:
    st.caption("Upload a contacts file to enable sending.")
