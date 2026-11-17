import asyncio
import os
import json
import datetime
from pathlib import Path
from playwright.async_api import async_playwright
from summarizer import process_trial

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TRIALS_FILE = DATA_DIR / "trials.json"
DAILY_DIR = DATA_DIR / "daily"
SUMMARY_FILE = DATA_DIR / "summary.json"

WEB_DATA_DIR = Path(__file__).resolve().parent.parent / "web" / "data"
WEB_TRIALS_FILE = WEB_DATA_DIR / "trials.json"
WEB_SUMMARY_FILE = WEB_DATA_DIR / "summary.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
DAILY_DIR.mkdir(parents=True, exist_ok=True)
WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)

def load_existing_trials() -> list:
    if TRIALS_FILE.exists():
        try:
            with open(TRIALS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {TRIALS_FILE}: {e}")
            return []
    return []

def save_trials(all_trials: list, new_trials: list):
    # Sort all trials by date descending, then CTR descending
    all_trials.sort(
        key=lambda x: (x.get("first_disclosure_date", ""), x.get("registration_id", "")),
        reverse=True
    )
    
    with open(TRIALS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_trials, f, ensure_ascii=False, indent=2)
    with open(WEB_TRIALS_FILE, "w", encoding="utf-8") as f:
        json.dump(all_trials, f, ensure_ascii=False, indent=2)

    # Save daily batch
    today_str = datetime.date.today().isoformat()
    daily_file = DAILY_DIR / f"{today_str}.json"
    existing_daily = []
    if daily_file.exists():
        try:
            with open(daily_file, "r", encoding="utf-8") as f:
                existing_daily = json.load(f)
        except Exception:
            existing_daily = []
    
    # Merge daily uniquely
    seen_daily = {t["registration_id"] for t in existing_daily}
    for t in new_trials:
        if t["registration_id"] not in seen_daily:
            existing_daily.append(t)
            seen_daily.add(t["registration_id"])

    with open(daily_file, "w", encoding="utf-8") as f:
        json.dump(existing_daily, f, ensure_ascii=False, indent=2)

    # Generate summary stats
    new_drug_count = sum(1 for t in all_trials if t.get("is_new_drug"))
    be_count = len(all_trials) - new_drug_count
    
    summary = {
        "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_trials": len(all_trials),
        "total_new_drugs": new_drug_count,
        "total_be_studies": be_count,
        "latest_disclosure_date": all_trials[0].get("first_disclosure_date") if all_trials else today_str,
        "daily_archives": [f.stem for f in sorted(DAILY_DIR.glob("*.json"), reverse=True)]
    }
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    with open(WEB_SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"Database successfully updated. Total: {len(all_trials)} trials (New Drugs: {new_drug_count}, BE: {be_count}).")

async def parse_detail_page(detail_page, list_row_info: dict) -> dict:
    """
    Extracts structured fields from the 19 tables in the trial detail page.
    """
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

    # Extract Sponsor name specifically from Table 0 or Table 2
    sponsor = await detail_page.evaluate("""() => {
        const bodyText = document.body.innerText;
        const m = bodyText.match(/申请人名称[\\s\\t]*([^\\n\\r]+)/);
        if (m && m[1] && m[1].trim() !== '1') {
            return m[1].trim();
        }
        // Fallback to table 2 first row value
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

    # Extract sample size
    sample_size = await detail_page.evaluate("""() => {
        const bodyText = document.body.innerText;
        const m = bodyText.match(/目标入组人数[\\s\\S]*?国内:[\\s\\xa0]*(\\d+)/);
        if (m && m[1]) return m[1];
        return '';
    }""")

    # Extract primary endpoint
    endpoints = await detail_page.evaluate("""() => {
        const bodyText = document.body.innerText;
        const m = bodyText.match(/主要终点指标及评价时间[\\s\\S]*?(指标[\\s\\S]*?)(?=次要终点|二、申请人|三、临床试验|$)/);
        if (m && m[1]) {
            return m[1].replace(/\\s+/g, ' ').slice(0, 300);
        }
        return '';
    }""")

    # Extract PI and leading hospital
    lead_info = await detail_page.evaluate("""() => {
        const bodyText = document.body.innerText;
        const instMatch = bodyText.match(/机构名称[\\s\\S]*?主要研究者[\\s\\S]*?1[\\s\\n\\t]+([^\\n\\r\\t]+)[\\s\\n\\t]+([^\\n\\r\\t]+)/);
        if (instMatch && instMatch[1] && instMatch[2]) {
            return { institution: instMatch[1].trim(), pi: instMatch[2].trim() };
        }
        return { institution: '', pi: '' };
    }""")

    reg_id = raw_data.get("登记号") or list_row_info.get("ctr_id", "")
    disclosure_date = raw_data.get("首次公示信息日期") or datetime.date.today().isoformat()
    status = raw_data.get("试验状态") or list_row_info.get("status", "")
    drug_name = raw_data.get("药物名称", "").split("曾用名")[0].strip() or list_row_info.get("drug_name", "")
    drug_type = raw_data.get("药物类型") or ("化学药物" if "片" in drug_name or "胶囊" in drug_name else "生物制品")
    indication = raw_data.get("适应症") or list_row_info.get("indication", "")
    title_lay = raw_data.get("试验通俗题目") or list_row_info.get("title_lay", "")
    title_prof = raw_data.get("试验专业题目") or title_lay
    phase = raw_data.get("试验分期") or ("生物等效性试验" if "生物等效性" in title_lay else "I期")

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
        "lead_institution": lead_info.get("institution", ""),
        "principal_investigator": lead_info.get("pi", ""),
        "primary_endpoints": endpoints or "Pharmacokinetics (PK) / Safety & Tolerability",
        "cde_url": "https://www.chinadrugtrials.org.cn/clinicaltrials.searchlist.dhtml"
    }

    return trial

async def scrape_new_trials(max_items: int = 15):
    """
    Main crawling loop:
    1. Loads existing trials to avoid duplicate fetches.
    2. Navigates to search list.
    3. Finds new CTR numbers.
    4. Extracts detailed protocol and enriches with translations & executive summaries.
    """
    all_trials = load_existing_trials()
    existing_ids = {t["registration_id"] for t in all_trials}
    print(f"Loaded {len(all_trials)} existing trials from database.")

    async with async_playwright() as p:
        print("Launching Chromium browser...")
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

        print("Connecting to CDE portal (https://www.chinadrugtrials.org.cn/index.html)...")
        await page.goto("https://www.chinadrugtrials.org.cn/index.html", timeout=60000)
        await page.wait_for_timeout(3000)

        print("Navigating to search listing...")
        await page.goto("https://www.chinadrugtrials.org.cn/clinicaltrials.searchlist.dhtml", timeout=60000)
        await page.wait_for_timeout(4000)

        # Parse Page 1 rows
        rows = await page.query_selector_all("table tr")
        print(f"Found {len(rows)} table rows on Page 1.")

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
                
                candidates.append({
                    "row_index": i,
                    "ctr_id": ctr_id,
                    "status": status,
                    "drug_name": drug_name,
                    "indication": indication,
                    "title_lay": title_lay
                })

        print(f"Identified {len(candidates)} trial listings on Page 1.")

        # Determine which candidates are new
        new_candidates = [c for c in candidates if c["ctr_id"] not in existing_ids]
        print(f"New trials to ingest: {len(new_candidates)} (out of {len(candidates)})")

        if not new_candidates:
            print("No new trials registered since last run. Database is already up-to-date!")
            await browser.close()
            return []

        # Limit to max_items if specified
        new_candidates = new_candidates[:max_items]

        newly_processed = []
        for idx, candidate in enumerate(new_candidates, start=1):
            ctr_id = candidate["ctr_id"]
            print(f"[{idx}/{len(new_candidates)}] Extracting detail for {ctr_id} ({candidate['drug_name']})...")

            try:
                # Find and click the link with this CTR id
                link = await page.query_selector(f"table tr a:has-text('{ctr_id}')")
                if not link:
                    print(f"Could not find link for {ctr_id}, skipping.")
                    continue

                async with page.expect_popup() as popup_info:
                    await link.click()
                
                detail_page = await popup_info.value
                await detail_page.wait_for_load_state("networkidle")
                await detail_page.wait_for_timeout(2000)

                # Parse detailed fields
                trial_raw = await parse_detail_page(detail_page, candidate)
                await detail_page.close()

                # Process translations & executive summary
                print(f"Generating English translation & executive summary for {ctr_id}...")
                enriched_trial = process_trial(trial_raw)

                newly_processed.append(enriched_trial)
                all_trials.append(enriched_trial)

                # Respectful delay between requests
                await page.wait_for_timeout(1500)

            except Exception as e:
                print(f"Error extracting {ctr_id}: {e}")
                continue

        await browser.close()

        if newly_processed:
            print(f"Saving {len(newly_processed)} newly ingested trials to database...")
            save_trials(all_trials, newly_processed)

        return newly_processed

if __name__ == "__main__":
    asyncio.run(scrape_new_trials(max_items=15))
