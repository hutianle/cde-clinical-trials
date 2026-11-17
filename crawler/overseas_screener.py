import json
import urllib.request
import urllib.parse
import time
import re
import csv
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_FILE = DATA_DIR / "sponsor_overseas_cache.json"

BRAND_MAP = {
    "恒瑞": "Hengrui",
    "百济": "BeiGene",
    "先声": "Simcere",
    "豪森": "Hansoh",
    "翰森": "Hansoh",
    "齐鲁": "Qilu Pharmaceutical",
    "康弘": "Kanghong",
    "海正": "Hisun",
    "贝海": "Beihai",
    "瑞博": "Ribo",
    "众生": "Zhongsheng",
    "智翔": "Zhixiang",
    "普利": "Puli",
    "人福": "Humanwell",
    "华兰": "Hualan",
    "地奥": "Diao",
    "海思盛诺": "HiSino",
    "神州细胞": "SinoCellTech",
    "剂泰": "METiS"
}

def clean_sponsor_query(sp_zh: str, sp_en: str) -> str:
    """Extracts a recognizable clean corporate entity name for ClinicalTrials.gov search."""
    if not sp_en and not sp_zh:
        return ""
    
    # Check multinational pharma companies
    if "Boehringer" in sp_en or "勃林格" in sp_zh:
        return "Boehringer Ingelheim"
    if "Eli Lilly" in sp_en or "礼来" in sp_zh:
        return "Eli Lilly"
    if "Novartis" in sp_en or "诺华" in sp_zh:
        return "Novartis"
    if "UCB" in sp_en or "优时比" in sp_zh:
        return "UCB"

    # Check curated Chinese brand names
    for zh_k, en_v in BRAND_MAP.items():
        if zh_k in sp_zh:
            return en_v

    # Fallback to cleaned English company name
    first_part = sp_en.split('/')[0].strip()
    cleaned = re.sub(
        r'\b(Co\.,?\s*Ltd\.?|Pharmaceuticals?|Biotechnology|Biopharmaceutical|Biomedical|Technology|Group|Holdings|Limited|Corp\.)\b',
        '', first_part, flags=re.I
    ).strip()
    return cleaned if len(cleaned) >= 3 else first_part

def load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cache(cache: dict):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving sponsor cache: {e}")

def check_sponsor_us_sites(sp_zh: str, sp_en: str, cache: dict) -> tuple[bool, list[str]]:
    """
    Queries ClinicalTrials.gov API v2 to confirm if the sponsor has active/completed trials with a US site.
    Uses cached results when available to minimize network latency and respect API rate limits.
    """
    cache_key = sp_zh.strip()
    if cache_key in cache:
        cached = cache[cache_key]
        return cached.get("has_us_site", False), cached.get("us_trials", [])

    query_term = clean_sponsor_query(sp_zh, sp_en)
    if not query_term or len(query_term) < 3:
        cache[cache_key] = {"has_us_site": False, "us_trials": [], "query_term": query_term}
        save_cache(cache)
        return False, []

    encoded_term = urllib.parse.quote(query_term)
    encoded_locn = urllib.parse.quote("United States")
    url = f"https://clinicaltrials.gov/api/v2/studies?query.term={encoded_term}&query.locn={encoded_locn}&pageSize=5"

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (CDE-Intelligence-BD-Tool)"})
    us_trials = []
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for s in data.get("studies", []):
                ps = s.get("protocolSection", {})
                nct = ps.get("identificationModule", {}).get("nctId")
                lead = ps.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name", "")
                collabs = [c.get("name", "") for c in ps.get("sponsorCollaboratorsModule", {}).get("collaborators", [])]
                all_sponsors = [lead] + collabs
                
                locs = ps.get("contactsLocationsModule", {}).get("locations", [])
                has_us = any(l.get("country") in ["United States", "USA", "United States of America"] for l in locs)

                # Confirm genuine sponsor match
                is_match = any(query_term.lower() in str(x).lower() for x in all_sponsors)
                if is_match and has_us and nct:
                    us_trials.append(nct)
    except Exception as e:
        print(f"ClinicalTrials.gov API warning for '{query_term}': {e}")

    has_us_site = len(us_trials) > 0
    cache[cache_key] = {
        "sponsor_en": sp_en,
        "query_term": query_term,
        "has_us_site": has_us_site,
        "us_trials": us_trials
    }
    save_cache(cache)
    time.sleep(0.2) # Courteous pacing
    return has_us_site, us_trials

def check_dual_filing(trial: dict) -> tuple[bool, list[str]]:
    """
    Checks for CDE Class 1 new drug in Phase II/III that also has an international
    registration number (dual FDA+CDE filing signal derived from crawler collected fields).
    """
    phase_en = trial.get("phase_en", "")
    is_p2_p3 = any(p in phase_en for p in ["Phase II", "Phase III"])
    if not is_p2_p3:
        return False, []

    full_text = " ".join([
        trial.get("title_lay", ""),
        trial.get("title_professional", ""),
        trial.get("drug_name", ""),
        trial.get("lead_institution", ""),
        trial.get("primary_endpoints", "")
    ])

    # International trial registration regex (e.g. NCT01234567, EUCTR, EudraCT)
    intl_numbers = re.findall(r'\b(NCT\d{8}|EUCTR\d+|EudraCT\s*\d+)\b', full_text, re.I)

    # Check for Class 1 new drug indication
    is_class1 = (
        trial.get("is_new_drug", False) and (
            "1类" in full_text or "Class 1" in full_text or "创新" in full_text or
            trial.get("category_tag") == "Innovative New Drug"
        )
    )

    if is_class1 and intl_numbers:
        return True, list(set(intl_numbers))

    return False, []

def screen_trial_overseas_signals(trial: dict, cache: dict = None) -> dict:
    """
    Evaluates overseas-intent signals for a single trial and returns updated dictionary with:
    - overseas_signals: ["us_site", "dual_filing"] (only confirmed signals; never invented)
    - overseas_intent: True / False
    """
    if cache is None:
        cache = load_cache()

    sp_zh = trial.get("sponsor", "")
    sp_en = trial.get("sponsor_en", "")

    signals = []
    us_trials = []

    # Signal (a): Sponsor has confirmed clinical trial with US site on ClinicalTrials.gov
    has_us, found_us_ncts = check_sponsor_us_sites(sp_zh, sp_en, cache)
    if has_us:
        signals.append("us_site")
        us_trials.extend(found_us_ncts)

    # Signal (b): Dual FDA+CDE filing (Phase II/III Class 1 new drug with international registration number)
    is_dual, dual_ncts = check_dual_filing(trial)
    if is_dual:
        signals.append("dual_filing")

    trial["overseas_signals"] = sorted(list(set(signals)))
    trial["overseas_intent"] = bool(trial["overseas_signals"])
    return trial

def generate_overseas_targets_report(trials: list, md_path: Path, csv_path: Path):
    """
    Generates data/overseas_targets.md and data/overseas_targets.csv
    Targeting 10-20 sponsors with confirmed global clinical signals for BD outreach.
    """
    cache = load_cache()
    
    # Group by unique sponsor
    sponsors_map = {}
    for t in trials:
        if not t.get("overseas_intent"):
            continue
        sp_zh = t.get("sponsor", "Unknown")
        sp_en = t.get("sponsor_en", sp_zh)
        ctr = t.get("registration_id")
        signals = t.get("overseas_signals", [])

        if sp_zh not in sponsors_map:
            cached_data = cache.get(sp_zh, {})
            sponsors_map[sp_zh] = {
                "sponsor_en": sp_en,
                "sponsor_zh": sp_zh,
                "signals": set(signals),
                "ctrs": [],
                "us_ncts": cached_data.get("us_trials", [])
            }
        sponsors_map[sp_zh]["signals"].update(signals)
        if ctr and ctr not in sponsors_map[sp_zh]["ctrs"]:
            sponsors_map[sp_zh]["ctrs"].append(ctr)

    # Convert to sorted list of targets
    targets = list(sponsors_map.values())
    targets.sort(key=lambda x: len(x["ctrs"]), reverse=True)

    # 1. Generate Markdown Report
    md_lines = [
        "# BD Target List: China Biopharma Sponsors with Overseas Intent",
        "",
        "> **Methodology & Source Verification:**",
        "> - **US Site Signal (`us_site`):** Confirmed clinical trial with sites in the United States registered on ClinicalTrials.gov (API v2).",
        "> - **Dual Filing Signal (`dual_filing`):** CDE Class 1 innovative candidate in Phase II/III with international trial registration identifier.",
        "> - **Manual BD Columns:** FDA IND/Orphan Drug designations and recent licensing/financing news are reserved as manual diligence fields.",
        f"> - **Generated Date:** {time.strftime('%Y-%m-%d')} | **Identified High-Priority Sponsors:** {len(targets)}",
        "",
        "| # | Sponsor (English) | Sponsor (Chinese) | Overseas Signal(s) | China CDE Trial(s) | US Trial NCT(s) | FDA IND / Orphan Status | Licensing / Financing News | Priority |",
        "| :---: | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    ]

    for idx, t in enumerate(targets, 1):
        signals_str = ", ".join([
            "US Trial Site" if s == "us_site" else "Dual FDA+CDE Filing" if s == "dual_filing" else s
            for s in sorted(t["signals"])
        ])
        ctrs_str = ", ".join(t["ctrs"])
        ncts_str = ", ".join(t["us_ncts"][:2]) if t["us_ncts"] else "N/A"
        priority = "Tier 1 (High)" if len(t["signals"]) > 1 or len(t["ctrs"]) > 1 else "Tier 2 (Active)"
        md_lines.append(
            f"| {idx} | {t['sponsor_en']} | {t['sponsor_zh']} | {signals_str} | {ctrs_str} | {ncts_str} | Pending BD Review | Pending BD Review | {priority} |"
        )

    md_lines.append("")
    md_lines.append("### Strategic BD Guidance:")
    md_lines.append("1. **Cross-Border Licensing:** Sponsors with active US clinical trials have existing regulatory momentum and overseas clinical operations.")
    md_lines.append("2. **Phase II/III Acceleration:** Sponsors in Phase II/III represent prime targets for ex-China out-licensing, co-development partnerships, and global CRO services.")
    md_lines.append("")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))
    print(f"Generated {md_path} with {len(targets)} target sponsors.")

    # 2. Generate CSV
    csv_headers = [
        "sponsor_en",
        "sponsor_zh",
        "overseas_signals",
        "cde_trials",
        "us_trials_nct",
        "fda_ind_orphan_status",
        "licensing_financing_news",
        "bd_priority"
    ]

    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(csv_headers)
        for t in targets:
            signals_str = "; ".join(sorted(t["signals"]))
            ctrs_str = "; ".join(t["ctrs"])
            ncts_str = "; ".join(t["us_ncts"])
            priority = "Tier 1 (High)" if len(t["signals"]) > 1 or len(t["ctrs"]) > 1 else "Tier 2 (Active)"
            writer.writerow([
                t["sponsor_en"],
                t["sponsor_zh"],
                signals_str,
                ctrs_str,
                ncts_str,
                "Pending BD Review",
                "Pending BD Review",
                priority
            ])
    print(f"Generated {csv_path} with {len(targets)} target sponsors.")
