"""
ETL — Job Market Intelligence Tool v2.0
Estrae offerte IT da JSearch API, le trasforma e le carica su Supabase.
Aggiornamenti v2:
- Nuove query bilingue (IT+EN) per ogni ruolo
- Nuove categorie: Business Analyst, ERP Consultant, IT Consultant, BI Developer, Project Manager, Operations Analyst
- Normalizzazione città estesa (50+ città italiane)
- Rilevamento modalità lavoro (remoto/ibrido/sede)
- Seniority matching esteso con terminologie di tutte le piattaforme
"""

import os
import re
import time
import requests
from datetime import datetime, timezone
from supabase import create_client, Client

# ── Credenziali ────────────────────────────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")

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
    "italy": "Italia", "italia": "Italia",
    "remote": "Remoto", "remoto": "Remoto",
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
def carica_su_supabase(supabase: Client, offerte_processate: list[dict]):
    inserite = 0
    saltate  = 0
    for offerta in offerte_processate:
        try:
            check = (
                supabase.table("offerte")
                .select("id")
                .eq("id_esterno", offerta["id_esterno"])
                .execute()
            )
            if check.data:
                saltate += 1
                continue

            record = {
                "id_esterno":        offerta["id_esterno"],
                "titolo":            offerta["titolo"],
                "azienda":           offerta["azienda"],
                "città":             offerta["citta"],
                "paese":             "Italy",
                "descrizione":       offerta["descrizione"],
                "url":               offerta["url"],
                "data_pubblicazione": offerta["data_pubblicazione"],
                "categoria_ruolo":   offerta["categoria_ruolo"],
                "seniority":         offerta["seniority"],
                "modalita_lavoro":   offerta["modalita_lavoro"],
                "stipendio_min":     offerta.get("stipendio_min"),
                "stipendio_max":     offerta.get("stipendio_max"),
            }

            res = supabase.table("offerte").insert(record).execute()
            offerta_id = res.data[0]["id"]

            skill_rows = [{"offerta_id": offerta_id, "skill": s} for s in offerta["skill"]]
            if skill_rows:
                supabase.table("skill_richieste").insert(skill_rows).execute()

            inserite += 1
        except Exception as e:
            print(f"  ⚠ Errore inserimento '{offerta.get('titolo', '?')}': {e}")
    return inserite, saltate

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print(f"ETL v2.0 — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    if not all([SUPABASE_URL, SUPABASE_KEY, RAPIDAPI_KEY]):
        raise EnvironmentError("Credenziali mancanti!")

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    totale_inserite = 0
    totale_saltate  = 0
    chiamate_api    = 0
    MAX_CHIAMATE    = 190  # Piano free: 200/giorno

    for q in QUERIES:
        if chiamate_api >= MAX_CHIAMATE:
            print(f"\n⚠ Limite chiamate API ({MAX_CHIAMATE}). Stop.")
            break

        print(f"\n📋 [{chiamate_api}/{MAX_CHIAMATE}] {q['query']}")
        jobs_raw = fetch_offerte(q["query"], q["num_pages"])
        chiamate_api += q["num_pages"]

        offerte_processate = []
        for job in jobs_raw:
            try:
                exp     = None
                exp_obj = job.get("job_required_experience")
                if isinstance(exp_obj, dict):
                    exp = exp_obj.get("required_experience_in_months")

                titolo      = job.get("job_title", "") or ""
                descrizione = job.get("job_description", "") or ""

                offerte_processate.append({
                    "id_esterno":        job.get("job_id", ""),
                    "titolo":            titolo,
                    "azienda":           job.get("employer_name", "") or "Non specificata",
                    "citta":             normalizza_citta(job.get("job_city", "") or ""),
                    "descrizione":       descrizione,
                    "url":               job.get("job_apply_link", ""),
                    "data_pubblicazione": job.get("job_posted_at_datetime_utc"),
                    "categoria_ruolo":   q["categoria"],
                    "seniority":         rileva_seniority(titolo, descrizione, exp),
                    "modalita_lavoro":   rileva_modalita_lavoro(titolo, descrizione),
                    "stipendio_min":     job.get("job_min_salary"),
                    "stipendio_max":     job.get("job_max_salary"),
                    "skill":             estrai_skill(descrizione),
                })
            except Exception as e:
                print(f"  ⚠ Errore trasformazione: {e}")

        ins, sal = carica_su_supabase(supabase, offerte_processate)
        totale_inserite += ins
        totale_saltate  += sal
        print(f"  ✅ Inserite: {ins} | Saltate: {sal}")

    print("\n" + "=" * 60)
    print(f"Completato — Inserite: {totale_inserite} | Saltate: {totale_saltate}")
    print(f"Chiamate API: {chiamate_api}/{MAX_CHIAMATE}")
    print("=" * 60)

if __name__ == "__main__":
    main()
