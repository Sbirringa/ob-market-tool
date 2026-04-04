"""
IT Job Market Intelligence — Dashboard Streamlit v2.0
Design: Dark editorial 2026
Nuovi filtri: modalità lavoro, periodo esteso, seniority estesa, nuovi ruoli
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from supabase import create_client, Client
import os

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

/* Badge seniority */
.badge { display: inline-block; padding: 0.2rem 0.65rem; border-radius: 20px; font-size: 0.72rem; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; }
.badge-junior      { background: #1a2e1a; color: #4ade80; border: 1px solid #166534; }
.badge-mid         { background: #1e2a3a; color: #60a5fa; border: 1px solid #1e3a5f; }
.badge-senior      { background: #2d1e3a; color: #c084fc; border: 1px solid #581c87; }
.badge-unspecified { background: #1e1e2e; color: #94a3b8; border: 1px solid #334155; }

/* Badge modalità lavoro */
.badge-remoto  { background: #1a2e26; color: #34d399; border: 1px solid #065f46; }
.badge-ibrido  { background: #2a2010; color: #fb923c; border: 1px solid #92400e; }
.badge-sede    { background: #1e1e2e; color: #94a3b8; border: 1px solid #334155; }
.badge-ns      { background: #111118; color: #4b5563; border: 1px solid #1f2937; }

.section-title {
    font-family: 'DM Serif Display', serif; font-size: 1.5rem; color: #f0ede6;
    margin: 2rem 0 1rem 0; padding-bottom: 0.5rem; border-bottom: 1px solid #1e1e2e;
}

.offerta-card {
    background: #13131f; border: 1px solid #1e1e2e;
    border-radius: 12px; padding: 1.2rem 1.4rem; margin-bottom: 0.8rem;
    transition: border-color 0.2s;
}
.offerta-card:hover { border-color: #3d3d6b; }
.offerta-titolo  { font-size: 1rem; font-weight: 600; color: #f0ede6; margin-bottom: 0.3rem; }
.offerta-azienda { font-size: 0.85rem; color: #6b6880; }
.offerta-citta   { font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: #a78bfa; }

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

@st.cache_data(ttl=3600)
def carica_dati():
    supabase = get_supabase()
    offerte_raw = supabase.table("offerte").select("*").execute().data
    skill_raw   = supabase.table("skill_richieste").select("*").execute().data
    df       = pd.DataFrame(offerte_raw)
    df_skill = pd.DataFrame(skill_raw)
    if not df.empty and "data_pubblicazione" in df.columns:
        df["data_pubblicazione"] = pd.to_datetime(df["data_pubblicazione"], utc=True, errors="coerce")
    # Gestisci colonna modalita_lavoro (potrebbe non esistere in DB vecchi)
    if not df.empty and "modalita_lavoro" not in df.columns:
        df["modalita_lavoro"] = "non specificato"
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

# Label leggibili per seniority
SENIORITY_LABELS = {
    "junior":      "Junior / Stage / Neolaureato",
    "mid":         "Middle / Con esperienza",
    "senior":      "Senior / Lead / Manager",
    "unspecified": "Non specificato",
}

MODALITA_LABELS = {
    "remoto":          "🌐 Remoto / Smart Working",
    "ibrido":          "🔀 Ibrido / Flessibile",
    "sede":            "🏢 In sede",
    "non specificato": "❓ Non specificato",
}

# Tutti i ruoli disponibili (aggiornati con ETL v2)
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

def badge_seniority(seniority: str) -> str:
    s = str(seniority).lower()
    cls = f"badge-{s}" if s in ["junior", "mid", "senior", "unspecified"] else "badge-unspecified"
    label = s if s != "unspecified" else "n/d"
    return f'<span class="badge {cls}">{label}</span>'

def badge_modalita(modalita: str) -> str:
    m = str(modalita).lower()
    icons = {"remoto": "🌐", "ibrido": "🔀", "sede": "🏢", "non specificato": ""}
    if m == "remoto":   return f'<span class="badge badge-remoto">🌐 remoto</span>'
    if m == "ibrido":   return f'<span class="badge badge-ibrido">🔀 ibrido</span>'
    if m == "sede":     return f'<span class="badge badge-sede">🏢 sede</span>'
    return ""

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

    # ── Periodo ────────────────────────────────────────────────────────────────
    st.markdown('<div class="filtri-sezione">📅 Periodo</div>', unsafe_allow_html=True)
    periodo = st.selectbox(
        "Periodo pubblicazione",
        options=["Ultime 24 ore", "Ultimi 7 giorni", "Ultimi 30 giorni", "Ultimi 90 giorni", "Tutto"],
        index=4,
        label_visibility="collapsed",
    )

    # ── Seniority ──────────────────────────────────────────────────────────────
    st.markdown('<div class="filtri-sezione">🎯 Livello esperienza</div>', unsafe_allow_html=True)
    seniority_sel = st.multiselect(
        "Livello",
        options=list(SENIORITY_LABELS.keys()),
        default=[],
        format_func=lambda x: SENIORITY_LABELS[x],
        placeholder="Tutti i livelli",
        label_visibility="collapsed",
    )

    # ── Modalità lavoro ────────────────────────────────────────────────────────
    st.markdown('<div class="filtri-sezione">🏠 Modalità di lavoro</div>', unsafe_allow_html=True)
    modalita_sel = st.multiselect(
        "Modalità",
        options=list(MODALITA_LABELS.keys()),
        default=[],
        format_func=lambda x: MODALITA_LABELS[x],
        placeholder="Tutte le modalità",
        label_visibility="collapsed",
    )

    # ── Città ──────────────────────────────────────────────────────────────────
    st.markdown('<div class="filtri-sezione">📍 Città</div>', unsafe_allow_html=True)
    citta_options = ["Tutte"]
    if dati_ok and "città" in df.columns:
        citta_valide = df["città"].dropna().unique().tolist()
        citta_valide = [c for c in citta_valide if c not in ["Non specificata", ""]]
        citta_options += sorted(citta_valide)
    citta_sel = st.text_input(
    "Città",
    placeholder="Es: Milano, Roma, Torino...",
    label_visibility="collapsed",
)

    # ── Skill ──────────────────────────────────────────────────────────────────
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

    st.markdown("---")
    if st.button("🔄 Aggiorna dati", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Contatore filtri attivi
    n_filtri = sum([
        bool(seniority_sel), bool(modalita_sel),
        citta_sel != "Tutte", bool(skill_sel),
        periodo != "Tutto"
    ])
    if n_filtri > 0:
        st.markdown(f'<div style="font-size:0.75rem; color:#a78bfa; text-align:center;">{n_filtri} filtro{"i" if n_filtri > 1 else ""} attivo{"i" if n_filtri > 1 else ""}</div>', unsafe_allow_html=True)

    st.markdown('<div class="footer">Dati aggiornati ogni mattina<br>via GitHub Actions + JSearch API</div>', unsafe_allow_html=True)

# ── HEADER ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="menu-hint">← Apri il menù laterale per filtrare i risultati</div>
<div class="main-header">Mercato IT Italiano</div>
<div class="main-subtitle">Intelligence sulle offerte di lavoro · Aggiornamento quotidiano</div>
""", unsafe_allow_html=True)

# ── FILTRAGGIO DATI ────────────────────────────────────────────────────────────
if dati_ok:
    df_f = df.copy()

    # Filtro periodo
    if "data_pubblicazione" in df_f.columns:
        oggi = pd.Timestamp.now(tz="UTC")
        df_f["data_pubblicazione"] = pd.to_datetime(df_f["data_pubblicazione"], utc=True, errors="coerce")
        if periodo == "Ultime 24 ore":
            df_f = df_f[df_f["data_pubblicazione"] >= oggi - pd.Timedelta(hours=24)]
        elif periodo == "Ultimi 7 giorni":
            df_f = df_f[df_f["data_pubblicazione"] >= oggi - pd.Timedelta(days=7)]
        elif periodo == "Ultimi 30 giorni":
            df_f = df_f[df_f["data_pubblicazione"] >= oggi - pd.Timedelta(days=30)]
        elif periodo == "Ultimi 90 giorni":
            df_f = df_f[df_f["data_pubblicazione"] >= oggi - pd.Timedelta(days=90)]

    # Filtro seniority
    if seniority_sel:
        df_f = df_f[df_f["seniority"].isin(seniority_sel)]

    # Filtro modalità lavoro
    if modalita_sel and "modalita_lavoro" in df_f.columns:
        df_f = df_f[df_f["modalita_lavoro"].isin(modalita_sel)]

    # Filtro città
    if citta_sel:
        df_f = df_f[df_f["città"].str.contains(citta_sel, case=False, na=False)]
    
    # Filtro skill
    if skill_sel and not df_skill.empty:
        ids_con_skill = df_skill[df_skill["skill"].isin(skill_sel)]["offerta_id"].unique()
        df_f = df_f[df_f["id"].isin(ids_con_skill)]

    skill_correnti = (
        df_skill[df_skill["offerta_id"].isin(df_f["id"].tolist())]
        if not df_skill.empty and "offerta_id" in df_skill.columns
        else pd.DataFrame()
    )
else:
    df_f = pd.DataFrame()
    skill_correnti = pd.DataFrame()

# ── KPI ────────────────────────────────────────────────────────────────────────
n_offerte  = len(df_f)
citta_top  = df_f["città"].value_counts().index[0] if n_offerte > 0 and "città" in df_f.columns else "—"
skill_top  = skill_correnti["skill"].value_counts().index[0] if not skill_correnti.empty else "—"

# Modalità più comune
if n_offerte > 0 and "modalita_lavoro" in df_f.columns:
    mod_counts = df_f["modalita_lavoro"].value_counts()
    pct_remoto = round(len(df_f[df_f["modalita_lavoro"] == "remoto"]) / n_offerte * 100)
else:
    pct_remoto = 0

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="kpi-card"><div class="kpi-value">{len(df_tab)}</div><div class="kpi-label">Offerte trovate</div><div class="kpi-sub">{periodo.lower()}</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="kpi-card"><div class="kpi-value">{citta_top}</div><div class="kpi-label">Città più attiva</div><div class="kpi-sub">maggior concentrazione</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="kpi-card"><div class="kpi-value">{skill_top}</div><div class="kpi-label">Skill più richiesta</div><div class="kpi-sub">nelle offerte filtrate</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="kpi-card"><div class="kpi-value">{pct_remoto}%</div><div class="kpi-label">Offerte Remote/Ibrido</div><div class="kpi-sub">lavoro flessibile</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── TABS per ruolo ─────────────────────────────────────────────────────────────
# Mostra solo tab con almeno 1 offerta (+ sempre "Tutte")
tab_attive = {}
for nome, ruolo in RUOLI.items():
    if ruolo is None:
        tab_attive[nome] = ruolo
        continue
    if dati_ok and "categoria_ruolo" in df_f.columns:
        count = len(df_f[df_f["categoria_ruolo"] == ruolo])
        if count > 0:
            tab_attive[nome] = ruolo

tabs = st.tabs(list(tab_attive.keys()))

for tab, (tab_nome, ruolo_filter) in zip(tabs, tab_attive.items()):
    with tab:
        df_tab = df_f.copy()
        if ruolo_filter and "categoria_ruolo" in df_tab.columns:
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
            if not skill_tab.empty:
                top_skill = skill_tab["skill"].value_counts().head(12).reset_index()
                top_skill.columns = ["skill", "count"]
                fig_skill = go.Figure(go.Bar(
                    x=top_skill["count"], y=top_skill["skill"], orientation="h",
                    marker=dict(color=top_skill["count"], colorscale=[[0, "#2d1e3a"], [0.5, "#6d28d9"], [1, "#a78bfa"]], line=dict(color="rgba(0,0,0,0)", width=0)),
                    text=top_skill["count"], textposition="outside", textfont=dict(color="#6b6880", size=11),
                ))
                fig_skill.update_layout(
                    **PLOTLY_BASE, height=380, showlegend=False,
                    xaxis=dict(gridcolor="#1e1e2e", linecolor="#0a0a0f", tickfont=dict(color="#6b6880")),
                    yaxis=dict(autorange="reversed", gridcolor="#1e1e2e", linecolor="#1e1e2e", tickfont=dict(color="#e8e6e0", size=12)),
                )
                st.plotly_chart(fig_skill, use_container_width=True, config={"displayModeBar": False}, key=f"skill_{tab_nome}")
            else:
                st.info("Nessuna skill disponibile.")

        with col_g2:
            st.markdown('<div class="section-title">🎯 Distribuzione Seniority</div>', unsafe_allow_html=True)
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
                annotations=[dict(text=f"<b>{len(df_tab)}</b><br><span style='font-size:10px'>offerte</span>", x=0.5, y=0.5, font_size=20, font_color="#f0ede6", showarrow=False)],
            )
            st.plotly_chart(fig_sen, use_container_width=True, config={"displayModeBar": False}, key=f"sen_{tab_nome}")

        # ── Riga 2: Città + Modalità lavoro ───────────────────────────────────
        col_g3, col_g4 = st.columns([1, 1])

        with col_g3:
            st.markdown('<div class="section-title">📍 Offerte per Città</div>', unsafe_allow_html=True)
            if "città" in df_tab.columns:
                citta_count = df_tab[df_tab["città"] != "Non specificata"]["città"].value_counts().head(10).reset_index()
                citta_count.columns = ["città", "count"]
                fig_citta = go.Figure(go.Bar(
                    x=citta_count["città"], y=citta_count["count"],
                    marker=dict(color=citta_count["count"], colorscale=[[0, "#1e2a3a"], [1, "#60a5fa"]]),
                    text=citta_count["count"], textposition="outside", textfont=dict(color="#6b6880", size=11),
                ))
                fig_citta.update_layout(
                    **PLOTLY_BASE, height=320, showlegend=False,
                    xaxis=dict(gridcolor="#1e1e2e", linecolor="#0a0a0f", tickfont=dict(color="#e8e6e0", size=11), tickangle=-30),
                    yaxis=dict(gridcolor="#1e1e2e", linecolor="#1e1e2e", tickfont=dict(color="#6b6880")),
                )
                st.plotly_chart(fig_citta, use_container_width=True, config={"displayModeBar": False}, key=f"citta_{tab_nome}")

        with col_g4:
            st.markdown('<div class="section-title">🏠 Modalità di Lavoro</div>', unsafe_allow_html=True)
            if "modalita_lavoro" in df_tab.columns:
                mod_count = df_tab["modalita_lavoro"].value_counts().reset_index()
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
        if "data_pubblicazione" in df_tab.columns:
            df_trend = df_tab.copy()
            df_trend["settimana"] = df_trend["data_pubblicazione"].dt.to_period("W").dt.start_time
            trend = df_trend.groupby("settimana").size().reset_index(name="count").sort_values("settimana")
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

        # ── Lista offerte ──────────────────────────────────────────────────────
        st.markdown(f'<div class="section-title">📋 Lista Offerte <span style="color:#a78bfa; font-size:1.1rem; font-weight:600;"> {len(df_tab)}</span> <span style="color:#6b6880; font-size:1rem;">risultati</span></div>', unsafe_allow_html=True)

        # Ordinamento
        col_ord1, col_ord2 = st.columns([2, 1])
        with col_ord1:
            ordina_per = st.selectbox(
                "Ordina per",
                options=["Data (più recente)", "Data (più vecchia)", "Azienda A→Z"],
                key=f"ord_{tab_nome}",
                label_visibility="collapsed",
            )
        with col_ord2:
            mostra_n = st.selectbox("Mostra", options=[25, 50, 100], key=f"mostra_{tab_nome}", label_visibility="collapsed")

        if ordina_per == "Data (più recente)":
            df_show = df_tab.sort_values("data_pubblicazione", ascending=False).head(mostra_n)
        elif ordina_per == "Data (più vecchia)":
            df_show = df_tab.sort_values("data_pubblicazione", ascending=True).head(mostra_n)
        else:
            df_show = df_tab.sort_values("azienda", ascending=True).head(mostra_n)

        for _, row in df_show.iterrows():
            titolo     = row.get("titolo", "N/D")
            azienda    = row.get("azienda", "N/D")
            citta      = row.get("città", "N/D")
            seniority  = row.get("seniority", "unspecified")
            modalita   = row.get("modalita_lavoro", "non specificato")
            url        = row.get("url", "")
            data_pub   = row.get("data_pubblicazione")
            categoria  = row.get("categoria_ruolo", "")

            data_str   = data_pub.strftime("%d %b %Y") if pd.notna(data_pub) else "—"
            link_html  = f'<a href="{url}" target="_blank" style="color:#a78bfa; text-decoration:none; font-size:0.82rem; font-weight:500;">→ Candidati</a>' if url else ""
            badge_mod  = badge_modalita(modalita)

            html = (
                '<div class="offerta-card">'
                '<div style="display:flex; justify-content:space-between; align-items:flex-start;">'
                '<div style="flex:1;">'
                f'<div class="offerta-titolo">{titolo}</div>'
                f'<div class="offerta-azienda">{azienda}</div>'
                '<div style="margin-top:0.6rem; display:flex; gap:0.4rem; align-items:center; flex-wrap:wrap;">'
                f'{badge_seniority(seniority)}'
                f'{badge_mod}'
                f'<span class="offerta-citta">📍 {citta}</span>'
                f'<span style="font-family:JetBrains Mono; font-size:0.72rem; color:#3d3d5c;">{data_str}</span>'
                f'<span style="font-size:0.72rem; color:#4b5563;">{categoria}</span>'
                '</div>'
                '</div>'
                f'<div style="text-align:right; min-width:90px; padding-left:1rem;">{link_html}</div>'
                '</div>'
                '</div>'
            )
            st.markdown(html, unsafe_allow_html=True)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
    IT Job Market Intelligence · Dati da JSearch API · Aggiornamento automatico ogni mattina alle 08:00
</div>
""", unsafe_allow_html=True)
