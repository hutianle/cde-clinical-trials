import asyncio
import os
import sys
import json
import datetime
import re
from pathlib import Path
from playwright.async_api import async_playwright

# Force unbuffered output so logs appear immediately
sys.stdout.reconfigure(line_buffering=True)

from summarizer import process_trial, normalize_raw_phase, determine_new_drug
from overseas_screener import screen_trial_overseas_signals, generate_overseas_targets_report

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TRIALS_FILE = DATA_DIR / "trials.json"
DAILY_DIR = DATA_DIR / "daily"
SUMMARY_FILE = DATA_DIR / "summary.json"
STATE_FILE = DATA_DIR / "state.json"

WEB_DATA_DIR = Path(__file__).resolve().parent.parent / "web" / "data"
WEB_TRIALS_FILE = WEB_DATA_DIR / "trials.json"
WEB_SUMMARY_FILE = WEB_DATA_DIR / "summary.json"
WEB_STATE_FILE = WEB_DATA_DIR / "state.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
DAILY_DIR.mkdir(parents=True, exist_ok=True)
WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Default batch target per execution: 10 records.
# When run 5 times a day spaced out, this achieves ~50 new drug records per day!
RUN_TARGET = int(os.environ.get("RUN_TARGET", "10"))

def is_generic_be_study(text: str) -> bool:
    """
    Checks if a trial is a generic bioequivalence (BE) study.
    Returns True if it's a generic BE study (to be skipped).
    """
    text_lower = str(text).lower()
    return any(k in text_lower for k in [
        "生物等效性", "be试验", "bioequivalence", "等效性研究", "等效性试验",
        "仿制药", "参比制剂", "双交叉空腹", "受试制剂与参比制剂"
    ])

def load_existing_trials() -> list:
    if TRIALS_FILE.exists():
        try:
            with open(TRIALS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {TRIALS_FILE}: {e}")
            return []
    return []

def load_crawler_state() -> dict:
    default_state = {
        "current_history_page": 2,
        "total_ingested": 0,
        "last_run": None,
        "daily_target": 50,
        "run_target": RUN_TARGET
    }
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
                return {**default_state, **state}
        except Exception:
            return default_state
    return default_state

def save_crawler_state(state: dict):
    state["last_run"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    with open(WEB_STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def save_trials(all_trials: list, new_trials: list):
    all_trials.sort(
        key=lambda x: (x.get("first_disclosure_date", ""), x.get("registration_id", "")),
        reverse=True
    )
    
    with open(TRIALS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_trials, f, ensure_ascii=False, indent=2)
    with open(WEB_TRIALS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_trials, f, ensure_ascii=False, indent=2)

    today_str = datetime.date.today().isoformat()
    daily_file = DAILY_DIR / f"{today_str}.json"
    web_daily_file = WEB_DATA_DIR / "daily" / f"{today_str}.json"
    web_daily_file.parent.mkdir(parents=True, exist_ok=True)

    existing_daily = []
    if daily_file.exists():
        try:
            with open(daily_file, "r", encoding="utf-8") as f:
                existing_daily = json.load(f)
        except Exception:
            existing_daily = []
    
    seen_daily = {t["registration_id"] for t in existing_daily}
    for t in new_trials:
        if t["registration_id"] not in seen_daily:
            existing_daily.append(t)
            seen_daily.add(t["registration_id"])

    with open(daily_file, "w", encoding="utf-8") as f:
        json.dump(existing_daily, f, ensure_ascii=False, indent=2)
    with open(web_daily_file, "w", encoding="utf-8") as f:
        json.dump(existing_daily, f, ensure_ascii=False, indent=2)

    summary = {
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_trials": len(all_trials),
        "total_new_drugs": len(all_trials),
        "latest_disclosure_date": all_trials[0].get("first_disclosure_date") if all_trials else today_str,
        "daily_archives": [f.stem for f in sorted(DAILY_DIR.glob("*.json"), reverse=True)]
    }
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    with open(WEB_SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # Generate and update BD overseas targets report
    try:
        generate_overseas_targets_report(all_trials, DATA_DIR / "overseas_targets.md", DATA_DIR / "overseas_targets.csv")
        (WEB_DATA_DIR / "overseas_targets.md").write_text((DATA_DIR / "overseas_targets.md").read_text(encoding="utf-8"), encoding="utf-8")
        (WEB_DATA_DIR / "overseas_targets.csv").write_text((DATA_DIR / "overseas_targets.csv").read_text(encoding="utf-8"), encoding="utf-8")
    except Exception as e:
        print(f"Notice: Failed to update overseas targets report: {e}")

    print(f"Database successfully updated. Total: {len(all_trials)} new drug clinical trials.")

async def parse_detail_page(detail_page, list_row_info: dict) -> dict:
    raw_data = await detail_page.evaluate("""() => {
        const result = {};
        const tables = document.querySelectorAll('table');
        tables.forEach((t) => {
            const rows = t.querySelectorAll('tr');
            rows.forEach(r => {
                const cells = Array.from(r.querySelectorAll('th, td')).map(c => c.innerText.trim());
                for (let i = 0; i < cells.length; i += 2) {
                    if (cells[i] && cells[i+1] && !result[cells[i]]) {
                        result[cells[i]] = cells[i+1];
                    }
                }
            });
        });
        return result;
    }""")

    sponsor = await detail_page.evaluate("""() => {
        const bodyText = document.body.innerText;
        const m = bodyText.match(/申请人名称[\\s\\t]*([^\\n\\r]+)/);
        if (m && m[1] && m[1].trim() !== '1') {
            return m[1].trim();
        }
        const tables = document.querySelectorAll('table');
        for (let t of tables) {
            const text = t.innerText;
            if (text.includes('企业名称') || text.includes('申请人名称')) {
                const lines = text.split('\\n').map(l => l.trim()).filter(Boolean);
                for (let i = 0; i < lines.length; i++) {
                    if ((lines[i] === '申请人名称' || lines[i] === '企业名称') && lines[i+1]) {
                        return lines[i+1];
                    }
                }
            }
        }
        return '';
    }""")

    sample_size = await detail_page.evaluate("""() => {
        const bodyText = document.body.innerText;
        const m = bodyText.match(/目标入组人数[\\s\\S]*?国内:[\\s\\xa0]*(\\d+)/);
        if (m && m[1]) return m[1];
        return '';
    }""")

    endpoints = await detail_page.evaluate("""() => {
        const bodyText = document.body.innerText;
        const m = bodyText.match(/主要终点指标及评价时间[\\s\\S]*?(指标[\\s\\S]*?)(?=次要终点|二、申请人|三、临床试验|$)/);
        if (m && m[1]) {
            return m[1].replace(/\\s+/g, ' ').slice(0, 300);
        }
        return '';
    }""")

    site_and_url_info = await detail_page.evaluate("""() => {
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
        
        let trial_id = '';
        const idInput = document.querySelector('input[name="id"]');
        if (idInput && idInput.value) {
            trial_id = idInput.value.trim();
        }

        return {
            institution: lead_institution,
            pi: principal_investigator,
            trial_id: trial_id
        };
    }""")

    reg_id = raw_data.get("登记号") or list_row_info.get("ctr_id", "")
    disclosure_date = raw_data.get("首次公示信息日期") or datetime.date.today().isoformat()
    status = raw_data.get("试验状态") or list_row_info.get("status", "")
    drug_name = raw_data.get("药物名称", "").split("曾用名")[0].strip() or list_row_info.get("drug_name", "")
    drug_type = raw_data.get("药物类型") or ("化学药物" if "片" in drug_name or "胶囊" in drug_name else "生物制品")
    indication = raw_data.get("适应症") or list_row_info.get("indication", "")
    title_lay = raw_data.get("试验通俗题目") or list_row_info.get("title_lay", "")
    title_prof = raw_data.get("试验专业题目") or title_lay
    raw_phase = raw_data.get("试验分期") or "I期"
    phase = normalize_raw_phase(raw_phase)

    trial_internal_id = site_and_url_info.get("trial_id") or list_row_info.get("row_id", "")
    if trial_internal_id:
        cde_url = f"https://www.chinadrugtrials.org.cn/clinicaltrials.searchlistdetail.dhtml?id={trial_internal_id}"
    else:
        cde_url = detail_page.url

    trial = {
        "registration_id": reg_id,
        "first_disclosure_date": disclosure_date,
        "status": status,
        "sponsor": sponsor or raw_data.get("申请人联系人", "Unknown Sponsor"),
        "drug_name": drug_name,
        "drug_type": drug_type,
        "indication": indication,
        "title_lay": title_lay,
        "title_professional": title_prof,
        "phase": phase,
        "target_sample_size": sample_size or "30-100",
        "lead_institution": site_and_url_info.get("institution", ""),
        "principal_investigator": site_and_url_info.get("pi", ""),
        "primary_endpoints": endpoints or "Safety, Tolerability & Pharmacokinetics (PK)",
        "is_new_drug": True,
        "cde_url": cde_url
    }

    return trial

async def get_page_candidates(page, existing_ids: set) -> list:
    rows = await page.query_selector_all("table tr")
    candidates = []
    for i, row in enumerate(rows[1:], start=1):
        text = await row.inner_text()
        parts = [p.strip() for p in text.split("\t") if p.strip()]
        if len(parts) >= 5 and "CTR" in parts[1]:
            ctr_id = parts[1]
            status = parts[2]
            drug_name = parts[3]
            indication = parts[4]
            title_lay = parts[5] if len(parts) > 5 else parts[4]

            # Filter out generic BE
            full_text = f"{title_lay} {drug_name} {indication}"
            if is_generic_be_study(full_text):
                continue
            
            if ctr_id not in existing_ids:
                candidates.append({
                    "row_index": i,
                    "ctr_id": ctr_id,
                    "status": status,
                    "drug_name": drug_name,
                    "indication": indication,
                    "title_lay": title_lay
                })
    return candidates

async def navigate_to_page(page, page_number: int):
    print(f"Navigating to CDE listing Page {page_number}...")
    async with page.expect_navigation():
        await page.evaluate(f"""() => {{
            const f = document.forms[0];
            if (f) {{
                f.action = 'https://www.chinadrugtrials.org.cn/clinicaltrials.searchlist.dhtml';
                f.target = '_self';
                const input = document.querySelector("input[name='currentpage']");
                if (input) input.value = '{page_number}';
                f.submit();
            }}
        }}""")
    await page.wait_for_timeout(2500)

async def run_crawl_session(target_count: int = RUN_TARGET):
    all_trials = load_existing_trials()
    existing_ids = {t["registration_id"] for t in all_trials}
    crawler_state = load_crawler_state()
    history_page = crawler_state.get("current_history_page", 2)

    print("=" * 60)
    print(f"Starting CDE Crawl Session | Batch Target: {target_count} new drug trials")
    print(f"Existing DB: {len(all_trials)} trials | History Page Cursor: {history_page}")
    print("=" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox"
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        page = await context.new_page()

        print("Connecting to CDE portal...")
        await page.goto("https://www.chinadrugtrials.org.cn/index.html", timeout=60000)
        await page.wait_for_timeout(3000)

        # -------------------------------------------------------------
        # STAGE 1: Check Page 1 (Today's New Registrations)
        # -------------------------------------------------------------
        print("\n--- STAGE 1: Checking Page 1 for Today's New Registrations ---")
        await page.goto("https://www.chinadrugtrials.org.cn/clinicaltrials.searchlist.dhtml", timeout=60000)
        await page.wait_for_timeout(4000)

        page1_candidates = await get_page_candidates(page, existing_ids)
        print(f"Page 1: Found {len(page1_candidates)} unseen new drug candidates.")

        newly_ingested = []

        for cand in page1_candidates:
            if len(newly_ingested) >= target_count:
                break
            ctr_id = cand["ctr_id"]
            existing_ids.add(ctr_id) # Ensure seen

            print(f"[Today's New] Ingesting {ctr_id} ({cand['drug_name']})...")
            try:
                link = await page.query_selector(f"table tr a:has-text('{ctr_id}')")
                if not link:
                    continue
                cand["row_id"] = await link.get_attribute("id")
                async with page.expect_popup() as popup_info:
                    await link.click()
                detail_page = await popup_info.value
                await detail_page.wait_for_load_state("networkidle")
                await detail_page.wait_for_timeout(2000)

                trial_raw = await parse_detail_page(detail_page, cand)
                await detail_page.close()

                if is_generic_be_study(f"{trial_raw.get('title_lay')} {trial_raw.get('title_professional')} {trial_raw.get('drug_name')} {trial_raw.get('phase')}"):
                    print(f"Skipping {ctr_id} (identified as BE).")
                    continue

                enriched = process_trial(trial_raw)
                if not enriched.get("is_new_drug", True):
                    print(f"Skipping {ctr_id} (is_new_drug is False).")
                    continue

                screen_trial_overseas_signals(enriched)
                newly_ingested.append(enriched)
                all_trials.append(enriched)
                await page.wait_for_timeout(1200)
            except Exception as e:
                print(f"Error extracting {ctr_id}: {e}")

        # -------------------------------------------------------------
        # STAGE 2: Historical Backfill
        # -------------------------------------------------------------
        remaining_needed = target_count - len(newly_ingested)
        print(f"\n--- STAGE 2: Historical Backfill (Quota remaining: {remaining_needed}) ---")

        while remaining_needed > 0 and history_page <= 1500:
            await navigate_to_page(page, history_page)
            hist_candidates = await get_page_candidates(page, existing_ids)
            print(f"Page {history_page}: Found {len(hist_candidates)} new drug candidates.")

            if hist_candidates:
                for cand in hist_candidates:
                    if remaining_needed <= 0:
                        break
                    ctr_id = cand["ctr_id"]
                    existing_ids.add(ctr_id)

                    print(f"[Backfill P{history_page}] Ingesting {ctr_id} ({cand['drug_name']})...")
                    try:
                        link = await page.query_selector(f"table tr a:has-text('{ctr_id}')")
                        if not link:
                            continue
                        cand["row_id"] = await link.get_attribute("id")
                        async with page.expect_popup() as popup_info:
                            await link.click()
                        detail_page = await popup_info.value
                        await detail_page.wait_for_load_state("networkidle")
                        await detail_page.wait_for_timeout(2000)

                        trial_raw = await parse_detail_page(detail_page, cand)
                        await detail_page.close()

                        if is_generic_be_study(f"{trial_raw.get('title_lay')} {trial_raw.get('title_professional')} {trial_raw.get('drug_name')} {trial_raw.get('phase')}"):
                            print(f"Skipping {ctr_id} (identified as BE).")
                            continue

                        enriched = process_trial(trial_raw)
                        if not enriched.get("is_new_drug", True):
                            print(f"Skipping {ctr_id} (is_new_drug is False).")
                            continue

                        screen_trial_overseas_signals(enriched)
                        newly_ingested.append(enriched)
                        all_trials.append(enriched)
                        remaining_needed -= 1
                        print(f"   -> Enriched {ctr_id}. (Quota left: {remaining_needed})")
                        await page.wait_for_timeout(1200)
                    except Exception as e:
                        print(f"Error extracting {ctr_id}: {e}")

            # Advance to the next historical page
            history_page += 1

        await browser.close()

        # Save state and database
        crawler_state["current_history_page"] = history_page
        crawler_state["total_ingested"] = len(all_trials)
        save_crawler_state(crawler_state)

        if newly_ingested:
            print(f"\nSuccessfully ingested and translated {len(newly_ingested)} new drug clinical trials.")
            save_trials(all_trials, newly_ingested)
        else:
            print("\nNo new records ingested this session. Everything up to date.")

        print(f"History Page Cursor now at: Page {history_page}")
        print("=" * 60)
        return newly_ingested

if __name__ == "__main__":
    asyncio.run(run_crawl_session())
