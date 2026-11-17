# China CDE Clinical Trials Daily Intelligence Portal

An automated, open-access intelligence portal and database that monitors China's **Center for Drug Evaluation (CDE / NMPA)** platform ([chinadrugtrials.org.cn](https://www.chinadrugtrials.org.cn)), captures newly registered clinical trials daily (~10 new records/day), translates them into medical English, generates concise **executive summaries**, and deploys a searchable web portal to **GitHub Pages** with zero hosting costs.

---

## 🌟 Key Features

* **Anti-WAF Headless Ingestion:** Runs a Chromium instance via Playwright to seamlessly handle CDE's Ruishu (瑞数) dynamic token challenges (`MmEwMD` & `FSSBBIl1UgzbN7N80T`) without brittle JS reverse-engineering or risk of IP ban.
* **Smart Incremental Updates:** Compares Page 1 registration numbers against the master database (`data/trials.json`). Only newly disclosed trials are scraped (~10/day), avoiding redundant crawling.
* **Innovative New Drug Focus:** Categorizes registrations into **Innovative New Drugs** (Phase I–IV, cell therapy, antibodies, small molecules) versus **Generic Bioequivalence (BE)** studies.
* **AI Medical Translation & Executive Summaries:** Enriches trial metadata with English drug names, indications, modalities, and structured 4-bullet executive summaries (powered by Gemini API with rule-based fallback).
* **Git-Backed Database:** Master database stored in version-controlled JSON (`data/trials.json` and `data/daily/YYYY-MM-DD.json`), requiring no external database infrastructure.
* **Interactive Web Portal:** Modern, mobile-responsive dashboard hosted on GitHub Pages:
  * **Today's Executive Briefing:** High-impact digests of today's newly entered clinical trials.
  * **Database & Search Explorer:** Search by drug name, indication, sponsor, or CTR number in English or Chinese.
  * **Protocol Detail Modal:** Full clinical parameters (sample size, lead hospital, PI, primary endpoints).
  * **Data Export:** Instant download of filtered trials in JSON or CSV.
* **100% Free Automation:** Scheduled via GitHub Actions (`cron: '0 1 * * *'`, 09:00 AM Beijing time).

---

## 📁 Repository Structure

```
cde-clinical-trials/
├── .github/
│   └── workflows/
│       └── daily_crawl.yml        # GitHub Actions: Crawl -> Summarize -> Commit -> Deploy
├── crawler/
│   ├── scraper.py                 # Playwright crawler for chinadrugtrials.org.cn
│   └── summarizer.py              # LLM translation & executive summary generator
├── data/
│   ├── trials.json                # Master searchable database of all trials
│   ├── summary.json               # Pipeline metrics (total count, new drug count, last sync)
│   └── daily/                     # Historical daily archives (e.g. 2026-11-17.json)
├── web/
│   ├── index.html                 # Web portal UI (Tailwind CSS + Lucide Icons)
│   ├── app.js                     # Client-side search, filtering, and modal rendering
│   ├── styles.css                 # Custom styles and animations
│   └── data/                      # Local data copy served directly by GitHub Pages
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 🚀 Deployment to GitHub

### 1. Initialize Git & Push to GitHub

In your project directory, initialize git and push to your new GitHub repository:

```bash
git init
git add .
git commit -m "Initial commit: CDE Clinical Trials Portal & Daily Crawler"
git branch -M main
git remote add origin https://github.com/<YOUR_USERNAME>/<YOUR_REPO_NAME>.git
git push -u origin main
```

### 2. Configure GitHub Pages

1. In your GitHub repository, navigate to **Settings** > **Pages**.
2. Under **Build and deployment** > **Source**, select **GitHub Actions**.

### 3. Add Gemini API Key (For AI Summaries)

1. Get a free API key from [Google AI Studio](https://aistudio.google.com/).
2. In your GitHub repository, go to **Settings** > **Secrets and variables** > **Actions**.
3. Click **New repository secret**.
4. Set the name as `GEMINI_API_KEY` and paste your key.
*(Note: If no key is set, the crawler automatically uses built-in medical rule-based translations and templates so it never crashes).*

### 4. Enable Read & Write Permissions for Workflows

1. Go to **Settings** > **Actions** > **General**.
2. Scroll to **Workflow permissions**.
3. Select **Read and write permissions** and check **Allow GitHub Actions to create and approve pull requests**.
4. Click **Save**.

The workflow in `.github/workflows/daily_crawl.yml` will now execute automatically every morning at 01:00 UTC (09:00 AM Beijing time). You can also click **Run workflow** manually anytime in the **Actions** tab!

---

## 💻 Local Development & Testing

### 1. Run the Crawler Locally

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run the crawler
python crawler/scraper.py
```

### 2. Preview the Web App Locally

```bash
# Start a simple local server
python -m http.server 8000 --directory web

# Open in your browser:
# http://localhost:8000
```

---

## ⚖️ Legal & Data Usage Disclaimer

Data is retrieved publicly from the [China Drug Clinical Trial Registration and Information Platform](https://www.chinadrugtrials.org.cn) maintained by the Center for Drug Evaluation (CDE) of the National Medical Products Administration (NMPA). This project is intended for scientific research, competitive intelligence, and public informational purposes.
