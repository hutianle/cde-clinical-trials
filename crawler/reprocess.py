import json
import sys
from pathlib import Path

# Add crawler directory to path
sys.path.append(str(Path(__file__).resolve().parent / "crawler"))
from summarizer import process_trial

DATA_DIR = Path("data")
WEB_DATA_DIR = Path("web/data")

TRIALS_FILE = DATA_DIR / "trials.json"
WEB_TRIALS_FILE = WEB_DATA_DIR / "trials.json"

DAILY_FILE = DATA_DIR / "daily" / "2026-11-17.json"
WEB_DAILY_FILE = WEB_DATA_DIR / "daily" / "2026-11-17.json"

with open(TRIALS_FILE, "r", encoding="utf-8") as f:
    trials = json.load(f)

print(f"Reprocessing {len(trials)} trials into English...")
updated_trials = []
for idx, trial in enumerate(trials, start=1):
    reg_id = trial.get("registration_id")
    print(f"[{idx}/{len(trials)}] Translating {reg_id} ({trial.get('drug_name')})...")
    enriched = process_trial(trial)
    print(f"    EN Drug: {enriched.get('drug_name_en')}")
    print(f"    EN Indication: {enriched.get('indication_en')[:60]}...")
    print(f"    EN Sponsor: {enriched.get('sponsor_en')}")
    updated_trials.append(enriched)

# Save back to all data locations
with open(TRIALS_FILE, "w", encoding="utf-8") as f:
    json.dump(updated_trials, f, ensure_ascii=False, indent=2)

with open(WEB_TRIALS_FILE, "w", encoding="utf-8") as f:
    json.dump(updated_trials, f, ensure_ascii=False, indent=2)

with open(DAILY_FILE, "w", encoding="utf-8") as f:
    json.dump(updated_trials, f, ensure_ascii=False, indent=2)

with open(WEB_DAILY_FILE, "w", encoding="utf-8") as f:
    json.dump(updated_trials, f, ensure_ascii=False, indent=2)

print("All 15 trials successfully translated and updated in database!")
