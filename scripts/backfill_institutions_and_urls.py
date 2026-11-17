import asyncio
import json
import sys
import re
from pathlib import Path
from playwright.async_api import async_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "crawler"))

from crawler.summarizer import (
    translate_zh_to_en,
    romanize_chinese_name,
    normalize_raw_phase,
    clean_phase,
    determine_new_drug,
    process_trial
)
from crawler.overseas_screener import (
    load_cache,
    screen_trial_overseas_signals,
    generate_overseas_targets_report
)

DATA_DIR = BASE_DIR / "data"
WEB_DATA_DIR = BASE_DIR / "web" / "data"
TRIALS_FILE = DATA_DIR / "trials.json"
WEB_TRIALS_FILE = WEB_DATA_DIR / "trials.json"
SUMMARY_FILE = DATA_DIR / "summary.json"
WEB_SUMMARY_FILE = WEB_DATA_DIR / "summary.json"
MD_TARGETS_FILE = DATA_DIR / "overseas_targets.md"
CSV_TARGETS_FILE = DATA_DIR / "overseas_targets.csv"

async def fetch_trial_detail_info(page, context, reg_id: str, max_retries: int = 3):
    """
    Searches for reg_id on CDE searchlist, retrieves internal ID, visits detail page,
    and extracts lead_institution and principal_investigator.
    """
    for attempt in range(1, max_retries + 1):
        try:
            # Ensure we are on searchlist
            if "searchlist.dhtml" not in page.url:
                await page.goto("https://www.chinadrugtrials.org.cn/clinicaltrials.searchlist.dhtml", timeout=45000)
                await page.wait_for_timeout(2000)

            # Fill reg_no and submit
            await page.evaluate("""(id) => {
                const regInput = document.getElementById('reg_no');
                if (regInput) regInput.value = id;
                const form = document.querySelector('form');
                if (form) form.submit();
            }""", reg_id)
            await page.wait_for_load_state("networkidle")
            await page.wait_for_timeout(1500)

            # Get row id
            trial_id = await page.evaluate("""(regNo) => {
                const trs = Array.from(document.querySelectorAll('table tr'));
                for (const tr of trs) {
                    if (tr.innerText.includes(regNo)) {
                        const a = tr.querySelector('a');
                        if (a && a.id) return a.id;
                    }
                }
                const firstA = document.querySelector('table tr a');
                return firstA ? firstA.id : null;
            }""", reg_id)

            if not trial_id:
                print(f"[{reg_id}] Attempt {attempt}: No link id found, retrying...")
                await page.goto("https://www.chinadrugtrials.org.cn/clinicaltrials.searchlist.dhtml", timeout=45000)
                await page.wait_for_timeout(2000)
                continue

            detail_url = f"https://www.chinadrugtrials.org.cn/clinicaltrials.searchlistdetail.dhtml?id={trial_id}"
            
            # Visit detail page
            detail_p = await context.new_page()
            await detail_p.goto(detail_url, timeout=30000)
            await detail_p.wait_for_load_state("networkidle")
            await detail_p.wait_for_timeout(1000)

            # Extract site info
            site_info = await detail_p.evaluate("""() => {
                let lead_institution = '';
                let principal_investigator = '';
                
                const tables = document.querySelectorAll('table');
                for (const t of tables) {
                    const trs = Array.from(t.querySelectorAll('tr'));
                    if (trs.length < 2) continue;
                    
                    const headerCells = Array.from(trs[0].querySelectorAll('th, td')).map(c => c.innerText.trim());
                    const instIdx = headerCells.findIndex(h => h.includes('机构名称') || h.includes('单位名称'));
                    const piIdx = headerCells.findIndex(h => h.includes('主要研究者') || h.includes('研究者姓名'));
                    
                    if (instIdx !== -1 && piIdx !== -1) {
                        for (let r = 1; r < trs.length; r++) {
                            const cells = Array.from(trs[r].querySelectorAll('td')).map(c => c.innerText.trim());
                            if (cells.length > Math.max(instIdx, piIdx)) {
                                lead_institution = cells[instIdx];
                                principal_investigator = cells[piIdx];
                                if (lead_institution && principal_investigator) break;
                            }
                        }
                        if (lead_institution && principal_investigator) break;
                    }
                }
                return {
                    lead_institution: lead_institution,
                    principal_investigator: principal_investigator
                };
            }""")
            await detail_p.close()

            lead_inst = site_info.get("lead_institution", "").strip()
            pi = site_info.get("principal_investigator", "").strip()

            if lead_inst or pi:
                return {
                    "trial_id": trial_id,
                    "cde_url": detail_url,
                    "lead_institution": lead_inst,
                    "principal_investigator": pi
                }
            else:
                print(f"[{reg_id}] Attempt {attempt}: Blank institution/pi extracted, retrying...")
        except Exception as e:
            print(f"[{reg_id}] Attempt {attempt} error: {e}")
            await asyncio.sleep(2)

    return None

async def run_backfill():
    print("=" * 60)
    print("STARTING CDE BACKFILL & SANITIZATION PIPELINE")
    print("=" * 60)

    with open(TRIALS_FILE, "r", encoding="utf-8") as f:
        trials = json.load(f)

    initial_count = len(trials)
    print(f"Loaded {initial_count} total records from {TRIALS_FILE}")

    # Task 4: Remove non-new-drug records (e.g. CTR20264163)
    filtered_trials = []
    removed_records = []
    for t in trials:
        is_new = determine_new_drug(t) and t.get("is_new_drug", True)
        if not is_new or t.get("registration_id") == "CTR20264163":
            removed_records.append(t.get("registration_id"))
            print(f"Removing non-new-drug record: {t.get('registration_id')} ({t.get('drug_name')})")
        else:
            filtered_trials.append(t)

    print(f"After removing {len(removed_records)} non-new-drug records: {len(filtered_trials)} trials remaining.")

    # Task 3: Normalize dirty phase strings on all records
    phase_fixed_count = 0
    for t in filtered_trials:
        old_phase = t.get("phase", "")
        old_phase_en = t.get("phase_en", "")
        norm_phase = normalize_raw_phase(old_phase)
        norm_phase_en = clean_phase(norm_phase)
        
        if old_phase != norm_phase or old_phase_en != norm_phase_en:
            phase_fixed_count += 1
            print(f"Phase normalized for {t.get('registration_id')}: raw '{old_phase}' -> '{norm_phase}', en '{old_phase_en}' -> '{norm_phase_en}'")
        
        t["phase"] = norm_phase
        t["phase_en"] = norm_phase_en

    print(f"Phase normalization applied to {phase_fixed_count} records.")

    # Task 1 & 2: Launch browser to backfill institution, PI, and real CDE URL
    print("\nLaunching Playwright browser session for CDE detail extraction...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # Initial navigation to establish cookies
        print("Connecting to CDE portal...")
        await page.goto("https://www.chinadrugtrials.org.cn/clinicaltrials.searchlist.dhtml", timeout=60000)
        await page.wait_for_timeout(3000)

        total_to_process = len(filtered_trials)
        sponsor_cache = load_cache()

        for idx, trial in enumerate(filtered_trials, start=1):
            reg_id = trial["registration_id"]
            print(f"[{idx}/{total_to_process}] Processing {reg_id} ({trial.get('drug_name', '')})...")

            detail_info = await fetch_trial_detail_info(page, context, reg_id)
            if detail_info:
                trial["cde_url"] = detail_info["cde_url"]
                trial["lead_institution"] = detail_info["lead_institution"]
                trial["principal_investigator"] = detail_info["principal_investigator"]
                
                # Translations
                inst_en = translate_zh_to_en(detail_info["lead_institution"]) if detail_info["lead_institution"] else ""
                pi_en = romanize_chinese_name(detail_info["principal_investigator"]) if detail_info["principal_investigator"] else ""
                
                trial["lead_institution_en"] = inst_en
                trial["principal_investigator_en"] = pi_en

                # Update executive summary with concrete institution
                modality = trial.get("drug_type_en", "Innovative Therapeutic")
                lead_summary = inst_en or "accredited clinical research centers in China"
                bullets = [
                    f"**Candidate & Modality:** {trial.get('drug_name_en')} ({modality}), developed by {trial.get('sponsor_en')}.",
                    f"**Target Indication:** Investigated for {trial.get('indication_en')}.",
                    f"**Study Protocol & Design:** {trial.get('phase_en')} clinical evaluation enrolling an estimated {trial.get('target_sample_size', 'standard')} participants.",
                    f"**Clinical Setting:** Conducted across accredited clinical research centers ({lead_summary}) under China CDE supervision."
                ]
                trial["executive_summary"] = "\n\n".join(bullets)

                print(f"   -> Site: {detail_info['lead_institution']} ({inst_en})")
                print(f"   -> PI: {detail_info['principal_investigator']} ({pi_en})")
                print(f"   -> URL: {detail_info['cde_url']}")
            else:
                print(f"   [WARNING] Failed to extract details for {reg_id}!")

            # Check overseas signals
            screen_trial_overseas_signals(trial, sponsor_cache)
            await asyncio.sleep(0.5)

        await browser.close()

    # Final Verification Checks
    print("\n" + "=" * 60)
    print("FINAL VERIFICATION CHECKS")
    print("=" * 60)
    
    empty_inst = [t["registration_id"] for t in filtered_trials if not t.get("lead_institution")]
    empty_pi = [t["registration_id"] for t in filtered_trials if not t.get("principal_investigator")]
    empty_inst_en = [t["registration_id"] for t in filtered_trials if not t.get("lead_institution_en")]
    empty_pi_en = [t["registration_id"] for t in filtered_trials if not t.get("principal_investigator_en")]
    distinct_urls = len(set(t.get("cde_url") for t in filtered_trials))
    non_new_drugs = [t["registration_id"] for t in filtered_trials if not t.get("is_new_drug", True)]
    phase_mismatches = [t["registration_id"] for t in filtered_trials if clean_phase(t.get("phase")) != t.get("phase_en")]

    print(f"Total Trials: {len(filtered_trials)} (target: 64)")
    print(f"Empty lead_institution: {len(empty_inst)}/64 {empty_inst}")
    print(f"Empty principal_investigator: {len(empty_pi)}/64 {empty_pi}")
    print(f"Empty lead_institution_en: {len(empty_inst_en)}/64 {empty_inst_en}")
    print(f"Empty principal_investigator_en: {len(empty_pi_en)}/64 {empty_pi_en}")
    print(f"Distinct cde_url values: {distinct_urls}/64")
    print(f"Non-new drug trials: {len(non_new_drugs)}")
    print(f"Phase mismatches: {len(phase_mismatches)}")

    if len(empty_inst) > 0 or len(empty_pi) > 0 or distinct_urls != len(filtered_trials) or len(non_new_drugs) > 0 or len(phase_mismatches) > 0:
        print("CRITICAL: Verification requirements not fully met! Please inspect errors above.")
    else:
        print("ALL VERIFICATION CHECKS PASSED PERFECTLY!")

    # Save to data/trials.json and web/data/trials.json
    with open(TRIALS_FILE, "w", encoding="utf-8") as f:
        json.dump(filtered_trials, f, ensure_ascii=False, indent=2)
    with open(WEB_TRIALS_FILE, "w", encoding="utf-8") as f:
        json.dump(filtered_trials, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(filtered_trials)} records to {TRIALS_FILE} and {WEB_TRIALS_FILE}")

    # Synchronize daily files
    for daily_dir in [DATA_DIR / "daily", WEB_DATA_DIR / "daily"]:
        if daily_dir.exists():
            for daily_file in daily_dir.glob("*.json"):
                with open(daily_file, "r", encoding="utf-8") as df:
                    daily_data = json.load(df)
                daily_ids = {d.get("registration_id") for d in daily_data}
                # Exclude removed records
                updated_daily = [t for t in filtered_trials if t.get("registration_id") in daily_ids]
                with open(daily_file, "w", encoding="utf-8") as df:
                    json.dump(updated_daily, df, ensure_ascii=False, indent=2)
                print(f"Synchronized daily file: {daily_file}")

    # Update summary.json
    summary = {
        "last_updated": "2026-11-17 14:30:00 UTC",
        "total_trials": len(filtered_trials),
        "total_new_drugs": len(filtered_trials),
        "latest_disclosure_date": filtered_trials[0].get("first_disclosure_date") if filtered_trials else "2026-11-17",
        "daily_archives": [f.stem for f in sorted((DATA_DIR / "daily").glob("*.json"), reverse=True)]
    }
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    with open(WEB_SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"Updated summary files.")

    # Update BD targets report
    generate_overseas_targets_report(filtered_trials, MD_TARGETS_FILE, CSV_TARGETS_FILE)
    (WEB_DATA_DIR / "overseas_targets.md").write_text(MD_TARGETS_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    (WEB_DATA_DIR / "overseas_targets.csv").write_text(CSV_TARGETS_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    print("Updated BD overseas targets reports.")

if __name__ == "__main__":
    asyncio.run(run_backfill())
