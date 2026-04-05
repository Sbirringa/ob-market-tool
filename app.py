"""
IT Job Market Intelligence — Dashboard Streamlit v3.0
Design: Dark editorial 2026
Miglioramenti v3:
  - Normalizzazione robusta modalita_lavoro e seniority (gestisce varianti raw dal DB)
  - Filtro remoto = 100% remoto, ibrido = misto — semantica precisa
  - Filtro skill con toggle AND / OR
  - Reset pagina automatico al cambio di qualsiasi filtro
  - Paginazione con ellipsis (non salta il layout con molte pagine)
  - KPI: remoto e ibrido separati + esclusione "Non specificata" da città top
  - Filtro città: dropdown con città reali + text fallback
  - Gestione difensiva colonne assenti tramite col_safe()
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from supabase import create_client, Client
import os
import hashlib

# ── Configurazione pagina ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="IT Job Market Italia",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #0a0a0f; color: #e8e6e0; }

[data-testid="stSidebar"] {
    background: #0f0f18 !important;
    border-right: 1px solid #1e1e2e;
}

.menu-hint { font-size: 0.72rem; color: #3d3d5c; margin-bottom: 0.8rem; letter-spacing: 0.04em; }

.main-header {
    font-family: 'DM Serif Display', serif;
    font-size: 3.2rem; font-weight: 400; color: #f0ede6;
    letter-spacing: -0.02em; line-height: 1.1; margin-bottom: 0.2rem;
}
.main-subtitle {
    font-size: 1rem; font-weight: 300; color: #6b6880;
    letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 2rem;
}

.kpi-card {
    background: linear-gradient(135deg, #13131f 0%, #1a1a2e 100%);
    border: 1px solid #1e1e30; border-radius: 16px;
    padding: 1.5rem; position: relative; overflow: hidden;
}
.kpi-card::before {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, #6c63ff, #a78bfa, #818cf8);
}
.kpi-value { font-family: 'DM Serif Display', serif; font-size: 2.6rem; color: #f0ede6; line-height: 1; margin-bottom: 0.4rem; }
.kpi-label { font-size: 0.78rem; color: #6b6880; text-transform: uppercase; letter-spacing: 0.1em; font-weight: 500; }
.kpi-sub   { font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; color: #a78bfa; margin-top: 0.5rem; }

.badge { display: inline-block; padding: 0.2rem 0.65rem; border-radius: 20px; font-size: 0.72rem; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }
.badge-junior      { background: #1a2e1a; color: #4ade80; border: 1px solid #166534; }
.badge-mid         { background: #1e2a3a; color: #60a5fa; border: 1px solid #1e3a5f; }
.badge-senior      { background: #2d1e3a; color: #c084fc; border: 1px solid #581c87; }
.badge-unspecified { background: #1e1e2e; color: #94a3b8; border: 1px solid #334155; }

.badge-remoto  { background: #1a2e26; color: #34d399; border: 1px solid #065f46; }
.badge-ibrido  { background: #2a2010; color: #fb923c; border: 1px solid #92400e; }
.badge-sede    { background: #1e1e2e; color: #94a3b8; border: 1px solid #334155; }

.section-title {
    font-family: 'DM Serif Display', serif; font-size: 1.5rem; color: #f0ede6;
    margin: 2rem 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 1px solid #1e1e2e;
}

.offerta-card {
    background: #13131f; border: 1px solid #1e1e2e;
    border-radius: 12px; padding: 1.2rem 1.4rem; margin-bottom: 0.8rem;
}
.offerta-card:hover { border-color: #3d3d6b; }
.offerta-titolo  { font-size: 1rem; font-weight: 600; color: #f0ede6; margin-bottom: 0.3rem; }
.offerta-azienda { font-size: 0.85rem; color: #6b6880; }
.offerta-citta   { font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: #a78bfa; }

.hint-pill {
    display: inline-block; font-size: 0.68rem; color: #4b5563;
    background: #111118; border: 1px solid #1f2937;
    border-radius: 20px; padding: 0.15rem 0.55rem; margin-top: 0.3rem;
}

.stTabs [data-baseweb="tab-list"] { background: #0f0f18; border-bottom: 1px solid #1e1e2e; gap: 0; }
.stTabs [data-baseweb="tab"] { color: #6b6880; font-size: 0.88rem; font-weight: 500; padding: 0.75rem 1.2rem; border-radius: 0; }
.stTabs [aria-selected="true"] { color: #f0ede6 !important; border-bottom: 2px solid #a78bfa !important; background: transparent !important; }

::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #0a0a0f; }
::-webkit-scrollbar-thumb { background: #2a2a3e; border-radius: 4px; }

.filtri-sezione { font-size: 0.7rem; color: #3d3d5c; text-transform: uppercase; letter-spacing: 0.1em; margin: 1rem 0 0.4rem 0; }
.footer { font-size: 0.75rem; color: #3d3d5c; text-align: center; padding: 2rem 0 1rem 0; letter-spacing: 0.05em; }
</style>
""", unsafe_allow_html=True)

# ── Connessione Supabase ───────────────────────────────────────────────────────
@st.cache_resource
def get_supabase() -> Client:
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except (KeyError, FileNotFoundError):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("Credenziali Supabase non trovate")
    return create_client(url, key)

# ── Normalizzazione valori raw dal DB ──────────────────────────────────────────
_MODALITA_MAP: dict[str, str] = {
    # remoto puro
    "remoto": "remoto", "remote": "remoto", "full remote": "remoto",
    "fully remote": "remoto", "100% remoto": "remoto", "100% remote": "remoto",
    "smart working": "remoto", "smartworking": "remoto",
    "da remoto": "remoto", "telelavoro": "remoto",
    # ibrido
    "ibrido": "ibrido", "hybrid": "ibrido", "ibrida": "ibrido",
    "misto": "ibrido", "flessibile": "ibrido", "flexible": "ibrido",
    "parzialmente remoto": "ibrido", "partial remote": "ibrido",
    "smart working parziale": "ibrido",
    # in sede
    "sede": "sede", "in sede": "sede", "on site": "sede",
    "onsite": "sede", "on-site": "sede", "in loco": "sede",
    "presenza": "sede", "in presenza": "sede", "ufficio": "sede",
}

_SENIORITY_MAP: dict[str, str] = {
    # junior
    "junior": "junior", "jr": "junior", "jr.": "junior",
    "stage": "junior", "stagista": "junior", "tirocinio": "junior",
    "neolaureato": "junior", "entry level": "junior", "entry": "junior",
    "graduate": "junior", "intern": "junior",
    # mid
    "mid": "mid", "middle": "mid", "medior": "mid",
    "con esperienza": "mid", "experienced": "mid",
    # senior
    "senior": "senior", "sr": "senior", "sr.": "senior",
    "lead": "senior", "tech lead": "senior", "principal": "senior",
    "manager": "senior", "head": "senior", "architect": "senior",
    "staff": "senior",
}

def _norm(raw: str, mapping: dict[str, str], default: str) -> str:
    if not isinstance(raw, str) or not raw.strip():
        return default
    return mapping.get(raw.strip().lower(), default)

def normalizza_modalita(val: str) -> str:
    return _norm(val, _MODALITA_MAP, "non specificato")

def normalizza_seniority(val: str) -> str:
    return _norm(val, _SENIORITY_MAP, "unspecified")

# ── Caricamento + normalizzazione dati ────────────────────────────────────────
@st.cache_data(ttl=3600)
def carica_dati():
    supabase = get_supabase()
    offerte_raw = supabase.table("offerte").select("*").execute().data
    skill_raw   = supabase.table("skill_richieste").select("*").execute().data

    df       = pd.DataFrame(offerte_raw)
    df_skill = pd.DataFrame(skill_raw)

    if not df.empty:
        if "data_pubblicazione" in df.columns:
            df["data_pubblicazione"] = pd.to_datetime(
                df["data_pubblicazione"], utc=True, errors="coerce"
            )
        # Modalità lavoro normalizzata
        if "modalita_lavoro" in df.columns:
            df["modalita_lavoro"] = df["modalita_lavoro"].apply(normalizza_modalita)
        else:
            df["modalita_lavoro"] = "non specificato"

        # Seniority normalizzata
        if "seniority" in df.columns:
            df["seniority"] = df["seniority"].apply(normalizza_seniority)
        else:
            df["seniority"] = "unspecified"

        # Città: strip + title case + placeholder per vuoti
        if "città" in df.columns:
            df["città"] = df["città"].astype(str).str.strip().str.title()
            df["città"] = df["città"].replace({"": "Non Specificata", "Nan": "Non Specificata", "None": "Non Specificata"})
            df["città"] = df["città"].fillna("Non Specificata")

    return df, df_skill

# ── Costanti ───────────────────────────────────────────────────────────────────
PLOTLY_BASE = dict(
    paper_bgcolor="#0a0a0f", plot_bgcolor="#0a0a0f",
    font=dict(family="DM Sans", color="#94a3b8", size=12),
    margin=dict(l=20, r=20, t=40, b=20),
    colorway=["#a78bfa", "#818cf8", "#60a5fa", "#34d399", "#f472b6", "#fb923c"],
)
AXIS_X = dict(gridcolor="#1e1e2e", linecolor="#1e1e2e", tickfont=dict(color="#6b6880"))
AXIS_Y = dict(gridcolor="#1e1e2e", linecolor="#1e1e2e", tickfont=dict(color="#6b6880"))

SENIORITY_COLORS = {
    "junior": "#4ade80", "mid": "#60a5fa",
    "senior": "#c084fc", "unspecified": "#94a3b8",
}
MODALITA_COLORS = {
    "remoto": "#34d399", "ibrido": "#fb923c",
    "sede": "#94a3b8", "non specificato": "#374151",
}
SENIORITY_LABELS = {
    "junior":      "Junior / Stage / Neolaureato",
    "mid":         "Middle / Con esperienza",
    "senior":      "Senior / Lead / Manager",
    "unspecified": "Non specificato",
}
MODALITA_LABELS = {
    "remoto":          "🌐 Solo Remoto (100%)",
    "ibrido":          "🔀 Ibrido (ufficio + remoto)",
    "sede":            "🏢 Solo In Sede",
    "non specificato": "❓ Non specificato",
}
RUOLI = {
    "🌐 Tutte":               None,
    "📊 Data Analyst":        "Data Analyst",
    "⚙️ Data Engineer":       "Data Engineer",
    "💼 Business Analyst":    "Business Analyst",
    "📋 Analista Funzionale": "Analista Funzionale",
    "🔧 ERP Consultant":      "ERP Consultant",
    "💻 IT Consultant":       "IT Consultant",
    "📈 BI Developer":        "BI Developer",
    "🤖 ML Engineer":         "ML Engineer",
    "🧠 AI Solutions":        "AI Solutions",
    "📁 Project Manager":     "Project Manager",
    "⚙️ Operations Analyst":  "Operations Analyst",
}

PER_PAGINA = 30
CITTA_NON_VALIDE = {"Non Specificata", "Non specificata", "", "Nan", "None"}

# ── Helpers ───────────────────────────────────────────────────────────────────
def col_safe(df: pd.DataFrame, col: str) -> bool:
    """True se la colonna esiste e non è tutta NaN."""
    return col in df.columns and not df[col].isna().all()

def badge_seniority(seniority: str) -> str:
    s = str(seniority).lower()
    cls = f"badge-{s}" if s in ("junior", "mid", "senior", "unspecified") else "badge-unspecified"
    label = s if s != "unspecified" else "n/d"
    return f'<span class="badge {cls}">{label}</span>'

def badge_modalita(modalita: str) -> str:
    m = str(modalita).lower()
    if m == "remoto": return '<span class="badge badge-remoto">🌐 remoto</span>'
    if m == "ibrido": return '<span class="badge badge-ibrido">🔀 ibrido</span>'
    if m == "sede":   return '<span class="badge badge-sede">🏢 sede</span>'
    return ""

def pagine_visibili(corrente: int, totale: int, delta: int = 2) -> list:
    """Sequenza di numeri pagina con None come segnaposto per '…'."""
    pagine = set()
    pagine.add(1)
    pagine.add(totale)
    for i in range(max(2, corrente - delta), min(totale, corrente + delta + 1)):
        pagine.add(i)
    result = sorted(pagine)
    out = []
    prev = None
    for p in result:
        if prev is not None and p - prev > 1:
            out.append(None)
        out.append(p)
        prev = p
    return out

def filtri_hash(periodo, seniority_sel, modalita_sel, citta_key, skill_sel, skill_mode) -> str:
    raw = f"{periodo}|{sorted(seniority_sel)}|{sorted(modalita_sel)}|{citta_key}|{sorted(skill_sel)}|{skill_mode}"
    return hashlib.md5(raw.encode()).hexdigest()[:8]

# ── Caricamento dati ───────────────────────────────────────────────────────────
try:
    df, df_skill = carica_dati()
    dati_ok = not df.empty
except Exception as e:
    st.error(f"Errore connessione Supabase: {e}")
    dati_ok = False
    df = pd.DataFrame()
    df_skill = pd.DataFrame()

# ── SIDEBAR ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="padding: 1rem 0 1.5rem 0;">
        <div style="font-family: 'DM Serif Display', serif; font-size: 1.4rem; color: #f0ede6;">📊 Job Market</div>
        <div style="font-size: 0.72rem; color: #6b6880; text-transform: uppercase; letter-spacing: 0.1em; margin-top: 0.3rem;">Italia · Settore IT</div>
    </div>
    """, unsafe_allow_html=True)

    # Periodo
    st.markdown('<div class="filtri-sezione">📅 Periodo</div>', unsafe_allow_html=True)
    periodo = st.selectbox(
        "Periodo",
        options=["Ultime 24 ore", "Ultimi 7 giorni", "Ultimi 30 giorni", "Ultimi 90 giorni", "Tutto"],
        index=4,
        label_visibility="collapsed",
        help="L'ETL si aggiorna ogni mattina alle 08:00. 'Ultime 24 ore' mostra pochissimi risultati nelle ore serali.",
    )

    # Seniority
    st.markdown('<div class="filtri-sezione">🎯 Livello esperienza</div>', unsafe_allow_html=True)
    seniority_sel = st.multiselect(
        "Livello",
        options=list(SENIORITY_LABELS.keys()),
        default=[],
        format_func=lambda x: SENIORITY_LABELS[x],
        placeholder="Tutti i livelli",
        label_visibility="collapsed",
    )

    # Modalità lavoro
    st.markdown('<div class="filtri-sezione">🏠 Modalità di lavoro</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hint-pill">Remoto = 100% da casa · Ibrido = misto ufficio+casa</div>',
        unsafe_allow_html=True,
    )
    modalita_sel = st.multiselect(
        "Modalità",
        options=list(MODALITA_LABELS.keys()),
        default=[],
        format_func=lambda x: MODALITA_LABELS[x],
        placeholder="Tutte le modalità",
        label_visibility="collapsed",
    )

    # Città — dropdown con tutte le città reali + ricerca libera come fallback
    st.markdown('<div class="filtri-sezione">📍 Città</div>', unsafe_allow_html=True)
    citta_options = ["Tutte"]
    if dati_ok and col_safe(df, "città"):
        citta_valide = sorted([
            c for c in df["città"].dropna().unique()
            if c not in CITTA_NON_VALIDE
        ])
        citta_options += citta_valide
    citta_sel = st.selectbox(
        "Seleziona città",
        options=citta_options,
        index=0,
        label_visibility="collapsed",
    )
    citta_testo = st.text_input(
        "Oppure cerca (testo libero):",
        placeholder="Es: Bergamo, Padova...",
        label_visibility="visible",
        help="Usato solo se 'Tutte' è selezionato sopra.",
    )

    # Skill + AND/OR
    st.markdown('<div class="filtri-sezione">🔧 Skill richieste</div>', unsafe_allow_html=True)
    skill_options = []
    if not df_skill.empty and "skill" in df_skill.columns:
        skill_options = sorted(df_skill["skill"].dropna().unique().tolist())
    skill_sel = st.multiselect(
        "Skill",
        options=skill_options,
        placeholder="Es: Python, SQL, Power BI...",
        label_visibility="collapsed",
    )
    if skill_sel:
        skill_mode = st.radio(
            "Logica di ricerca skill:",
            options=["Almeno una (OR)", "Tutte le skill (AND)"],
            index=0,
            horizontal=True,
        )
    else:
        skill_mode = "Almeno una (OR)"

    st.markdown("---")
    if st.button("🔄 Aggiorna dati", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    n_filtri = sum([
        bool(seniority_sel),
        bool(modalita_sel),
        citta_sel != "Tutte",
        bool(citta_testo.strip()),
        bool(skill_sel),
        periodo != "Tutto",
    ])
    if n_filtri > 0:
        st.markdown(
            f'<div style="font-size:0.75rem; color:#a78bfa; text-align:center; margin-top:0.5rem;">'
            f'{n_filtri} filtro{"i" if n_filtri > 1 else ""} attivo{"i" if n_filtri > 1 else ""}'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown(
        '<div class="footer">Dati aggiornati ogni mattina alle 08:00<br>via GitHub Actions + JSearch API</div>',
        unsafe_allow_html=True,
    )

# ── HEADER ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="menu-hint">← Apri il menù laterale per filtrare i risultati</div>
<div class="main-header">Mercato IT Italiano</div>
<div class="main-subtitle">Intelligence sulle offerte di lavoro · Aggiornamento quotidiano</div>
""", unsafe_allow_html=True)

# ── FILTRAGGIO DATI ────────────────────────────────────────────────────────────
if dati_ok:
    df_f = df.copy()

    # Periodo
    if col_safe(df_f, "data_pubblicazione"):
        oggi = pd.Timestamp.now(tz="UTC")
        mappa_periodo = {
            "Ultime 24 ore":    pd.Timedelta(hours=24),
            "Ultimi 7 giorni":  pd.Timedelta(days=7),
            "Ultimi 30 giorni": pd.Timedelta(days=30),
            "Ultimi 90 giorni": pd.Timedelta(days=90),
        }
        if periodo in mappa_periodo:
            df_f = df_f[df_f["data_pubblicazione"] >= oggi - mappa_periodo[periodo]]

    # Seniority
    if seniority_sel:
        df_f = df_f[df_f["seniority"].isin(seniority_sel)]

    # Modalità lavoro (semantica precisa: remoto ≠ ibrido)
    if modalita_sel:
        df_f = df_f[df_f["modalita_lavoro"].isin(modalita_sel)]

    # Città: selectbox ha priorità; text fallback se selectbox = "Tutte"
    if citta_sel != "Tutte" and col_safe(df_f, "città"):
        df_f = df_f[df_f["città"] == citta_sel]
    elif citta_testo.strip() and col_safe(df_f, "città"):
        df_f = df_f[df_f["città"].str.contains(citta_testo.strip(), case=False, na=False)]

    # Skill (AND / OR)
    if skill_sel and not df_skill.empty and "offerta_id" in df_skill.columns:
        if "AND" in skill_mode:
            ids_validi: set | None = None
            for skill in skill_sel:
                ids_skill = set(df_skill[df_skill["skill"] == skill]["offerta_id"].tolist())
                ids_validi = ids_skill if ids_validi is None else ids_validi & ids_skill
            df_f = df_f[df_f["id"].isin(ids_validi or [])]
        else:
            ids_con_skill = df_skill[df_skill["skill"].isin(skill_sel)]["offerta_id"].unique()
            df_f = df_f[df_f["id"].isin(ids_con_skill)]

    skill_correnti = (
        df_skill[df_skill["offerta_id"].isin(df_f["id"].tolist())]
        if not df_skill.empty and "offerta_id" in df_skill.columns
        else pd.DataFrame()
    )

    # Reset pagina automatico se i filtri sono cambiati
    h = filtri_hash(periodo, seniority_sel, modalita_sel,
                    citta_sel + citta_testo, skill_sel, skill_mode)
    if st.session_state.get("_filtri_hash") != h:
        for k in list(st.session_state.keys()):
            if k.startswith("_pg_"):
                st.session_state[k] = 1
        st.session_state["_filtri_hash"] = h

else:
    df_f = pd.DataFrame()
    skill_correnti = pd.DataFrame()

# ── KPI ────────────────────────────────────────────────────────────────────────
n_offerte = len(df_f)

citta_top = "—"
if n_offerte > 0 and col_safe(df_f, "città"):
    citta_valide_top = df_f[~df_f["città"].isin(CITTA_NON_VALIDE)]["città"]
    if not citta_valide_top.empty:
        citta_top = citta_valide_top.value_counts().index[0]

skill_top = skill_correnti["skill"].value_counts().index[0] if not skill_correnti.empty else "—"

pct_remoto = pct_ibrido = 0
if n_offerte > 0 and col_safe(df_f, "modalita_lavoro"):
    pct_remoto = round(len(df_f[df_f["modalita_lavoro"] == "remoto"]) / n_offerte * 100)
    pct_ibrido = round(len(df_f[df_f["modalita_lavoro"] == "ibrido"]) / n_offerte * 100)

kpis = [
    (str(n_offerte),   "Offerte trovate",     periodo.lower()),
    (citta_top,        "Città più attiva",    "maggior concentrazione"),
    (skill_top,        "Skill più richiesta", "nelle offerte filtrate"),
    (f"{pct_remoto}%", "Solo Remoto",         "100% da casa"),
    (f"{pct_ibrido}%", "Ibrido",              "ufficio + remoto"),
]
cols_kpi = st.columns(5)
for col, (val, label, sub) in zip(cols_kpi, kpis):
    with col:
        st.markdown(
            f'<div class="kpi-card">'
            f'<div class="kpi-value">{val}</div>'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-sub">{sub}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# ── TABS per ruolo ─────────────────────────────────────────────────────────────
tab_attive: dict[str, str | None] = {}
for nome, ruolo in RUOLI.items():
    if ruolo is None:
        tab_attive[nome] = ruolo
        continue
    if dati_ok and col_safe(df_f, "categoria_ruolo"):
        if len(df_f[df_f["categoria_ruolo"] == ruolo]) > 0:
            tab_attive[nome] = ruolo

tabs = st.tabs(list(tab_attive.keys()))

for tab, (tab_nome, ruolo_filter) in zip(tabs, tab_attive.items()):
    with tab:
        df_tab = df_f.copy()
        if ruolo_filter and col_safe(df_tab, "categoria_ruolo"):
            df_tab = df_tab[df_tab["categoria_ruolo"] == ruolo_filter]

        skill_tab = (
            skill_correnti[skill_correnti["offerta_id"].isin(df_tab["id"].tolist())]
            if not skill_correnti.empty and "offerta_id" in skill_correnti.columns
            else pd.DataFrame()
        )

        if df_tab.empty:
            st.markdown("""
            <div style="text-align:center; padding: 3rem; color: #3d3d5c;">
                <div style="font-size: 2rem; margin-bottom: 1rem;">🔍</div>
                <div style="font-size: 0.9rem;">Nessuna offerta trovata con i filtri selezionati</div>
            </div>
            """, unsafe_allow_html=True)
            continue

        # ── Riga 1: Skill + Seniority ──────────────────────────────────────────
        col_g1, col_g2 = st.columns([1.2, 1])

        with col_g1:
            st.markdown('<div class="section-title">🔧 Skill più richieste</div>', unsafe_allow_html=True)
            if not skill_tab.empty and "skill" in skill_tab.columns:
                top_skill = skill_tab["skill"].value_counts().head(12).reset_index()
                top_skill.columns = ["skill", "count"]
                fig_skill = go.Figure(go.Bar(
                    x=top_skill["count"], y=top_skill["skill"], orientation="h",
                    marker=dict(
                        color=top_skill["count"],
                        colorscale=[[0, "#2d1e3a"], [0.5, "#6d28d9"], [1, "#a78bfa"]],
                        line=dict(color="rgba(0,0,0,0)", width=0),
                    ),
                    text=top_skill["count"], textposition="outside",
                    textfont=dict(color="#6b6880", size=11),
                ))
                fig_skill.update_layout(
                    **PLOTLY_BASE, height=380, showlegend=False,
                    xaxis=dict(gridcolor="#1e1e2e", linecolor="#0a0a0f", tickfont=dict(color="#6b6880")),
                    yaxis=dict(autorange="reversed", gridcolor="#1e1e2e", linecolor="#1e1e2e", tickfont=dict(color="#e8e6e0", size=12)),
                )
                st.plotly_chart(fig_skill, use_container_width=True, config={"displayModeBar": False}, key=f"skill_{tab_nome}")
            else:
                st.info("Nessuna skill disponibile per questo filtro.")

        with col_g2:
            st.markdown('<div class="section-title">🎯 Distribuzione Seniority</div>', unsafe_allow_html=True)
            if col_safe(df_tab, "seniority"):
                sen_count = df_tab["seniority"].value_counts().reset_index()
                sen_count.columns = ["seniority", "count"]
                colors_sen = [SENIORITY_COLORS.get(s, "#94a3b8") for s in sen_count["seniority"]]
                fig_sen = go.Figure(go.Pie(
                    labels=[SENIORITY_LABELS.get(s, s) for s in sen_count["seniority"]],
                    values=sen_count["count"], hole=0.65,
                    marker=dict(colors=colors_sen, line=dict(color="#0a0a0f", width=3)),
                    textfont=dict(color="#e8e6e0", size=11), textinfo="label+percent",
                ))
                fig_sen.update_layout(
                    **PLOTLY_BASE, height=380, showlegend=False,
                    annotations=[dict(
                        text=f"<b>{len(df_tab)}</b><br><span style='font-size:10px'>offerte</span>",
                        x=0.5, y=0.5, font_size=20, font_color="#f0ede6", showarrow=False,
                    )],
                )
                st.plotly_chart(fig_sen, use_container_width=True, config={"displayModeBar": False}, key=f"sen_{tab_nome}")

        # ── Riga 2: Città + Modalità lavoro ───────────────────────────────────
        col_g3, col_g4 = st.columns([1, 1])

        with col_g3:
            st.markdown('<div class="section-title">📍 Offerte per Città</div>', unsafe_allow_html=True)
            if col_safe(df_tab, "città"):
                citta_count = (
                    df_tab[~df_tab["città"].isin(CITTA_NON_VALIDE)]["città"]
                    .value_counts().head(10).reset_index()
                )
                citta_count.columns = ["città", "count"]
                if not citta_count.empty:
                    fig_citta = go.Figure(go.Bar(
                        x=citta_count["città"], y=citta_count["count"],
                        marker=dict(color=citta_count["count"], colorscale=[[0, "#1e2a3a"], [1, "#60a5fa"]]),
                        text=citta_count["count"], textposition="outside",
                        textfont=dict(color="#6b6880", size=11),
                    ))
                    fig_citta.update_layout(
                        **PLOTLY_BASE, height=320, showlegend=False,
                        xaxis=dict(gridcolor="#1e1e2e", linecolor="#0a0a0f", tickfont=dict(color="#e8e6e0", size=11), tickangle=-30),
                        yaxis=dict(gridcolor="#1e1e2e", linecolor="#1e1e2e", tickfont=dict(color="#6b6880")),
                    )
                    st.plotly_chart(fig_citta, use_container_width=True, config={"displayModeBar": False}, key=f"citta_{tab_nome}")

        with col_g4:
            st.markdown('<div class="section-title">🏠 Modalità di Lavoro</div>', unsafe_allow_html=True)
            if col_safe(df_tab, "modalita_lavoro"):
                # Escludi "non specificato" dal grafico se ci sono altri dati
                df_mod = df_tab[df_tab["modalita_lavoro"] != "non specificato"]
                if df_mod.empty:
                    df_mod = df_tab
                mod_count = df_mod["modalita_lavoro"].value_counts().reset_index()
                mod_count.columns = ["modalita", "count"]
                colors_mod = [MODALITA_COLORS.get(m, "#374151") for m in mod_count["modalita"]]
                labels_mod = [MODALITA_LABELS.get(m, m) for m in mod_count["modalita"]]
                fig_mod = go.Figure(go.Pie(
                    labels=labels_mod, values=mod_count["count"], hole=0.55,
                    marker=dict(colors=colors_mod, line=dict(color="#0a0a0f", width=3)),
                    textfont=dict(color="#e8e6e0", size=11), textinfo="label+percent",
                ))
                fig_mod.update_layout(**PLOTLY_BASE, height=320, showlegend=False)
                st.plotly_chart(fig_mod, use_container_width=True, config={"displayModeBar": False}, key=f"mod_{tab_nome}")

        # ── Riga 3: Trend settimanale ──────────────────────────────────────────
        st.markdown('<div class="section-title">📈 Trend Settimanale</div>', unsafe_allow_html=True)
        if col_safe(df_tab, "data_pubblicazione"):
            df_trend = df_tab.dropna(subset=["data_pubblicazione"]).copy()
            df_trend["settimana"] = df_trend["data_pubblicazione"].dt.to_period("W").dt.start_time
            trend = df_trend.groupby("settimana").size().reset_index(name="count").sort_values("settimana")
            if len(trend) > 1:
                fig_trend = go.Figure()
                fig_trend.add_trace(go.Scatter(
                    x=trend["settimana"], y=trend["count"],
                    mode="lines+markers",
                    line=dict(color="#a78bfa", width=2.5, shape="spline"),
                    marker=dict(color="#a78bfa", size=6, line=dict(color="#0a0a0f", width=2)),
                    fill="tozeroy", fillcolor="rgba(167, 139, 250, 0.08)",
                ))
                fig_trend.update_layout(**PLOTLY_BASE, height=220, showlegend=False, xaxis=AXIS_X, yaxis=AXIS_Y)
                st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False}, key=f"trend_{tab_nome}")
            else:
                st.info("Dati insufficienti per il trend (servono almeno 2 settimane).")

        # ── Lista offerte ──────────────────────────────────────────────────────
        st.markdown(
            f'<div class="section-title">📋 Lista Offerte '
            f'<span style="color:#a78bfa; font-size:1.1rem; font-weight:600;">{len(df_tab)}</span> '
            f'<span style="color:#6b6880; font-size:1rem;">risultati</span></div>',
            unsafe_allow_html=True,
        )

        ordina_per = st.selectbox(
            "Ordina per",
            options=["Data (più recente)", "Data (più vecchia)", "Azienda A→Z"],
            key=f"ord_{tab_nome}",
            label_visibility="collapsed",
        )

        if ordina_per == "Data (più recente)" and col_safe(df_tab, "data_pubblicazione"):
            df_sorted = df_tab.sort_values("data_pubblicazione", ascending=False)
        elif ordina_per == "Data (più vecchia)" and col_safe(df_tab, "data_pubblicazione"):
            df_sorted = df_tab.sort_values("data_pubblicazione", ascending=True)
        elif col_safe(df_tab, "azienda"):
            df_sorted = df_tab.sort_values("azienda", ascending=True)
        else:
            df_sorted = df_tab.copy()

        # Paginazione
        totale          = len(df_sorted)
        n_pagine        = max(1, -(-totale // PER_PAGINA))
        pag_key         = f"_pg_{tab_nome}"
        if pag_key not in st.session_state:
            st.session_state[pag_key] = 1
        pagina_corrente = max(1, min(st.session_state[pag_key], n_pagine))
        inizio          = (pagina_corrente - 1) * PER_PAGINA
        df_show         = df_sorted.iloc[inizio: inizio + PER_PAGINA]

        # Rendering offerte
        for _, row in df_show.iterrows():
            titolo    = row.get("titolo") or "N/D"
            azienda   = row.get("azienda") or "N/D"
            citta_r   = row.get("città") or "N/D"
            seniority = row.get("seniority") or "unspecified"
            modalita  = row.get("modalita_lavoro") or "non specificato"
            url       = row.get("url") or ""
            data_pub  = row.get("data_pubblicazione")
            categoria = row.get("categoria_ruolo") or ""

            data_str  = data_pub.strftime("%d %b %Y") if pd.notna(data_pub) else "—"
            link_html = (
                f'<a href="{url}" target="_blank" '
                f'style="color:#a78bfa; text-decoration:none; font-size:0.82rem; font-weight:500;">'
                f'→ Candidati</a>'
                if url else ""
            )
            st.markdown(
                f'<div class="offerta-card">'
                f'<div style="display:flex; justify-content:space-between; align-items:flex-start;">'
                f'<div style="flex:1;">'
                f'<div class="offerta-titolo">{titolo}</div>'
                f'<div class="offerta-azienda">{azienda}</div>'
                f'<div style="margin-top:0.6rem; display:flex; gap:0.4rem; align-items:center; flex-wrap:wrap;">'
                f'{badge_seniority(seniority)}'
                f'{badge_modalita(modalita)}'
                f'<span class="offerta-citta">📍 {citta_r}</span>'
                f'<span style="font-family:JetBrains Mono; font-size:0.72rem; color:#3d3d5c;">{data_str}</span>'
                f'<span style="font-size:0.72rem; color:#4b5563;">{categoria}</span>'
                f'</div>'
                f'</div>'
                f'<div style="text-align:right; min-width:90px; padding-left:1rem;">{link_html}</div>'
                f'</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Navigazione pagine con ellipsis
        if n_pagine > 1:
            st.markdown("<br>", unsafe_allow_html=True)
            sequenza   = pagine_visibili(pagina_corrente, n_pagine)
            col_widths = [0.6] + [0.45] * len(sequenza) + [0.6]
            nav_cols   = st.columns(col_widths)

            with nav_cols[0]:
                if st.button("←", key=f"prec_{tab_nome}", disabled=pagina_corrente <= 1):
                    st.session_state[pag_key] = pagina_corrente - 1
                    st.rerun()

            for i, p in enumerate(sequenza):
                with nav_cols[i + 1]:
                    if p is None:
                        st.markdown(
                            '<div style="text-align:center; color:#3d3d5c; padding-top:0.4rem;">…</div>',
                            unsafe_allow_html=True,
                        )
                    elif p == pagina_corrente:
                        st.markdown(
                            f'<div style="text-align:center; color:#a78bfa; font-weight:700; '
                            f'font-size:0.9rem; padding-top:0.4rem;">{p}</div>',
                            unsafe_allow_html=True,
                        )
                    else:
                        if st.button(str(p), key=f"pag_{tab_nome}_{p}"):
                            st.session_state[pag_key] = p
                            st.rerun()

            with nav_cols[-1]:
                if st.button("→", key=f"succ_{tab_nome}", disabled=pagina_corrente >= n_pagine):
                    st.session_state[pag_key] = pagina_corrente + 1
                    st.rerun()

            st.markdown(
                f'<div style="text-align:center; color:#6b6880; font-size:0.8rem; margin-top:0.5rem;">'
                f'Pagina {pagina_corrente} di {n_pagine} · {totale} offerte totali</div>',
                unsafe_allow_html=True,
            )

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
    IT Job Market Intelligence · Dati da JSearch API · Aggiornamento automatico ogni mattina alle 08:00
</div>
""", unsafe_allow_html=True)
