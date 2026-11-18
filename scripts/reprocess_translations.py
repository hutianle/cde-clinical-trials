import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "crawler"))

from summarizer import process_trial, save_translation_cache, has_chinese
from overseas_screener import generate_overseas_targets_report

DATA_DIR = Path("data")
WEB_DATA_DIR = Path("web/data")

trials_file = DATA_DIR / "trials.json"
web_trials_file = WEB_DATA_DIR / "trials.json"

trials = json.loads(trials_file.read_text(encoding="utf-8"))
print(f"Loaded {len(trials)} trials for reprocessing...")

fixed_count = 0
for idx, t in enumerate(trials):
    rid = t["registration_id"]
    
    # Check if this trial has missing, chinese, or degraded translations
    needs_fix = False
    for f in ["indication_en", "drug_name_en", "sponsor_en"]:
        val = t.get(f, "")
        if not val or not str(val).strip() or has_chinese(val) or any(bad in str(val) for bad in ['()', '（）', 'BiotechCo., Ltd.', 'PharmaceuticalCo., Ltd.']):
            needs_fix = True
            break
            
    lead_en = t.get("lead_institution_en", "")
    if not lead_en or has_chinese(lead_en) or lead_en in ["UniversityHospital", "HospitalHospital", "Medical UniversityHospital"]:
        needs_fix = True

    pi_en = t.get("principal_investigator_en", "")
    if not pi_en or has_chinese(pi_en):
        needs_fix = True

    if needs_fix:
        print(f"[{idx+1}/{len(trials)}] Fixing {rid}...")
        enriched = process_trial(t)
        trials[idx] = enriched
        fixed_count += 1

print(f"\nReprocessed and fixed {fixed_count} trials.")

# Save trials.json
trials.sort(
    key=lambda x: (x.get("first_disclosure_date", ""), x.get("registration_id", "")),
    reverse=True
)
trials_file.write_text(json.dumps(trials, ensure_ascii=False, indent=2), encoding="utf-8")
web_trials_file.write_text(json.dumps(trials, ensure_ascii=False, indent=2), encoding="utf-8")

# Update daily archives
for daily_path in DATA_DIR.glob("daily/*.json"):
    daily_trials = json.loads(daily_path.read_text(encoding="utf-8"))
    daily_map = {t["registration_id"]: t for t in trials}
    updated_daily = [daily_map.get(t["registration_id"], t) for t in daily_trials]
    daily_path.write_text(json.dumps(updated_daily, ensure_ascii=False, indent=2), encoding="utf-8")
    web_daily_path = WEB_DATA_DIR / "daily" / daily_path.name
    if web_daily_path.exists():
        web_daily_path.write_text(json.dumps(updated_daily, ensure_ascii=False, indent=2), encoding="utf-8")

# Save translation cache
save_translation_cache()

# Re-generate overseas targets report
try:
    generate_overseas_targets_report(trials, DATA_DIR / "overseas_targets.md", DATA_DIR / "overseas_targets.csv")
    (WEB_DATA_DIR / "overseas_targets.md").write_text((DATA_DIR / "overseas_targets.md").read_text(encoding="utf-8"), encoding="utf-8")
    (WEB_DATA_DIR / "overseas_targets.csv").write_text((DATA_DIR / "overseas_targets.csv").read_text(encoding="utf-8"), encoding="utf-8")
except Exception as e:
    print(f"Notice: Failed to update overseas targets report: {e}")

print("Reprocessing completed successfully!")
