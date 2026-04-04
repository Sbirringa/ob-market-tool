"""
ETL — Job Market Intelligence Tool
Estrae offerte IT da JSearch API, le trasforma e le carica su Supabase.
"""

import os
import re
import requests
from datetime import datetime, timezone
from supabase import create_client, Client

# ── Credenziali ────────────────────────────────────────────────────────────────
# In locale legge da variabili d'ambiente (Streamlit le inietta da secrets.toml)
# In GitHub Actions legge dai Repository Secrets
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY")

# ── Configurazione query ───────────────────────────────────────────────────────
QUERIES = [
    {"query": "data analyst Italy",              "categoria": "Data Analyst",        "num_pages": 2},
    {"query": "analista funzionale Italy",       "categoria": "Analista Funzionale", "num_pages": 2},
    {"query": "data engineer Italy",             "categoria": "Data Engineer",       "num_pages": 2},
    {"query": "machine learning engineer Italy", "categoria": "ML Engineer",         "num_pages": 1},
    {"query": "AI consultant OR AI solution Italy", "categoria": "AI Solutions",     "num_pages": 1},
]

# ── Keyword seniority ──────────────────────────────────────────────────────────
KEYWORD_JUNIOR = [
    "junior", "entry level", "entry-level", "neolaureato", "neolaureati",
    "prima esperienza", "0-2 anni", "0-1 anni", "1-2 anni", "laureando",
    "appena laureato", "esperienza minima", "senza esperienza",
    "fresh graduate", "stage", "tirocinio", "internship", "trainee", "graduate",
]

KEYWORD_SENIOR = [
    "senior", "lead", "principal", "manager", "head of",
    "5+ anni", "5 anni di esperienza", "almeno 5",
    "esperienza consolidata", "figura esperta", "responsabile", "direttore",
]

# ── Skill da rilevare ──────────────────────────────────────────────────────────
SKILL_LIST = [
    "Python", "SQL", "R", "Java", "Scala", "JavaScript",
    "Power BI", "Tableau", "Looker", "QlikView", "Excel",
    "Spark", "Hadoop", "Kafka", "Airflow", "dbt",
    "AWS", "Azure", "GCP", "Google Cloud",
    "TensorFlow", "PyTorch", "scikit-learn", "Keras",
    "Pandas", "NumPy", "Matplotlib", "Seaborn",
    "PostgreSQL", "MySQL", "MongoDB", "Snowflake", "BigQuery", "Redshift",
    "Docker", "Kubernetes", "Git", "CI/CD",
    "Machine Learning", "Deep Learning", "NLP", "LLM", "RAG",
    "Statistics", "Statistica", "A/B Testing",
    "ETL", "Data Warehouse", "Data Lake", "Data Mesh",
    "SAP", "Salesforce", "PowerPoint",
]

# ── Normalizzazione città ──────────────────────────────────────────────────────
CITTA_MAP = {
    # Milano
    "milan": "Milano", "mi": "Milano", "milano nord": "Milano",
    "sesto san giovanni": "Milano", "cologno monzese": "Milano",
    # Roma
    "rome": "Roma", "rm": "Roma", "roma eur": "Roma", "roma nord": "Roma",
    # Torino
    "turin": "Torino", "to": "Torino",
    # Altre
    "florence": "Firenze", "naples": "Napoli", "bologna": "Bologna",
    "genoa": "Genova", "genova": "Genova",
    "venice": "Venezia", "venezia": "Venezia",
    "bari": "Bari", "palermo": "Palermo",
}

def normalizza_citta(citta_raw: str) -> str:
    if not citta_raw:
        return "Non specificata"
    key = citta_raw.strip().lower()
    return CITTA_MAP.get(key, citta_raw.strip().title())

# ── Rilevamento seniority ──────────────────────────────────────────────────────
def rileva_seniority(titolo: str, descrizione: str, mesi_esperienza) -> str:
    # Metodo 1 — campo strutturato API
    if mesi_esperienza is not None:
        try:
            mesi = int(mesi_esperienza)
            if mesi <= 24:
                return "junior"
            elif mesi <= 60:
                return "mid"
            else:
                return "senior"
        except (ValueError, TypeError):
            pass

    # Metodo 2 — keyword matching
    testo = f"{titolo} {descrizione}".lower()

    for kw in KEYWORD_SENIOR:
        if kw.lower() in testo:
            return "senior"

    for kw in KEYWORD_JUNIOR:
        if kw.lower() in testo:
            return "junior"

    return "unspecified"

# ── Estrazione skill ───────────────────────────────────────────────────────────
def estrai_skill(descrizione: str) -> list[str]:
    trovate = []
    testo = descrizione.lower() if descrizione else ""
    for skill in SKILL_LIST:
        # Usa word boundary per evitare falsi positivi (es. "R" dentro "Python")
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, testo):
            trovate.append(skill)
    return trovate

# ── Chiamata JSearch API ───────────────────────────────────────────────────────
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
            data = resp.json()
            jobs = data.get("data", [])
            risultati.extend(jobs)
            print(f"  → Pagina {page}: {len(jobs)} offerte trovate")
        except Exception as e:
            print(f"  ⚠ Errore fetch pagina {page}: {e}")
    return risultati

# ── Caricamento su Supabase ────────────────────────────────────────────────────
def carica_su_supabase(supabase: Client, offerte_processate: list[dict]):
    inserite = 0
    saltate = 0

    for offerta in offerte_processate:
        try:
            # Deduplicazione — controlla se id_esterno esiste già
            check = (
                supabase.table("offerte")
                .select("id")
                .eq("id_esterno", offerta["id_esterno"])
                .execute()
            )
            if check.data:
                saltate += 1
                continue

            # Prepara record principale
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
                "stipendio_min":     offerta.get("stipendio_min"),
                "stipendio_max":     offerta.get("stipendio_max"),
            }

            # INSERT offerta
            res = supabase.table("offerte").insert(record).execute()
            offerta_id = res.data[0]["id"]

            # INSERT skill
            skill_rows = [
                {"offerta_id": offerta_id, "skill": s}
                for s in offerta["skill"]
            ]
            if skill_rows:
                supabase.table("skill_richieste").insert(skill_rows).execute()

            inserite += 1

        except Exception as e:
            print(f"  ⚠ Errore inserimento '{offerta.get('titolo', '?')}': {e}")

    return inserite, saltate

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print(f"ETL avviato — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    # Verifica credenziali
    if not all([SUPABASE_URL, SUPABASE_KEY, RAPIDAPI_KEY]):
        raise EnvironmentError(
            "Credenziali mancanti! Controlla SUPABASE_URL, SUPABASE_KEY, RAPIDAPI_KEY"
        )

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    totale_inserite = 0
    totale_saltate = 0

    for q in QUERIES:
        print(f"\n📋 Query: {q['query']}")
        jobs_raw = fetch_offerte(q["query"], q["num_pages"])
        print(f"  Totale grezzi: {len(jobs_raw)}")

        # Trasformazione
        offerte_processate = []
        for job in jobs_raw:
            try:
                exp = None
                exp_obj = job.get("job_required_experience")
                if isinstance(exp_obj, dict):
                    exp = exp_obj.get("required_experience_in_months")

                titolo      = job.get("job_title", "") or ""
                descrizione = job.get("job_description", "") or ""

                offerta = {
                    "id_esterno":        job.get("job_id", ""),
                    "titolo":            titolo,
                    "azienda":           job.get("employer_name", "") or "Non specificata",
                    "citta":             normalizza_citta(job.get("job_city", "")),
                    "descrizione":       descrizione,
                    "url":               job.get("job_apply_link", ""),
                    "data_pubblicazione": job.get("job_posted_at_datetime_utc"),
                    "categoria_ruolo":   q["categoria"],
                    "seniority":         rileva_seniority(titolo, descrizione, exp),
                    "stipendio_min":     job.get("job_min_salary"),
                    "stipendio_max":     job.get("job_max_salary"),
                    "skill":             estrai_skill(descrizione),
                }
                offerte_processate.append(offerta)
            except Exception as e:
                print(f"  ⚠ Errore trasformazione job: {e}")

        # Caricamento
        ins, sal = carica_su_supabase(supabase, offerte_processate)
        totale_inserite += ins
        totale_saltate  += sal
        print(f"  ✅ Inserite: {ins} | Saltate (duplicati): {sal}")

    print("\n" + "=" * 60)
    print(f"ETL completato — Inserite: {totale_inserite} | Saltate: {totale_saltate}")
    print("=" * 60)

if __name__ == "__main__":
    main()
