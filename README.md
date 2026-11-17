# China CDE New Drug Clinical Trials Intelligence Portal

An automated, open-access intelligence portal and database that monitors China's **Center for Drug Evaluation (CDE / NMPA)** platform ([chinadrugtrials.org.cn](https://www.chinadrugtrials.org.cn)), captures newly registered **innovative new drug clinical trials** (excluding generic bioequivalence studies), translates them into medical English, generates concise **executive summaries**, and deploys a searchable web portal to **GitHub Pages** with zero hosting costs.

---

## 🌟 Progressive Building Strategy (~50 Records/Day Spaced Out)

To build the database progressively without triggering rate limits or overwhelming the CDE server:

1. **Stage 1 (Today's New Entries):** In every run, the crawler first inspects Page 1 to ensure that any new trials registered today are captured immediately.
2. **Stage 2 (Historical Backfill):** The crawler then checks its cursor in `data/state.json` (e.g. Page 2, Page 3, Page 4...) and backfills older new drug records.
3. **Timed Schedule (Every 4 Hours on GitHub Actions):**
   * Scheduled via GitHub Actions (`cron: '0 */4 * * *'` = 6 times a day).
   * Ingests ~8–10 new drug trials per run (takes ~60–90 seconds per run).
   * Smoothly builds up **~50 new drug trials per day** spaced out around the clock.
   * State cursor is committed back to Git so each run picks up right where the previous run left off.

---

## 🚀 Key Features

* **Anti-WAF Headless Ingestion:** Runs Chromium via Playwright with stealth configurations to handle CDE's Ruishu (瑞数) dynamic protection without IP bans.
* **Pure Innovative Drug Focus:** Automatically skips generic bioequivalence (BE) studies right on the listing page.
* **AI Medical Translation & Executive Summaries:** Enriches trial metadata with English drug names, clean indications, and structured 4-bullet executive summaries (powered by Gemini API with an automated rule-based translation fallback).
* **Git-Backed Database:** Stored in version-controlled JSON (`data/trials.json`, `data/state.json`, and `data/daily/YYYY-MM-DD.json`).
* **Interactive Web Portal:** Modern dashboard hosted on GitHub Pages:
  * **Today's Executive Briefing:** High-impact digests of today's newly entered new drug clinical trials.
  * **Database & Search Explorer:** Search across indications, drug names, sponsors, or CTR numbers in English or Chinese.
  * **Protocol Detail Modal:** Full clinical parameters (cohort size, lead hospital, PI, primary endpoints).
  * **Data Export:** Instant download in JSON or CSV.

---

## 📁 Repository Structure

```
cde-clinical-trials/
├── .github/
│   └── workflows/
│       └── daily_crawl.yml        # GitHub Actions: Timed cron (every 4 hrs) -> Scrape -> Translate -> Commit -> Deploy
├── crawler/
│   ├── scraper.py                 # Dual-engine crawler: checks Page 1 + backfills history from state.json
│   ├── summarizer.py              # Medical translation & executive summary generator
│   └── reprocess.py               # Utility to re-translate or re-format records
├── data/
│   ├── trials.json                # Master searchable database of all new drug trials
│   ├── state.json                 # Crawler cursor (current_history_page, total_ingested, last_run)
│   ├── summary.json               # Pipeline metrics (total count, last sync date)
│   └── daily/                     # Daily archive snapshots (e.g. 2026-11-17.json)
├── web/
│   ├── index.html                 # Web portal UI (Tailwind CSS + Lucide Icons)
│   ├── app.js                     # Client-side search, filtering, and modal rendering
│   ├── styles.css                 # Custom styling
│   └── data/                      # Local data copy served directly by GitHub Pages
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 🛠️ Deployment to GitHub

### 1. Push Local Repo to GitHub

Create a new repository on [GitHub](https://github.com/new) (e.g. `cde-clinical-trials`), then run:

```bash
git remote add origin https://github.com/<YOUR_GITHUB_USERNAME>/cde-clinical-trials.git
git push -u origin main
```

### 2. Configure GitHub Pages

1. In your GitHub repository, go to **Settings** > **Pages**.
2. Under **Build and deployment** > **Source**, choose **GitHub Actions**.

### 3. Enable Workflow Permissions & (Optional) Add API Key

1. Go to **Settings** > **Actions** > **General**.
2. Under **Workflow permissions**, select **Read and write permissions** (allows the bot to commit new daily JSON files and state cursor) and click **Save**.
3. (Optional) In **Settings** > **Secrets and variables** > **Actions**, add a repository secret named `GEMINI_API_KEY` with your free [Google AI Studio](https://aistudio.google.com/) key. *(The crawler works out-of-the-box even without an API key using built-in translation).*

The workflow in `.github/workflows/daily_crawl.yml` will now execute automatically every 4 hours, building up ~50 new drug trials every day, and deploying the website continuously.

---

## 💻 Local Testing

```bash
# Run crawler with custom batch size (e.g. 5 records)
python crawler/scraper.py

# Preview the web app locally
python -m http.server 8000 --directory web
```
