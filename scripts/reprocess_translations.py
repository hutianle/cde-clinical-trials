import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "crawler"))

from summarizer import process_trial, save_translation_cache, has_chinese, is_degraded_sponsor, is_degraded_lead_institution
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
    
    needs_fix = False
    sponsor_en = t.get("sponsor_en", "")
    if is_degraded_sponsor(sponsor_en):
        needs_fix = True

    ind_en = t.get("indication_en", "")
    if not ind_en or not str(ind_en).strip() or has_chinese(ind_en) or any(bad in str(ind_en) for bad in ['()', '（）']):
        needs_fix = True

    drug_en = t.get("drug_name_en", "")
    if not drug_en or not str(drug_en).strip() or has_chinese(drug_en):
        needs_fix = True
            
    lead_en = t.get("lead_institution_en", "")
    if is_degraded_lead_institution(lead_en):
        needs_fix = True

    pi_en = t.get("principal_investigator_en", "")
    if not pi_en or not str(pi_en).strip() or has_chinese(pi_en):
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
