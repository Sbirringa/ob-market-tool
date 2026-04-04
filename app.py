"""
IT Job Market Intelligence — Dashboard Streamlit
Design: Dark editorial, tipografia raffinata, grafici Plotly custom
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

# ── CSS personalizzato — dark editorial 2026 ───────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #0a0a0f; color: #e8e6e0; }
[data-testid="stSidebar"] {
    background: #0f0f18 !important;
    border-right: 1px solid #1e1e2e;
}
.main-header {
    font-family: 'DM Serif Display', serif;
    font-size: 3.2rem;
    font-weight: 400;
    color: #f0ede6;
    letter-spacing: -0.02em;
    line-height: 1.1;
    margin-bottom: 0.2rem;
}
.main-subtitle {
    font-family: 'DM Sans', sans-serif;
    font-size: 1rem;
    font-weight: 300;
    color: #6b6880;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 2rem;
}
.kpi-card {
    background: linear-gradient(135deg, #13131f 0%, #1a1a2e 100%);
    border: 1px solid #1e1e30;
    border-radius: 16px;
    padding: 1.5rem;
    position: relative;
    overflow: hidden;
}
.kpi-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #6c63ff, #a78bfa, #818cf8);
}
.kpi-value {
    font-family: 'DM Serif Display', serif;
    font-size: 2.6rem;
    color: #f0ede6;
    line-height: 1;
    margin-bottom: 0.4rem;
}
.kpi-label {
    font-size: 0.78rem;
    color: #6b6880;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-weight: 500;
}
.kpi-sub {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
    color: #a78bfa;
    margin-top: 0.5rem;
}
.badge {
    display: inline-block;
    padding: 0.2rem 0.65rem;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.badge-junior     { background: #1a2e1a; color: #4ade80; border: 1px solid #166534; }
.badge-mid        { background: #1e2a3a; color: #60a5fa; border: 1px solid #1e3a5f; }
.badge-senior     { background: #2d1e3a; color: #c084fc; border: 1px solid #581c87; }
.badge-unspecified{ background: #1e1e2e; color: #94a3b8; border: 1px solid #334155; }
.section-title {
    font-family: 'DM Serif Display', serif;
    font-size: 1.5rem;
    color: #f0ede6;
    margin: 2rem 0 1rem 0;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid #1e1e2e;
}
.offerta-card {
    background: #13131f;
    border: 1px solid #1e1e2e;
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 0.8rem;
}
.offerta-titolo  { font-size: 1rem; font-weight: 600; color: #f0ede6; margin-bottom: 0.3rem; }
.offerta-azienda { font-size: 0.85rem; color: #6b6880; }
.offerta-citta   { font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: #a78bfa; }
.stTabs [data-baseweb="tab-list"] { background: #0f0f18; border-bottom: 1px solid #1e1e2e; gap: 0; }
.stTabs [data-baseweb="tab"] { color: #6b6880; font-size: 0.88rem; font-weight: 500; padding: 0.75rem 1.2rem; border-radius: 0; }
.stTabs [aria-selected="true"] { color: #f0ede6 !important; border-bottom: 2px solid #a78bfa !important; background: transparent !important; }
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: #0a0a0f; }
::-webkit-scrollbar-thumb { background: #2a2a3e; border-radius: 4px; }
.footer { font-size: 0.75rem; color: #3d3d5c; text-align: center; padding: 2rem 0 1rem 0; letter-spacing: 0.05em; }

[data-testid="stSidebarCollapsedControl"]::after,
[data-testid="collapsedControl"]::after,
button[kind="header"]::after {
    content: 'Menù';
    display: block;
    font-size: 0.55rem;
    color: #6b6880;
    text-align: center;
    letter-spacing: 0.05em;
    margin-top: 2px;
}
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
        raise ValueError("SUPABASE_URL e SUPABASE_KEY non trovati nei secrets")
    return create_client(url, key)

@st.cache_data(ttl=3600)
def carica_dati():
    supabase = get_supabase()
    offerte_raw = supabase.table("offerte").select("*").execute().data
    skill_raw   = supabase.table("skill_richieste").select("*").execute().data
    df = pd.DataFrame(offerte_raw)
    df_skill = pd.DataFrame(skill_raw)
    if not df.empty and "data_pubblicazione" in df.columns:
        df["data_pubblicazione"] = pd.to_datetime(df["data_pubblicazione"], utc=True, errors="coerce")
    return df, df_skill

# ── Tema Plotly base ───────────────────────────────────────────────────────────
PLOTLY_BASE = dict(
    paper_bgcolor="#0a0a0f",
    plot_bgcolor="#0a0a0f",
    font=dict(family="DM Sans", color="#94a3b8", size=12),
    margin=dict(l=20, r=20, t=40, b=20),
    colorway=["#a78bfa", "#818cf8", "#60a5fa", "#34d399", "#f472b6", "#fb923c"],
)

AXIS_X = dict(gridcolor="#1e1e2e", linecolor="#1e1e2e", tickfont=dict(color="#6b6880"))
AXIS_Y = dict(gridcolor="#1e1e2e", linecolor="#1e1e2e", tickfont=dict(color="#6b6880"))

SENIORITY_COLORS = {
    "junior":      "#4ade80",
    "mid":         "#60a5fa",
    "senior":      "#c084fc",
    "unspecified": "#94a3b8",
}

def badge_html(seniority: str) -> str:
    s = str(seniority).lower()
    cls = f"badge-{s}" if s in ["junior", "mid", "senior", "unspecified"] else "badge-unspecified"
    return f'<span class="badge {cls}">{s}</span>'

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

    st.markdown("**🎯 Filtri**")

    seniority_options = ["junior", "mid", "senior", "unspecified"]
    seniority_sel = st.multiselect(
        "Livello seniority",
        options=seniority_options,
        default=[],
        placeholder="Tutti i livelli"
    )

    periodo = st.selectbox(
        "Periodo",
        options=["Ultimi 7 giorni", "Ultimi 30 giorni", "Ultimi 90 giorni", "Tutto"],
        index=3
    )

    citta_options = ["Tutte"]
    if dati_ok and "città" in df.columns:
        citta_options += sorted(df["città"].dropna().unique().tolist())
    citta_sel = st.selectbox("Città", options=citta_options)

    skill_options = []
    if not df_skill.empty and "skill" in df_skill.columns:
        skill_options = sorted(df_skill["skill"].dropna().unique().tolist())
    skill_sel = st.multiselect("Skill richieste", options=skill_options, placeholder="Filtra per skill...")

    st.markdown("---")
    if st.button("🔄 Aggiorna dati", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown('<div class="footer">Dati aggiornati ogni mattina<br>via GitHub Actions + JSearch API</div>', unsafe_allow_html=True)

# ── HEADER ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">Mercato IT Italiano</div>
<div class="main-subtitle">Intelligence sulle offerte di lavoro · Aggiornamento quotidiano</div>
""", unsafe_allow_html=True)

# ── FILTRAGGIO DATI ────────────────────────────────────────────────────────────
if dati_ok:
    df_f = df.copy()

    # Filtro seniority — se vuoto mostra tutto
    if seniority_sel:
        df_f = df_f[df_f["seniority"].isin(seniority_sel)]

    # Filtro periodo
    if "data_pubblicazione" in df_f.columns:
        oggi = pd.Timestamp.now(tz="UTC")
        df_f["data_pubblicazione"] = pd.to_datetime(df_f["data_pubblicazione"], utc=True, errors="coerce")
        if periodo == "Ultimi 7 giorni":
            df_f = df_f[df_f["data_pubblicazione"] >= oggi - pd.Timedelta(days=7)]
        elif periodo == "Ultimi 30 giorni":
            df_f = df_f[df_f["data_pubblicazione"] >= oggi - pd.Timedelta(days=30)]
        elif periodo == "Ultimi 90 giorni":
            df_f = df_f[df_f["data_pubblicazione"] >= oggi - pd.Timedelta(days=90)]

    # Filtro città
    if citta_sel != "Tutte":
        df_f = df_f[df_f["città"] == citta_sel]

    # Filtro skill
    if skill_sel and not df_skill.empty:
        ids_con_skill = df_skill[df_skill["skill"].isin(skill_sel)]["offerta_id"].unique()
        df_f = df_f[df_f["id"].isin(ids_con_skill)]

    skill_correnti = df_skill[df_skill["offerta_id"].isin(df_f["id"].tolist())] if not df_skill.empty and "offerta_id" in df_skill.columns else pd.DataFrame()

else:
    df_f = pd.DataFrame()
    skill_correnti = pd.DataFrame()

# ── KPI ────────────────────────────────────────────────────────────────────────
n_offerte  = len(df_f)
citta_top  = df_f["città"].value_counts().index[0] if not df_f.empty and "città" in df_f.columns and n_offerte > 0 else "—"
skill_top  = skill_correnti["skill"].value_counts().index[0] if not skill_correnti.empty else "—"
pct_junior = round(len(df_f[df_f["seniority"] == "junior"]) / n_offerte * 100) if n_offerte > 0 else 0

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="kpi-card"><div class="kpi-value">{n_offerte}</div><div class="kpi-label">Offerte trovate</div><div class="kpi-sub">nel periodo selezionato</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="kpi-card"><div class="kpi-value">{citta_top}</div><div class="kpi-label">Città più attiva</div><div class="kpi-sub">maggior concentrazione</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="kpi-card"><div class="kpi-value">{skill_top}</div><div class="kpi-label">Skill più richiesta</div><div class="kpi-sub">nelle offerte filtrate</div></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="kpi-card"><div class="kpi-value">{pct_junior}%</div><div class="kpi-label">Offerte Junior</div><div class="kpi-sub">+ unspecified incluse</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── TABS ───────────────────────────────────────────────────────────────────────
RUOLI = {
    "🌐 Tutte":               None,
    "📊 Data Analyst":        "Data Analyst",
    "⚙️ Data Engineer":       "Data Engineer",
    "🤖 ML Engineer":         "ML Engineer",
    "🧠 AI Solutions":        "AI Solutions",
    "📋 Analista Funzionale": "Analista Funzionale",
}

tabs = st.tabs(list(RUOLI.keys()))

for tab, (tab_nome, ruolo_filter) in zip(tabs, RUOLI.items()):
    with tab:
        df_tab = df_f.copy()
        if ruolo_filter and "categoria_ruolo" in df_tab.columns:
            df_tab = df_tab[df_tab["categoria_ruolo"] == ruolo_filter]

        skill_tab = skill_correnti[skill_correnti["offerta_id"].isin(df_tab["id"].tolist())] if not skill_correnti.empty and "offerta_id" in skill_correnti.columns else pd.DataFrame()

        if df_tab.empty:
            st.markdown("""
            <div style="text-align:center; padding: 3rem; color: #3d3d5c;">
                <div style="font-size: 2rem; margin-bottom: 1rem;">🔍</div>
                <div style="font-size: 0.9rem;">Nessuna offerta trovata con i filtri selezionati</div>
            </div>
            """, unsafe_allow_html=True)
            continue

        # ── Grafici ────────────────────────────────────────────────────────────
        col_g1, col_g2 = st.columns([1.2, 1])

        with col_g1:
            st.markdown('<div class="section-title">🔧 Skill più richieste</div>', unsafe_allow_html=True)
            if not skill_tab.empty:
                top_skill = skill_tab["skill"].value_counts().head(12).reset_index()
                top_skill.columns = ["skill", "count"]
                fig_skill = go.Figure(go.Bar(
                    x=top_skill["count"],
                    y=top_skill["skill"],
                    orientation="h",
                    marker=dict(
                        color=top_skill["count"],
                        colorscale=[[0, "#2d1e3a"], [0.5, "#6d28d9"], [1, "#a78bfa"]],
                        line=dict(color="rgba(0,0,0,0)", width=0),
                    ),
                    text=top_skill["count"],
                    textposition="outside",
                    textfont=dict(color="#6b6880", size=11),
                ))
                fig_skill.update_layout(
                    **PLOTLY_BASE,
                    height=380,
                    showlegend=False,
                    title=dict(text="", x=0),
                    xaxis=dict(gridcolor="#1e1e2e", linecolor="#0a0a0f", tickfont=dict(color="#6b6880")),
                    yaxis=dict(autorange="reversed", gridcolor="#1e1e2e", linecolor="#1e1e2e", tickfont=dict(color="#e8e6e0", size=12)),
                )
                st.plotly_chart(fig_skill, use_container_width=True, config={"displayModeBar": False}, key=f"skill_{tab_nome}")
            else:
                st.info("Nessuna skill disponibile per questo filtro.")

        with col_g2:
            st.markdown('<div class="section-title">🎯 Distribuzione Seniority</div>', unsafe_allow_html=True)
            sen_count = df_tab["seniority"].value_counts().reset_index()
            sen_count.columns = ["seniority", "count"]
            colors_sen = [SENIORITY_COLORS.get(s, "#94a3b8") for s in sen_count["seniority"]]

            fig_sen = go.Figure(go.Pie(
                labels=sen_count["seniority"],
                values=sen_count["count"],
                hole=0.65,
                marker=dict(colors=colors_sen, line=dict(color="#0a0a0f", width=3)),
                textfont=dict(color="#e8e6e0", size=12),
                textinfo="label+percent",
            ))
            fig_sen.update_layout(
                **PLOTLY_BASE,
                height=380,
                showlegend=False,
                annotations=[dict(
                    text=f"<b>{len(df_tab)}</b><br><span style='font-size:10px'>offerte</span>",
                    x=0.5, y=0.5, font_size=22,
                    font_color="#f0ede6",
                    showarrow=False
                )],
            )
            st.plotly_chart(fig_sen, use_container_width=True, config={"displayModeBar": False}, key=f"sen_{tab_nome}")

        col_g3, col_g4 = st.columns([1, 1.2])

        with col_g3:
            st.markdown('<div class="section-title">📍 Offerte per Città</div>', unsafe_allow_html=True)
            if "città" in df_tab.columns:
                citta_count = df_tab["città"].value_counts().head(10).reset_index()
                citta_count.columns = ["città", "count"]
                fig_citta = go.Figure(go.Bar(
                    x=citta_count["città"],
                    y=citta_count["count"],
                    marker=dict(
                        color=citta_count["count"],
                        colorscale=[[0, "#1e2a3a"], [1, "#60a5fa"]],
                    ),
                    text=citta_count["count"],
                    textposition="outside",
                    textfont=dict(color="#6b6880", size=11),
                ))
                fig_citta.update_layout(
                    **PLOTLY_BASE,
                    height=320,
                    showlegend=False,
                    xaxis=dict(gridcolor="#1e1e2e", linecolor="#0a0a0f", tickfont=dict(color="#e8e6e0", size=11), tickangle=-30),
                    yaxis=dict(gridcolor="#1e1e2e", linecolor="#1e1e2e", tickfont=dict(color="#6b6880")),
                )
                st.plotly_chart(fig_citta, use_container_width=True, config={"displayModeBar": False}, key=f"citta_{tab_nome}")

        with col_g4:
            st.markdown('<div class="section-title">📈 Trend Settimanale</div>', unsafe_allow_html=True)
            if "data_pubblicazione" in df_tab.columns:
                df_trend = df_tab.copy()
                df_trend["settimana"] = df_trend["data_pubblicazione"].dt.to_period("W").dt.start_time
                trend = df_trend.groupby("settimana").size().reset_index(name="count")
                trend = trend.sort_values("settimana")

                fig_trend = go.Figure()
                fig_trend.add_trace(go.Scatter(
                    x=trend["settimana"],
                    y=trend["count"],
                    mode="lines+markers",
                    line=dict(color="#a78bfa", width=2.5, shape="spline"),
                    marker=dict(color="#a78bfa", size=6, line=dict(color="#0a0a0f", width=2)),
                    fill="tozeroy",
                    fillcolor="rgba(167, 139, 250, 0.08)",
                ))
                fig_trend.update_layout(
                    **PLOTLY_BASE,
                    height=320,
                    showlegend=False,
                    xaxis=AXIS_X,
                    yaxis=AXIS_Y,
                )
                st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False}, key=f"trend_{tab_nome}")

        # ── Lista offerte ──────────────────────────────────────────────────────
        st.markdown(f'<div class="section-title">📋 Lista Offerte <span style="color:#6b6880; font-size:1rem;">({len(df_tab)} risultati)</span></div>', unsafe_allow_html=True)

        df_show = df_tab.sort_values("data_pubblicazione", ascending=False).head(50)

        for _, row in df_show.iterrows():
            titolo    = row.get("titolo", "N/D")
            azienda   = row.get("azienda", "N/D")
            citta     = row.get("città", "N/D")
            seniority = row.get("seniority", "unspecified")
            url       = row.get("url", "")
            data_pub  = row.get("data_pubblicazione")

            data_str  = data_pub.strftime("%d %b %Y") if pd.notna(data_pub) else "—"
            link_html = f'<a href="{url}" target="_blank" style="color:#a78bfa; text-decoration:none; font-size:0.8rem;">→ Candidati</a>' if url else ""

            st.markdown(f"""
            <div class="offerta-card">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <div style="flex:1;">
                        <div class="offerta-titolo">{titolo}</div>
                        <div class="offerta-azienda">{azienda}</div>
                        <div style="margin-top:0.5rem; display:flex; gap:0.5rem; align-items:center; flex-wrap:wrap;">
                            {badge_html(seniority)}
                            <span class="offerta-citta">📍 {citta}</span>
                            <span style="font-size:0.75rem; color:#3d3d5c;">·</span>
                            <span style="font-family:'JetBrains Mono'; font-size:0.72rem; color:#3d3d5c;">{data_str}</span>
                        </div>
                    </div>
                    <div style="text-align:right; min-width:80px;">{link_html}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
    IT Job Market Intelligence · Dati da JSearch API · Aggiornamento automatico ogni mattina alle 08:00
</div>
""", unsafe_allow_html=True)
