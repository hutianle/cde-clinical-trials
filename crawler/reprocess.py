import json
import sys
import re
from pathlib import Path

# Add project root and crawler directory to path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "crawler"))

from crawler.summarizer import process_trial, clean_phase, has_chinese
from crawler.overseas_screener import (
    load_cache,
    screen_trial_overseas_signals,
    generate_overseas_targets_report
)

DATA_DIR = BASE_DIR / "data"
WEB_DATA_DIR = BASE_DIR / "web" / "data"

TRIALS_FILE = DATA_DIR / "trials.json"
WEB_TRIALS_FILE = WEB_DATA_DIR / "trials.json"
MD_TARGETS_FILE = DATA_DIR / "overseas_targets.md"
CSV_TARGETS_FILE = DATA_DIR / "overseas_targets.csv"

def verify_phase_consistency(trial: dict) -> bool:
    """Verifies that phase and phase_en are strictly consistent."""
    raw_p = trial.get("phase", "")
    p_en = trial.get("phase_en", "")
    expected_en = clean_phase(raw_p)

    if p_en != expected_en:
        print(f"[MISMATCH ERROR] {trial.get('registration_id')}: raw='{raw_p}', current_en='{p_en}', expected='{expected_en}'")
        return False
    return True

def main():
    if not TRIALS_FILE.exists():
        print(f"Error: {TRIALS_FILE} does not exist!")
        sys.exit(1)

    with open(TRIALS_FILE, "r", encoding="utf-8") as f:
        trials = json.load(f)

    print(f"--- Reprocessing {len(trials)} trials ---")
    print("1. Enforcing strict phase mapping (I期 -> Phase I, II期 -> Phase II, III期 -> Phase III, IV期 -> Phase IV, full-width Ⅰ/Ⅱ/Ⅲ/Ⅳ, compounds)")
    print("2. Enforcing 100% English medical translation for indications, drug names, and sponsors")
    print("3. Computing overseas-intent signals (US sites via ClinicalTrials.gov API v2 & Dual FDA+CDE filing)")

    sponsor_cache = load_cache()
    updated_trials = []
    phase_corrections = 0
    phase_mismatches = 0

    for idx, trial in enumerate(trials, start=1):
        reg_id = trial.get("registration_id")
        old_phase_en = trial.get("phase_en", "")
        raw_phase = trial.get("phase", "")
        
        # Re-process with updated summarizer
        enriched = process_trial(trial)
        
        # Compute overseas-intent signals
        screen_trial_overseas_signals(enriched, sponsor_cache)

        new_phase_en = enriched.get("phase_en", "")
        if old_phase_en != new_phase_en:
            phase_corrections += 1
            print(f"[{idx}/{len(trials)}] {reg_id} Phase Corrected: raw='{raw_phase}' | was: '{old_phase_en}' -> now: '{new_phase_en}'")

        # Verify phase consistency
        if not verify_phase_consistency(enriched):
            phase_mismatches += 1

        updated_trials.append(enriched)

    print(f"\n--- Reprocessing Phase Summary ---")
    print(f"Total trials processed: {len(updated_trials)}")
    print(f"Phase corrections applied: {phase_corrections}")
    print(f"Phase mismatches remaining: {phase_mismatches}")

    if phase_mismatches > 0:
        print(f"FATAL: Found {phase_mismatches} phase mismatches! Halting save.")
        sys.exit(1)

    # Save to data/trials.json and web/data/trials.json
    with open(TRIALS_FILE, "w", encoding="utf-8") as f:
        json.dump(updated_trials, f, ensure_ascii=False, indent=2)
    with open(WEB_TRIALS_FILE, "w", encoding="utf-8") as f:
        json.dump(updated_trials, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(updated_trials)} trials to {TRIALS_FILE} and {WEB_TRIALS_FILE}")

    # Synchronize daily files
    for daily_dir in [DATA_DIR / "daily", WEB_DATA_DIR / "daily"]:
        if daily_dir.exists():
            for daily_file in daily_dir.glob("*.json"):
                with open(daily_file, "r", encoding="utf-8") as df:
                    daily_data = json.load(df)
                daily_ids = {d.get("registration_id") for d in daily_data}
                updated_daily = [t for t in updated_trials if t.get("registration_id") in daily_ids]
                with open(daily_file, "w", encoding="utf-8") as df:
                    json.dump(updated_daily, df, ensure_ascii=False, indent=2)
                print(f"Updated daily snapshot: {daily_file}")

    # Generate BD Overseas Targets Report
    print("\n--- Generating BD Overseas Targets Report ---")
    generate_overseas_targets_report(updated_trials, MD_TARGETS_FILE, CSV_TARGETS_FILE)

    # Also copy targets to web/data if helpful
    web_md = WEB_DATA_DIR / "overseas_targets.md"
    web_csv = WEB_DATA_DIR / "overseas_targets.csv"
    with open(web_md, "w", encoding="utf-8") as f:
        f.write(MD_TARGETS_FILE.read_text(encoding="utf-8"))
    with open(web_csv, "w", encoding="utf-8") as f:
        f.write(CSV_TARGETS_FILE.read_text(encoding="utf-8"))

    # Summary count of overseas intent
    overseas_count = sum(1 for t in updated_trials if t.get("overseas_intent"))
    print(f"\nAll {len(updated_trials)} records successfully updated!")
    print(f"Trials with Overseas Intent: {overseas_count}/{len(updated_trials)}")
    print(f"Verified: Zero phase mismatches across database.")

if __name__ == "__main__":
    main()
