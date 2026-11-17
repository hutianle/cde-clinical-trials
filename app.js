// China CDE Clinical Trials Web Portal Application Logic

let allTrials = [];
let summaryData = {};
let currentTab = 'today';
let currentTodayFilter = 'all';
let currentArchiveDate = null;

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", async () => {
  await loadData();
  initTabs();
  renderTodayBriefing();
  renderDatabaseTable(allTrials);
  renderArchiveList();
  lucide.createIcons();
});

// Load trials and summary data
async function loadData() {
  const possiblePaths = [
    'data/trials.json',
    '../data/trials.json',
    './data/trials.json'
  ];

  for (const path of possiblePaths) {
    try {
      const resp = await fetch(path);
      if (resp.ok) {
        allTrials = await resp.json();
        break;
      }
    } catch (e) {
      // try next path
    }
  }

  // Load summary
  const summaryPaths = [
    'data/summary.json',
    '../data/summary.json',
    './data/summary.json'
  ];
  for (const path of summaryPaths) {
    try {
      const resp = await fetch(path);
      if (resp.ok) {
        summaryData = await resp.json();
        break;
      }
    } catch (e) {
      // try next
    }
  }

  // Update header stats
  if (summaryData.last_updated) {
    document.getElementById("stat-last-sync").innerText = summaryData.last_updated.split(" ")[0];
  } else {
    document.getElementById("stat-last-sync").innerText = "Today";
  }

  document.getElementById("stat-total-trials").innerText = allTrials.length || summaryData.total_trials || "0";
  
  // Calculate today's count
  const latestDate = summaryData.latest_disclosure_date || (allTrials[0] ? allTrials[0].first_disclosure_date : '');
  const todayTrials = allTrials.filter(t => t.first_disclosure_date === latestDate);
  document.getElementById("today-count-badge").innerText = todayTrials.length;
  
  const dateDisplay = document.getElementById("today-date-display");
  if (dateDisplay && latestDate) {
    dateDisplay.innerText = `Disclosed Date: ${latestDate} (${todayTrials.length} trials entered)`;
  }
}

// Tab Switching
function switchTab(tabName) {
  currentTab = tabName;
  const tabs = ['today', 'database', 'archive'];

  tabs.forEach(t => {
    const section = document.getElementById(`tab-${t}`);
    const btn = document.getElementById(`tab-${t}-btn`);
    if (t === tabName) {
      section.classList.remove('hidden');
      btn.className = "py-4 px-1 border-b-2 font-medium text-sm border-emerald-600 text-emerald-600 flex items-center space-x-2";
    } else {
      section.classList.add('hidden');
      btn.className = "py-4 px-1 border-b-2 font-medium text-sm border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300 flex items-center space-x-2";
    }
  });

  lucide.createIcons();
}

function initTabs() {
  // Tabs are linked via onclick in HTML
}

// -------------------------------------------------------------
// TAB 1: TODAY'S EXECUTIVE BRIEFING
// -------------------------------------------------------------
function filterToday(filterType) {
  currentTodayFilter = filterType;
  // Update button active state
  document.querySelectorAll(".today-filter-btn").forEach(btn => {
    if (btn.dataset.filter === filterType) {
      btn.className = "today-filter-btn px-3 py-1 text-xs font-medium rounded-full bg-slate-900 text-white shadow-sm";
    } else {
      btn.className = "today-filter-btn px-3 py-1 text-xs font-medium rounded-full bg-white text-slate-700 hover:bg-slate-100 border border-slate-200";
    }
  });

  renderTodayBriefing();
}

function renderTodayBriefing() {
  const container = document.getElementById("today-cards-container");
  const latestDate = summaryData.latest_disclosure_date || (allTrials[0] ? allTrials[0].first_disclosure_date : '');
  
  let trials = allTrials.filter(t => t.first_disclosure_date === latestDate);
  if (trials.length === 0) {
    trials = allTrials.slice(0, 10); // Fallback to latest 10
  }

  if (currentTodayFilter === 'new_drug') {
    trials = trials.filter(t => t.is_new_drug);
  } else if (currentTodayFilter === 'be') {
    trials = trials.filter(t => !t.is_new_drug);
  }

  if (trials.length === 0) {
    container.innerHTML = `
      <div class="col-span-full py-12 text-center text-slate-400 bg-white rounded-xl border border-slate-200">
        No trials found matching the selected filter for today.
      </div>`;
    return;
  }

  container.innerHTML = trials.map(trial => createTrialCard(trial)).join("");
  lucide.createIcons();
}

function formatMarkdownSummary(text) {
  if (!text) return "";
  // Simple markdown bullet to html converter
  const lines = text.split("\n\n");
  return lines.map(line => {
    line = line.replace(/^\*\*(.*?)\*\*:/g, '<strong class="text-slate-900">$1:</strong>');
    line = line.replace(/^\*\*(.*?)\*\*/g, '<strong class="text-slate-900">$1</strong>');
    return `<div class="mb-2 text-xs text-slate-600 leading-relaxed">${line}</div>`;
  }).join("");
}

function createTrialCard(trial) {
  const isNew = trial.is_new_drug;
  const categoryBadge = isNew
    ? `<span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200 flex items-center space-x-1">
         <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
         <span>Innovative New Drug</span>
       </span>`
    : `<span class="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
         Generic Bioequivalence (BE)
       </span>`;

  let phaseBadgeColor = "bg-blue-100 text-blue-800 border-blue-200";
  if (trial.phase_en.includes("Phase III")) phaseBadgeColor = "bg-purple-100 text-purple-800 border-purple-200";
  if (trial.phase_en.includes("Phase II")) phaseBadgeColor = "bg-indigo-100 text-indigo-800 border-indigo-200";
  if (trial.phase_en.includes("BE")) phaseBadgeColor = "bg-slate-100 text-slate-600 border-slate-200";

  return `
    <div class="trial-card bg-white rounded-xl border border-slate-200 p-6 flex flex-col justify-between shadow-sm hover:border-emerald-300">
      <div>
        <!-- Badges and Registration ID -->
        <div class="flex items-center justify-between mb-3 gap-2">
          <div class="flex flex-wrap items-center gap-1.5">
            ${categoryBadge}
            <span class="px-2 py-0.5 rounded text-xs font-medium border ${phaseBadgeColor}">
              ${escapeHtml(trial.phase_en.replace(/[\n\t]/g, ' ').slice(0, 20))}
            </span>
          </div>
          <span class="text-xs font-mono font-bold text-slate-400">${trial.registration_id}</span>
        </div>

        <!-- Drug Title -->
        <h3 class="text-base font-bold text-slate-900 leading-snug mb-1">
          ${escapeHtml(trial.drug_name_en || trial.drug_name)}
        </h3>
        ${trial.drug_name !== trial.drug_name_en ? `<p class="text-xs text-slate-400 mb-3">${escapeHtml(trial.drug_name)}</p>` : '<div class="mb-3"></div>'}

        <!-- Indication & Sponsor Brief -->
        <div class="bg-slate-50 p-3 rounded-lg border border-slate-100 mb-4 space-y-1.5 text-xs">
          <div>
            <span class="font-semibold text-slate-700">Target Indication: </span>
            <span class="text-slate-600">${escapeHtml(trial.indication_en || trial.indication)}</span>
          </div>
          <div>
            <span class="font-semibold text-slate-700">Sponsor: </span>
            <span class="text-slate-600">${escapeHtml(trial.sponsor_en || trial.sponsor)}</span>
          </div>
        </div>

        <!-- Executive Summary Digest -->
        <div class="border-l-2 border-emerald-500 pl-3 py-1 mb-4">
          <div class="text-xs font-semibold uppercase tracking-wider text-emerald-800 mb-1 flex items-center space-x-1">
            <i data-lucide="file-check" class="w-3.5 h-3.5"></i>
            <span>Executive Digest</span>
          </div>
          ${formatMarkdownSummary(trial.executive_summary)}
        </div>
      </div>

      <!-- Action Button -->
      <div class="pt-3 border-t border-slate-100 flex items-center justify-between">
        <span class="text-xs text-slate-400">Date: ${trial.first_disclosure_date}</span>
        <button onclick="openModal('${trial.registration_id}')" 
                class="inline-flex items-center space-x-1 text-xs font-semibold text-emerald-600 hover:text-emerald-700 p-1.5 hover:bg-emerald-50 rounded transition">
          <span>Full Protocol & Details</span>
          <i data-lucide="arrow-right" class="w-3.5 h-3.5"></i>
        </button>
      </div>
    </div>
  `;
}

// -------------------------------------------------------------
// TAB 2: DATABASE & SEARCH EXPLORER
// -------------------------------------------------------------
function applyFilters() {
  const query = (document.getElementById("search-input").value || "").toLowerCase().trim();
  const phase = document.getElementById("phase-filter").value;
  const drugType = document.getElementById("type-filter").value;

  const filtered = allTrials.filter(t => {
    // Keyword match
    if (query) {
      const haystack = [
        t.registration_id,
        t.drug_name,
        t.drug_name_en,
        t.indication,
        t.indication_en,
        t.sponsor,
        t.sponsor_en,
        t.title_lay,
        t.lead_institution
      ].join(" ").toLowerCase();
      if (!haystack.includes(query)) return false;
    }

    // Phase match
    if (phase !== 'all') {
      if (!t.phase_en.includes(phase) && !t.phase.includes(phase)) return false;
    }

    // Category match
    if (drugType === 'new_drug' && !t.is_new_drug) return false;
    if (drugType === 'be' && t.is_new_drug) return false;

    return true;
  });

  renderDatabaseTable(filtered);
}

function resetFilters() {
  document.getElementById("search-input").value = "";
  document.getElementById("phase-filter").value = "all";
  document.getElementById("type-filter").value = "all";
  renderDatabaseTable(allTrials);
}

function renderDatabaseTable(trials) {
  const tbody = document.getElementById("database-table-body");
  const countEl = document.getElementById("filtered-count");
  const emptyState = document.getElementById("table-empty-state");

  countEl.innerText = trials.length;

  if (trials.length === 0) {
    tbody.innerHTML = "";
    emptyState.classList.remove("hidden");
    return;
  }

  emptyState.classList.add("hidden");

  tbody.innerHTML = trials.map(t => {
    const isNew = t.is_new_drug;
    const catBadge = isNew
      ? `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-800">New Drug</span>`
      : `<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-600">BE</span>`;

    return `
      <tr class="hover:bg-slate-50 transition border-b border-slate-100">
        <td class="px-4 py-3 whitespace-nowrap">
          <div class="font-mono font-bold text-xs text-slate-800">${t.registration_id}</div>
          <div class="text-[11px] text-slate-400">${t.first_disclosure_date}</div>
        </td>
        <td class="px-4 py-3 max-w-xs">
          <div class="font-semibold text-slate-900">${escapeHtml(t.drug_name_en || t.drug_name)}</div>
          <div class="text-xs text-slate-400 truncate">${escapeHtml(t.drug_name)}</div>
        </td>
        <td class="px-4 py-3 whitespace-nowrap">
          <div class="text-xs text-slate-700">${escapeHtml(t.drug_type_en || t.drug_type)}</div>
          <div class="mt-0.5">${catBadge}</div>
        </td>
        <td class="px-4 py-3 max-w-sm">
          <div class="text-xs text-slate-700 line-clamp-2">${escapeHtml(t.indication_en || t.indication)}</div>
        </td>
        <td class="px-4 py-3 max-w-xs whitespace-nowrap truncate text-xs text-slate-600">
          ${escapeHtml(t.sponsor_en || t.sponsor)}
        </td>
        <td class="px-4 py-3 whitespace-nowrap">
          <span class="px-2 py-0.5 text-xs rounded font-medium bg-slate-100 text-slate-700 border border-slate-200">
            ${escapeHtml((t.phase_en || t.phase).slice(0, 15))}
          </span>
        </td>
        <td class="px-4 py-3 whitespace-nowrap text-center">
          <button onclick="openModal('${t.registration_id}')" 
                  class="text-xs px-2.5 py-1 bg-slate-100 hover:bg-emerald-50 hover:text-emerald-700 text-slate-700 font-medium rounded border border-slate-200 transition">
            View
          </button>
        </td>
      </tr>
    `;
  }).join("");

  lucide.createIcons();
}

// -------------------------------------------------------------
// TAB 3: DAILY ARCHIVE
// -------------------------------------------------------------
function renderArchiveList() {
  const container = document.getElementById("archive-dates-list");
  const archives = summaryData.daily_archives || [];

  if (archives.length === 0) {
    container.innerHTML = `<p class="col-span-full text-xs text-slate-400">No archived dates yet.</p>`;
    return;
  }

  container.innerHTML = archives.map(date => {
    return `
      <button onclick="viewArchiveDate('${date}')" 
              class="archive-date-btn p-3 rounded-lg border border-slate-200 hover:border-emerald-500 hover:bg-emerald-50/50 text-left transition flex items-center justify-between bg-white">
        <div class="flex items-center space-x-2">
          <i data-lucide="calendar" class="w-4 h-4 text-emerald-600"></i>
          <span class="text-xs font-semibold text-slate-800">${date}</span>
        </div>
        <i data-lucide="chevron-right" class="w-3.5 h-3.5 text-slate-400"></i>
      </button>
    `;
  }).join("");

  lucide.createIcons();
}

function viewArchiveDate(date) {
  currentArchiveDate = date;
  const resultsContainer = document.getElementById("archive-results-container");
  
  const trials = allTrials.filter(t => t.first_disclosure_date === date);

  resultsContainer.innerHTML = `
    <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
      <div class="flex items-center justify-between border-b border-slate-100 pb-3">
        <h4 class="font-bold text-slate-900 text-sm flex items-center space-x-2">
          <i data-lucide="archive" class="w-4 h-4 text-emerald-600"></i>
          <span>Batch Archive: ${date} (${trials.length} trials)</span>
        </h4>
        <button onclick="document.getElementById('archive-results-container').innerHTML = ''" class="text-xs text-slate-400 hover:text-slate-600">Clear</button>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        ${trials.map(t => createTrialCard(t)).join("")}
      </div>
    </div>
  `;

  lucide.createIcons();
}

// -------------------------------------------------------------
// DETAIL MODAL LOGIC
// -------------------------------------------------------------
function openModal(regId) {
  const trial = allTrials.find(t => t.registration_id === regId);
  if (!trial) return;

  document.getElementById("modal-ctr-id").innerText = trial.registration_id;
  document.getElementById("modal-drug-name-en").innerText = trial.drug_name_en || trial.drug_name;
  document.getElementById("modal-drug-name-zh").innerText = trial.drug_name;
  document.getElementById("modal-study-title").innerText = trial.title_professional || trial.title_lay;

  document.getElementById("modal-indication").innerText = trial.indication_en || trial.indication;
  document.getElementById("modal-sponsor").innerText = trial.sponsor_en || trial.sponsor;
  document.getElementById("modal-date").innerText = trial.first_disclosure_date;
  document.getElementById("modal-status").innerText = trial.status_en || trial.status;

  document.getElementById("modal-sample-size").innerText = trial.target_sample_size || "30-100";
  document.getElementById("modal-institution").innerText = trial.lead_institution || "Leading Clinical Site";
  document.getElementById("modal-pi").innerText = trial.principal_investigator || "Clinical PI";
  document.getElementById("modal-endpoints").innerText = trial.primary_endpoints || "PK & Safety Endpoints";

  // Badges
  const typeBadge = document.getElementById("modal-badge-type");
  if (trial.is_new_drug) {
    typeBadge.className = "px-2.5 py-0.5 rounded text-xs font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30";
    typeBadge.innerText = "Innovative Drug";
  } else {
    typeBadge.className = "px-2.5 py-0.5 rounded text-xs font-semibold bg-slate-500/20 text-slate-300 border border-slate-500/30";
    typeBadge.innerText = "Generic BE";
  }

  document.getElementById("modal-badge-phase").innerText = (trial.phase_en || trial.phase).replace(/[\n\t]/g, ' ').slice(0, 15);

  // Executive Summary in modal
  document.getElementById("modal-executive-summary").innerHTML = formatMarkdownSummary(trial.executive_summary);

  // CDE Link
  document.getElementById("modal-cde-link").href = "https://www.chinadrugtrials.org.cn/clinicaltrials.searchlist.dhtml";

  // Show modal
  document.getElementById("trial-modal").classList.remove("hidden");
  lucide.createIcons();
}

function closeModal() {
  document.getElementById("trial-modal").classList.add("hidden");
}

// Close modal on Escape
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeModal();
});

// -------------------------------------------------------------
// EXPORT DATA
// -------------------------------------------------------------
function exportData(format) {
  if (format === 'json') {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(allTrials, null, 2));
    const dlAnchor = document.createElement('a');
    dlAnchor.setAttribute("href", dataStr);
    dlAnchor.setAttribute("download", `china_cde_trials_${new Date().toISOString().slice(0,10)}.json`);
    dlAnchor.click();
  } else if (format === 'csv') {
    if (allTrials.length === 0) return;
    const headers = ["registration_id", "first_disclosure_date", "drug_name", "drug_name_en", "is_new_drug", "phase_en", "indication", "indication_en", "sponsor", "sponsor_en"];
    const csvRows = [headers.join(",")];
    
    allTrials.forEach(t => {
      const row = headers.map(h => {
        let val = (t[h] !== undefined ? t[h] : "").toString();
        val = val.replace(/"/g, '""');
        return `"${val}"`;
      });
      csvRows.push(row.join(","));
    });

    const csvStr = "data:text/csv;charset=utf-8," + encodeURIComponent(csvRows.join("\n"));
    const dlAnchor = document.createElement('a');
    dlAnchor.setAttribute("href", csvStr);
    dlAnchor.setAttribute("download", `china_cde_trials_${new Date().toISOString().slice(0,10)}.csv`);
    dlAnchor.click();
  }
}

// Utility: HTML escape
function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
