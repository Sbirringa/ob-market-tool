"""
ETL — Job Market Intelligence Tool v2.2
Estrae offerte IT da JSearch API, le trasforma e le carica su Supabase.

Fix v2.1:
- BUG FIX CRITICO: raccoglie TUTTE le offerte da TUTTE le query prima di caricare
- BUG FIX: disattiva solo le offerte non viste da più di 7 giorni (soglia configurabile)
- MIGLIORAMENTO: se la run è incompleta (limite API), le offerte recenti rimangono attive

Fix v2.2:
- BUG FIX: data_pubblicazione ora usa ultimo_check come fallback se JSearch restituisce null
  (prima: null → il filtro "Ultime 24 ore" in app.py includeva tutte le offerte con NaT)
- INVARIATO: tutte le query, skill, normalizzazioni, seniority detection
"""

import os
import re
import time
import requests
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client

# ── Credenziali ────────────────────────────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")

# ── Configurazione ─────────────────────────────────────────────────────────────
GIORNI_PRIMA_DISATTIVAZIONE = 7  # Disattiva offerte non viste da più di N giorni

# ── Query bilingue per ogni ruolo ──────────────────────────────────────────────
QUERIES = [
    # Data Analyst (IT + EN)
    {"query": "data analyst Italy",               "categoria": "Data Analyst",        "num_pages": 2},
    {"query": "analista dati Italy",              "categoria": "Data Analyst",        "num_pages": 1},
    {"query": "analisi dati Italy",               "categoria": "Data Analyst",        "num_pages": 1},
    {"query": "reporting analyst Italy",          "categoria": "Data Analyst",        "num_pages": 1},
    {"query": "analista reporting Italy",         "categoria": "Data Analyst",        "num_pages": 1},
    # Data Engineer
    {"query": "data engineer Italy",              "categoria": "Data Engineer",       "num_pages": 2},
    {"query": "ingegnere dati Italy",             "categoria": "Data Engineer",       "num_pages": 1},
    {"query": "ETL developer Italy",              "categoria": "Data Engineer",       "num_pages": 1},
    # Business Analyst (IT + EN)
    {"query": "business analyst Italy",           "categoria": "Business Analyst",    "num_pages": 2},
    {"query": "analista di business Italy",       "categoria": "Business Analyst",    "num_pages": 1},
    {"query": "analista requisiti Italy",         "categoria": "Business Analyst",    "num_pages": 1},
    {"query": "process analyst Italy",            "categoria": "Business Analyst",    "num_pages": 1},
    {"query": "analista processi Italy",          "categoria": "Business Analyst",    "num_pages": 1},
    # Analista Funzionale (IT + EN)
    {"query": "analista funzionale Italy",        "categoria": "Analista Funzionale", "num_pages": 2},
    {"query": "functional analyst Italy",         "categoria": "Analista Funzionale", "num_pages": 1},
    {"query": "analista tecnico funzionale Italy","categoria": "Analista Funzionale", "num_pages": 1},
    # ERP Consultant
    {"query": "ERP consultant Italy",             "categoria": "ERP Consultant",      "num_pages": 2},
    {"query": "SAP consultant Italy",             "categoria": "ERP Consultant",      "num_pages": 1},
    {"query": "Dynamics 365 consultant Italy",    "categoria": "ERP Consultant",      "num_pages": 1},
    {"query": "Zucchetti consultant Italy",       "categoria": "ERP Consultant",      "num_pages": 1},
    {"query": "consulente ERP Italy",             "categoria": "ERP Consultant",      "num_pages": 1},
    {"query": "consulente SAP Italy",             "categoria": "ERP Consultant",      "num_pages": 1},
    # IT Consultant
    {"query": "IT consultant Italy",              "categoria": "IT Consultant",       "num_pages": 2},
    {"query": "consulente IT Italy",              "categoria": "IT Consultant",       "num_pages": 1},
    {"query": "software application consultant Italy","categoria": "IT Consultant",   "num_pages": 1},
    {"query": "consulente applicativo Italy",     "categoria": "IT Consultant",       "num_pages": 1},
    # BI Developer
    {"query": "Power BI developer Italy",         "categoria": "BI Developer",        "num_pages": 1},
    {"query": "BI developer Italy",               "categoria": "BI Developer",        "num_pages": 1},
    {"query": "sviluppatore Power BI Italy",      "categoria": "BI Developer",        "num_pages": 1},
    {"query": "Tableau developer Italy",          "categoria": "BI Developer",        "num_pages": 1},
    # ML / AI
    {"query": "machine learning engineer Italy",  "categoria": "ML Engineer",         "num_pages": 1},
    {"query": "AI consultant Italy",              "categoria": "AI Solutions",        "num_pages": 1},
    {"query": "AI solution Italy",                "categoria": "AI Solutions",        "num_pages": 1},
    {"query": "intelligenza artificiale Italy",   "categoria": "AI Solutions",        "num_pages": 1},
    {"query": "digital transformation consultant Italy","categoria": "AI Solutions",  "num_pages": 1},
    # Project Manager
    {"query": "junior project manager IT Italy",  "categoria": "Project Manager",     "num_pages": 1},
    {"query": "project manager junior Italy",     "categoria": "Project Manager",     "num_pages": 1},
    {"query": "IT project coordinator Italy",     "categoria": "Project Manager",     "num_pages": 1},
    # Operations / Governance
    {"query": "operations analyst Italy",         "categoria": "Operations Analyst",  "num_pages": 1},
    {"query": "analista operativo Italy",         "categoria": "Operations Analyst",  "num_pages": 1},
    {"query": "data governance analyst Italy",    "categoria": "Operations Analyst",  "num_pages": 1},
    {"query": "compliance analyst Italy",         "categoria": "Operations Analyst",  "num_pages": 1},
]

# ── Keyword seniority ESTESE ───────────────────────────────────────────────────
KEYWORD_JUNIOR = [
    "junior", "entry level", "entry-level", "neolaureato", "neolaureati",
    "prima esperienza", "0-2 anni", "0-1 anni", "1-2 anni", "laureando",
    "appena laureato", "esperienza minima", "senza esperienza",
    "fresh graduate", "stage", "tirocinio", "internship", "trainee",
    "graduate", "neo-laureato", "neodiplomato", "primo impiego",
    "inserimento", "giovane", "talento", "associate",
    "early career", "new grad", "recent graduate", "0-2 years",
    "no experience required", "starter", "livello base", "livello iniziale",
]

KEYWORD_MID = [
    "2-5 anni", "3-5 anni", "2-4 anni", "livello medio",
    "esperienza pluriennale", "esperienza pregressa", "consolidata esperienza",
    "mid level", "mid-level", "intermediate", "2-5 years", "3-5 years",
    "some experience", "experienced", "proven experience",
    "livello intermedio",
]

KEYWORD_SENIOR = [
    "senior", "lead", "principal", "manager", "head of",
    "5+ anni", "5 anni di esperienza", "almeno 5", "oltre 5 anni",
    "esperienza consolidata", "figura esperta", "responsabile",
    "direttore", "coordinatore", "esperto", "specialista",
    "8+ anni", "10+ anni", "più di 5 anni",
    "senior level", "staff", "architect", "director",
    "5+ years", "8+ years", "10+ years", "extensive experience",
    "seasoned", "expert", "specialist", "team lead",
    "livello medio-alto", "livello alto", "executive", "c-level",
]

# ── Skill estese ───────────────────────────────────────────────────────────────
SKILL_LIST = [
    "Python", "SQL", "R", "Java", "Scala", "JavaScript", "VBA", "DAX", "M",
    "Power BI", "Tableau", "Looker", "QlikView", "QlikSense", "Excel",
    "Google Data Studio", "Metabase", "Superset",
    "Spark", "Hadoop", "Kafka", "Airflow", "dbt", "Databricks",
    "AWS", "Azure", "GCP", "Google Cloud",
    "TensorFlow", "PyTorch", "scikit-learn", "Keras", "LLM", "RAG",
    "Machine Learning", "Deep Learning", "NLP", "OpenAI", "GPT",
    "PostgreSQL", "MySQL", "MongoDB", "Snowflake", "BigQuery", "Redshift",
    "Oracle", "SQL Server",
    "Pandas", "NumPy", "Matplotlib", "Seaborn", "Plotly", "FastAPI", "Flask",
    "Docker", "Kubernetes", "Git", "GitHub", "CI/CD", "Terraform",
    "SAP", "SAP HANA", "Dynamics 365", "Zucchetti", "Salesforce",
    "ServiceNow", "Jira", "Confluence",
    "PowerPoint", "Word", "SharePoint",
    "Agile", "Scrum", "Kanban", "ITIL", "Prince2",
    "GDPR", "ISO 27001",
    "Statistics", "Statistica", "A/B Testing",
    "ETL", "Data Warehouse", "Data Lake", "Data Mesh",
    "REST API", "GraphQL", "Microservizi",
]

# ── Modalità lavoro ────────────────────────────────────────────────────────────
KEYWORD_REMOTO = [
    "remote", "remoto", "lavoro da casa", "smart working", "full remote",
    "100% remote", "completamente remoto", "telelavoro", "work from home",
    "wfh", "anywhere", "distributed",
]
KEYWORD_IBRIDO = [
    "ibrido", "hybrid", "ibrida", "modalità ibrida", "hybrid work",
    "smart working parziale", "partial remote", "flexible", "flessibile",
    "giorni in ufficio",
]
KEYWORD_SEDE = [
    "in sede", "on site", "onsite", "on-site", "presenza", "in loco",
    "full office", "no remote", "solo in sede",
]

def rileva_modalita_lavoro(titolo: str, descrizione: str) -> str:
    testo = f"{titolo} {descrizione}".lower()
    for kw in KEYWORD_REMOTO:
        if kw in testo:
            return "remoto"
    for kw in KEYWORD_IBRIDO:
        if kw in testo:
            return "ibrido"
    for kw in KEYWORD_SEDE:
        if kw in testo:
            return "sede"
    return "non specificato"

# ── Normalizzazione città ESTESA ───────────────────────────────────────────────
CITTA_MAP = {
    "milan": "Milano", "milano": "Milano", "mi": "Milano",
    "sesto san giovanni": "Milano", "cologno monzese": "Milano",
    "monza": "Milano", "rho": "Milano", "pero": "Milano",
    "corsico": "Milano", "assago": "Milano", "segrate": "Milano",
    "bergamo": "Bergamo", "como": "Como", "varese": "Varese",
    "rome": "Roma", "roma": "Roma", "rm": "Roma",
    "roma eur": "Roma", "guidonia": "Roma", "tivoli": "Roma",
    "fiumicino": "Roma", "ciampino": "Roma",
    "torino": "Torino", "turin": "Torino", "to": "Torino",
    "moncalieri": "Torino", "collegno": "Torino",
    "bologna": "Bologna", "bo": "Bologna",
    "firenze": "Firenze", "florence": "Firenze", "fi": "Firenze",
    "napoli": "Napoli", "naples": "Napoli", "na": "Napoli",
    "genova": "Genova", "genoa": "Genova", "ge": "Genova",
    "venezia": "Venezia", "venice": "Venezia", "ve": "Venezia",
    "mestre": "Venezia", "marghera": "Venezia",
    "bari": "Bari", "ba": "Bari",
    "palermo": "Palermo", "pa": "Palermo",
    "catania": "Catania", "ct": "Catania",
    "verona": "Verona", "vr": "Verona",
    "padova": "Padova", "padua": "Padova", "pd": "Padova",
    "trieste": "Trieste", "ts": "Trieste",
    "brescia": "Brescia", "bs": "Brescia",
    "parma": "Parma", "pr": "Parma",
    "modena": "Modena", "mo": "Modena",
    "reggio emilia": "Reggio Emilia",
    "perugia": "Perugia", "pg": "Perugia",
    "ancona": "Ancona", "an": "Ancona",
    "cagliari": "Cagliari", "ca": "Cagliari",
    "trento": "Trento", "tn": "Trento",
    "bolzano": "Bolzano", "bz": "Bolzano",
    "lecce": "Lecce", "salerno": "Salerno",
    "pisa": "Pisa", "siena": "Siena", "lucca": "Lucca",
    "remote": "Remoto", "remoto": "Remoto",
    "milan (mi)": "Milano", "milano (mi)": "Milano",
    "greater milan": "Milano", "milano, mi": "Milano",
    "provincia di milano": "Milano",
    "milan, metropolitan city of milan": "Milano",
    "metropolitan city of milan": "Milano",
    "rome, lazio": "Roma", "greater rome": "Roma",
    "city of rome": "Roma",
    "italy": "Non Specificata", "italia": "Non Specificata",
}

def normalizza_citta(citta_raw: str) -> str:
    if not citta_raw:
        return "Non specificata"
    key = citta_raw.strip().lower()
    if key in CITTA_MAP:
        return CITTA_MAP[key]
    for k, v in CITTA_MAP.items():
        if len(k) > 4 and k in key:
            return v
    return citta_raw.strip().title()

# ── Seniority ──────────────────────────────────────────────────────────────────
def rileva_seniority(titolo: str, descrizione: str, mesi_esperienza) -> str:
    if mesi_esperienza is not None:
        try:
            mesi = int(mesi_esperienza)
            if mesi <= 24:   return "junior"
            elif mesi <= 60: return "mid"
            else:            return "senior"
        except (ValueError, TypeError):
            pass

    testo = f"{titolo} {descrizione}".lower()
    for kw in KEYWORD_SENIOR:
        if kw.lower() in testo:
            return "senior"
    for kw in KEYWORD_MID:
        if kw.lower() in testo:
            return "mid"
    for kw in KEYWORD_JUNIOR:
        if kw.lower() in testo:
            return "junior"
    return "unspecified"

# ── Skill ──────────────────────────────────────────────────────────────────────
def estrai_skill(descrizione: str) -> list[str]:
    trovate = []
    testo = descrizione.lower() if descrizione else ""
    for skill in SKILL_LIST:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, testo):
            trovate.append(skill)
    return trovate

# ── JSearch API ────────────────────────────────────────────────────────────────
def fetch_offerte(query: str, num_pages: int) -> list[dict]:
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        "Content-Type": "application/json",
    }
    risultati = []
    for page in range(1, num_pages + 1):
        params = {
            "query": query,
            "page": str(page),
            "num_pages": "1",
            "country": "it",
            "date_posted": "all",
        }
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
            jobs = resp.json().get("data", [])
            risultati.extend(jobs)
            print(f"  → Pagina {page}: {len(jobs)} offerte trovate")
            time.sleep(0.5)
        except Exception as e:
            print(f"  ⚠ Errore fetch pagina {page}: {e}")
    return risultati

# ── Supabase ───────────────────────────────────────────────────────────────────
def carica_su_supabase(supabase: Client, tutte_le_offerte: list[dict]):
    """
    Riceve TUTTE le offerte raccolte dall'intera run (non più categoria per categoria).

    Logica corretta:
    1. Disattiva solo le offerte NON viste in questa run E non aggiornate
       da più di GIORNI_PRIMA_DISATTIVAZIONE giorni.
       → Se la run è incompleta (limite API), le offerte recenti restano attive.
    2. Per ogni offerta: se esiste aggiorna attiva=True, altrimenti inserisce.
    """
    inserite = 0
    aggiornate = 0
    errori = 0
    now = datetime.now(timezone.utc).isoformat()

    # Soglia: offerte non viste da più di N giorni vengono disattivate
    soglia_disattivazione = (
        datetime.now(timezone.utc) - timedelta(days=GIORNI_PRIMA_DISATTIVAZIONE)
    ).isoformat()

    # Set di tutti gli id_esterno trovati in questa run
    id_esterni_run = {o["id_esterno"] for o in tutte_le_offerte if o.get("id_esterno")}

    print(f"\n🔄 Offerte raccolte in questa run: {len(tutte_le_offerte)} ({len(id_esterni_run)} uniche)")

    # ── STEP 1: Disattiva solo le offerte vecchie non presenti in questa run ──
    # NON disattiva offerte recenti anche se non le abbiamo viste (run incompleta)
    if id_esterni_run:
        try:
            supabase.table("offerte").update({
                "attiva": False,
                "ultimo_check": now,
            }).not_.in_(
                "id_esterno", list(id_esterni_run)
            ).lt(
                "ultimo_check", soglia_disattivazione
            ).execute()
            print(f"  ✅ Offerte vecchie (>{GIORNI_PRIMA_DISATTIVAZIONE}gg non viste) disattivate")
        except Exception as e:
            print(f"  ⚠ Errore disattivazione offerte vecchie: {e}")
    else:
        print("  ⚠ Nessuna offerta raccolta — skip disattivazione (sicurezza)")

    # ── STEP 2: Upsert di ogni offerta ────────────────────────────────────────
    for offerta in tutte_le_offerte:
        try:
            id_est = offerta.get("id_esterno", "")
            if not id_est:
                continue

            # Controlla se l'offerta esiste già
            check = (
                supabase.table("offerte")
                .select("id")
                .eq("id_esterno", id_est)
                .execute()
            )

            if check.data:
                # Offerta già presente → riattiva e aggiorna ultimo_check
                supabase.table("offerte").update({
                    "attiva": True,
                    "ultimo_check": now,
                }).eq("id_esterno", id_est).execute()
                aggiornate += 1
            else:
                # Offerta nuova → inserisci
                record = {
                    "id_esterno":         offerta["id_esterno"],
                    "titolo":             offerta["titolo"],
                    "azienda":            offerta["azienda"],
                    "città":              offerta["citta"],
                    "paese":              "Italy",
                    "descrizione":        offerta["descrizione"],
                    "url":                offerta["url"],
                    "data_pubblicazione": offerta["data_pubblicazione"],
                    "categoria_ruolo":    offerta["categoria_ruolo"],
                    "seniority":          offerta["seniority"],
                    "modalita_lavoro":    offerta["modalita_lavoro"],
                    "stipendio_min":      offerta.get("stipendio_min"),
                    "stipendio_max":      offerta.get("stipendio_max"),
                    "attiva":             True,
                    "ultimo_check":       now,
                }
                res = supabase.table("offerte").insert(record).execute()
                offerta_id = res.data[0]["id"]

                skill_rows = [
                    {"offerta_id": offerta_id, "skill": s}
                    for s in offerta["skill"]
                ]
                if skill_rows:
                    supabase.table("skill_richieste").insert(skill_rows).execute()

                inserite += 1

        except Exception as e:
            print(f"  ⚠ Errore upsert '{offerta.get('titolo', '?')}': {e}")
            errori += 1

    return inserite, aggiornate, errori

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print(f"ETL v2.2 — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    if not all([SUPABASE_URL, SUPABASE_KEY, RAPIDAPI_KEY]):
        raise EnvironmentError("Credenziali mancanti! Controlla SUPABASE_URL, SUPABASE_KEY, RAPIDAPI_KEY.")

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    chiamate_api    = 0
    MAX_CHIAMATE    = 190  # Piano free: 200/giorno

    # ── FIX: raccogli TUTTO prima di caricare ──────────────────────────────────
    tutte_le_offerte: list[dict] = []

    for q in QUERIES:
        if chiamate_api >= MAX_CHIAMATE:
            print(f"\n⚠ Limite chiamate API ({MAX_CHIAMATE}) raggiunto. Stop fetch.")
            print(f"  Le offerte già raccolte verranno comunque caricate.")
            break

        print(f"\n📋 [{chiamate_api}/{MAX_CHIAMATE}] {q['query']}")
        jobs_raw = fetch_offerte(q["query"], q["num_pages"])
        chiamate_api += q["num_pages"]

        for job in jobs_raw:
            try:
                exp     = None
                exp_obj = job.get("job_required_experience")
                if isinstance(exp_obj, dict):
                    exp = exp_obj.get("required_experience_in_months")

                titolo      = job.get("job_title", "") or ""
                descrizione = job.get("job_description", "") or ""

                tutte_le_offerte.append({
                    "id_esterno":         job.get("job_id", ""),
                    "titolo":             titolo,
                    "azienda":            job.get("employer_name", "") or "Non specificata",
                    "citta":              normalizza_citta(job.get("job_city", "") or ""),
                    "descrizione":        descrizione,
                    "url":                job.get("job_apply_link", ""),
                    "data_pubblicazione": job.get("job_posted_at_datetime_utc") or datetime.now(timezone.utc).isoformat(),
                    "categoria_ruolo":    q["categoria"],
                    "seniority":          rileva_seniority(titolo, descrizione, exp),
                    "modalita_lavoro":    rileva_modalita_lavoro(titolo, descrizione),
                    "stipendio_min":      job.get("job_min_salary"),
                    "stipendio_max":      job.get("job_max_salary"),
                    "skill":              estrai_skill(descrizione),
                })
            except Exception as e:
                print(f"  ⚠ Errore trasformazione job: {e}")

        print(f"  📦 Accumulate {len(tutte_le_offerte)} offerte totali finora")

    # ── Caricamento singolo alla fine, dopo aver raccolto tutto ───────────────
    print(f"\n{'=' * 60}")
    print(f"🚀 Inizio caricamento su Supabase...")
    inserite, aggiornate, errori = carica_su_supabase(supabase, tutte_le_offerte)

    print(f"\n{'=' * 60}")
    print(f"✅ Completato!")
    print(f"   Inserite (nuove):    {inserite}")
    print(f"   Aggiornate (già DB): {aggiornate}")
    print(f"   Errori:              {errori}")
    print(f"   Chiamate API usate:  {chiamate_api}/{MAX_CHIAMATE}")
    print("=" * 60)

if __name__ == "__main__":
    main()
