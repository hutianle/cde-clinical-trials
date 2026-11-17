import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from crawler.summarizer import process_trial, has_chinese

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
WEB_DATA_DIR = Path(__file__).resolve().parent.parent / "web" / "data"

def main():
    trials_path = DATA_DIR / "trials.json"
    if not trials_path.exists():
        print("trials.json not found!")
        return

    with open(trials_path, "r", encoding="utf-8") as f:
        trials = json.load(f)

    print(f"Loaded {len(trials)} trials from {trials_path}")

    reprocessed = []
    updated_indications = 0
    updated_sponsors = 0
    updated_drugs = 0

    for i, t in enumerate(trials):
        prev_ind_en = t.get("indication_en", "")
        prev_sponsor_en = t.get("sponsor_en", "")
        prev_drug_en = t.get("drug_name_en", "")

        # Re-process with latest dictionary and translation safety checks
        enriched = process_trial(t)
        reprocessed.append(enriched)

        new_ind_en = enriched.get("indication_en", "")
        new_sponsor_en = enriched.get("sponsor_en", "")
        new_drug_en = enriched.get("drug_name_en", "")

        if prev_ind_en != new_ind_en or has_chinese(prev_ind_en):
            updated_indications += 1
            print(f"[{i+1}/{len(trials)}] {t.get('registration_id')}")
            print(f"   Indication ZH: {t.get('indication')}")
            print(f"   Indication EN: {new_ind_en}")

        if prev_sponsor_en != new_sponsor_en or has_chinese(prev_sponsor_en):
            updated_sponsors += 1

        if prev_drug_en != new_drug_en or has_chinese(prev_drug_en):
            updated_drugs += 1

    print("\n--- Reprocessing Complete ---")
    print(f"Total trials: {len(reprocessed)}")
    print(f"Indications updated: {updated_indications}")
    print(f"Sponsors updated: {updated_sponsors}")
    print(f"Drug names updated: {updated_drugs}")

    # Final verification: check for any Chinese characters in key English fields
    zh_issues = 0
    for t in reprocessed:
        for field in ["indication_en", "drug_name_en", "sponsor_en"]:
            val = str(t.get(field, ""))
            if has_chinese(val):
                print(f"WARNING: Chinese remaining in {t.get('registration_id')} {field}: {val}")
                zh_issues += 1

    if zh_issues == 0:
        print("\nAll key English fields are 100% free of Chinese characters!")
    else:
        print(f"\nFound {zh_issues} remaining Chinese occurrences.")

    # Save to data/trials.json and web/data/trials.json
    for p in [DATA_DIR / "trials.json", WEB_DATA_DIR / "trials.json"]:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(reprocessed, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(reprocessed)} records to {p}")

    # Also update daily files if they exist
    for daily_dir in [DATA_DIR / "daily", WEB_DATA_DIR / "daily"]:
        for daily_file in daily_dir.glob("*.json"):
            # Update matching records in daily file
            with open(daily_file, "r", encoding="utf-8") as f:
                daily_trials = json.load(f)
            daily_ids = {dt["registration_id"] for dt in daily_trials}
            updated_daily = [t for t in reprocessed if t["registration_id"] in daily_ids]
            with open(daily_file, "w", encoding="utf-8") as f:
                json.dump(updated_daily, f, ensure_ascii=False, indent=2)
            print(f"Updated daily file: {daily_file}")

if __name__ == "__main__":
    main()
