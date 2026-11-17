// China CDE New Drug Clinical Trials Intelligence Portal

let allTrials = [];
let summaryData = {};
let currentTab = 'today';
let selectedTodayPhases = new Set(); // Multi-choice for Today's Briefing
let selectedPhases = new Set();      // Multi-choice for Database & Search Explorer
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
    dateDisplay.innerText = `Disclosed: ${latestDate} (${todayTrials.length} new drugs registered)`;
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
  // Tabs initialized via HTML onclick
}

// -------------------------------------------------------------
// TAB 1: TODAY'S EXECUTIVE BRIEFING (Multi-Choice Phase Support)
// -------------------------------------------------------------
function filterTodayPhase(phase) {
  if (phase === 'all') {
    selectedTodayPhases.clear();
  } else {
    if (selectedTodayPhases.has(phase)) {
      selectedTodayPhases.delete(phase);
    } else {
      selectedTodayPhases.add(phase);
    }
  }

  const isAll = selectedTodayPhases.size === 0;
  document.querySelectorAll(".today-phase-btn").forEach(btn => {
    const p = btn.dataset.phase;
    if (p === 'all') {
      btn.className = isAll 
        ? "today-phase-btn px-3 py-1 text-xs font-semibold rounded-full bg-slate-900 text-white shadow-sm"
        : "today-phase-btn px-3 py-1 text-xs font-medium rounded-full bg-white text-slate-700 hover:bg-slate-100 border border-slate-200";
    } else {
      if (selectedTodayPhases.has(p)) {
        btn.className = "today-phase-btn px-3 py-1 text-xs font-semibold rounded-full bg-emerald-600 text-white shadow-sm border border-emerald-600";
      } else {
        btn.className = "today-phase-btn px-3 py-1 text-xs font-medium rounded-full bg-white text-slate-700 hover:bg-slate-100 border border-slate-200";
      }
    }
  });

  renderTodayBriefing();
}

function renderTodayBriefing() {
  const container = document.getElementById("today-cards-container");
  const latestDate = summaryData.latest_disclosure_date || (allTrials[0] ? allTrials[0].first_disclosure_date : '');
  
  let trials = allTrials.filter(t => t.first_disclosure_date === latestDate);
  if (trials.length === 0) {
    trials = allTrials.slice(0, 10);
  }

  if (selectedTodayPhases.size > 0) {
    trials = trials.filter(t => {
      return Array.from(selectedTodayPhases).some(p => {
        if (p === 'Phase I') return t.phase_en.includes('Phase I') || t.phase.includes('I期');
        if (p === 'Phase II') return t.phase_en.includes('Phase II') || t.phase.includes('II期');
        if (p === 'Phase III') return t.phase_en.includes('Phase III') || t.phase_en.includes('Phase IV') || t.phase.includes('III期') || t.phase.includes('IV期');
        return t.phase_en.includes(p) || t.phase.includes(p);
      });
    });
  }

  if (trials.length === 0) {
    container.innerHTML = `
      <div class="col-span-full py-12 text-center text-slate-400 bg-white rounded-xl border border-slate-200">
        No new drug trials found matching the selected phase choices.
      </div>`;
    return;
  }

  container.innerHTML = trials.map(trial => createTrialCard(trial)).join("");
  lucide.createIcons();
}

function formatMarkdownSummary(text) {
  if (!text) return "";
  const lines = text.split("\n\n");
  return lines.map(line => {
    line = line.replace(/^\*\*(.*?)\*\*:/g, '<strong class="text-slate-900">$1:</strong>');
    line = line.replace(/^\*\*(.*?)\*\*/g, '<strong class="text-slate-900">$1</strong>');
    return `<div class="mb-2 text-xs text-slate-600 leading-relaxed">${line}</div>`;
  }).join("");
}

function createTrialCard(trial) {
  let phaseBadgeColor = "bg-emerald-100 text-emerald-800 border-emerald-200";
  if (trial.phase_en.includes("Phase III") || trial.phase_en.includes("Phase IV")) {
    phaseBadgeColor = "bg-purple-100 text-purple-800 border-purple-200";
  } else if (trial.phase_en.includes("Phase II")) {
    phaseBadgeColor = "bg-indigo-100 text-indigo-800 border-indigo-200";
  }

  const overseasBadge = trial.overseas_intent ? `
    <span class="px-2 py-0.5 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 flex items-center space-x-1" title="Confirmed overseas clinical signal (US site on ClinicalTrials.gov or Dual filing)">
      <i data-lucide="globe" class="w-3 h-3 text-blue-600"></i>
      <span>Global / US Site</span>
    </span>
  ` : '';

  return `
    <div class="trial-card bg-white rounded-xl border border-slate-200 p-6 flex flex-col justify-between shadow-sm hover:border-emerald-400">
      <div>
        <!-- Badges and Registration ID -->
        <div class="flex items-center justify-between mb-3 gap-2">
          <div class="flex items-center flex-wrap gap-1.5">
            <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold border ${phaseBadgeColor} flex items-center space-x-1">
              <span class="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
              <span>${escapeHtml(trial.phase_en.replace(/[\n\t]/g, ' ').slice(0, 20))}</span>
            </span>
            <span class="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-600 font-medium border border-slate-200">
              ${escapeHtml(trial.drug_type_en || "Innovative Candidate")}
            </span>
            ${overseasBadge}
          </div>
          <span class="text-xs font-mono font-bold text-slate-400">${trial.registration_id}</span>
        </div>

        <!-- Drug Title -->
        <h3 class="text-base font-bold text-slate-900 leading-snug mb-1">
          ${escapeHtml(trial.drug_name_en || trial.drug_name)}
        </h3>
        ${trial.drug_name !== trial.drug_name_en ? `<p class="text-xs text-slate-400 mb-3">${escapeHtml(trial.drug_name)}</p>` : '<div class="mb-3"></div>'}

        <!-- Highlighted Target Indication in English -->
        <div class="bg-emerald-50/60 p-3.5 rounded-xl border border-emerald-100 mb-4 space-y-1.5">
          <div class="text-xs">
            <span class="font-bold text-emerald-900 uppercase tracking-wide text-[11px] block mb-0.5">Target Indication (English):</span>
            <span class="text-slate-900 font-semibold text-sm leading-snug">${escapeHtml(trial.indication_en || trial.indication)}</span>
          </div>
          <div class="text-xs pt-1 border-t border-emerald-100/60 flex items-center justify-between">
            <span class="text-slate-600"><span class="font-medium text-slate-700">Sponsor: </span>${escapeHtml(trial.sponsor_en || trial.sponsor)}</span>
            <span class="text-[11px] text-slate-400 font-mono">${trial.first_disclosure_date}</span>
          </div>
        </div>

        <!-- Executive Summary Digest -->
        <div class="border-l-2 border-emerald-500 pl-3 py-1 mb-4">
          <div class="text-xs font-semibold uppercase tracking-wider text-emerald-800 mb-1.5 flex items-center space-x-1">
            <i data-lucide="file-check" class="w-3.5 h-3.5"></i>
            <span>Executive Briefing</span>
          </div>
          ${formatMarkdownSummary(trial.executive_summary)}
        </div>
      </div>

      <!-- Action Button -->
      <div class="pt-3 border-t border-slate-100 flex items-center justify-between">
        <span class="text-xs text-slate-400">Cohort: ~${trial.target_sample_size || '30-100'}</span>
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
// TAB 2: DATABASE & SEARCH EXPLORER (Multi-Choice Phase Support)
// -------------------------------------------------------------
function togglePhase(phase) {
  if (phase === 'all') {
    selectedPhases.clear();
  } else {
    if (selectedPhases.has(phase)) {
      selectedPhases.delete(phase);
    } else {
      selectedPhases.add(phase);
    }
  }
  updatePhaseChipsUI();
  applyFilters();
}

function selectAllPhases() {
  selectedPhases.clear();
  updatePhaseChipsUI();
  applyFilters();
}

function updatePhaseChipsUI() {
  const isAll = selectedPhases.size === 0;

  const allChip = document.getElementById("phase-chip-all");
  if (allChip) {
    if (isAll) {
      allChip.className = "phase-filter-chip px-3 py-1.5 text-xs font-semibold rounded-lg bg-slate-900 text-white shadow-sm border border-slate-900 transition flex items-center space-x-1";
    } else {
      allChip.className = "phase-filter-chip px-3 py-1.5 text-xs font-medium rounded-lg bg-white text-slate-700 hover:bg-slate-50 border border-slate-200 transition flex items-center space-x-1";
    }
  }

  const phaseConfig = [
    { id: "Phase I", activeClass: "bg-emerald-600 text-white border-emerald-600 font-semibold shadow-sm" },
    { id: "Phase II", activeClass: "bg-indigo-600 text-white border-indigo-600 font-semibold shadow-sm" },
    { id: "Phase III", activeClass: "bg-purple-600 text-white border-purple-600 font-semibold shadow-sm" },
    { id: "Phase IV", activeClass: "bg-fuchsia-600 text-white border-fuchsia-600 font-semibold shadow-sm" }
  ];

  phaseConfig.forEach(p => {
    const chip = document.getElementById(`phase-chip-${p.id}`);
    if (chip) {
      if (selectedPhases.has(p.id)) {
        chip.className = `phase-filter-chip px-3 py-1.5 text-xs rounded-lg transition flex items-center space-x-1.5 border ${p.activeClass}`;
        chip.innerHTML = `<i data-lucide="check" class="w-3.5 h-3.5"></i><span>${p.id}</span>`;
      } else {
        chip.className = "phase-filter-chip px-3 py-1.5 text-xs font-medium rounded-lg bg-white text-slate-700 hover:bg-slate-50 border border-slate-200 transition flex items-center space-x-1.5";
        chip.innerHTML = `<span>${p.id}</span>`;
      }
    }
  });

  if (window.lucide) lucide.createIcons();
}

function applyFilters() {
  const query = (document.getElementById("search-input").value || "").toLowerCase().trim();
  const overseasOnly = document.getElementById("overseas-filter") ? document.getElementById("overseas-filter").checked : false;

  const filtered = allTrials.filter(t => {
    if (overseasOnly && !t.overseas_intent) return false;

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

    // Multi-choice Phase Filter
    if (selectedPhases.size > 0) {
      const match = Array.from(selectedPhases).some(p => {
        if (p === 'Phase I') return t.phase_en.includes('Phase I') || t.phase.includes('I期') || t.phase.includes('1期');
        if (p === 'Phase II') return t.phase_en.includes('Phase II') || t.phase.includes('II期') || t.phase.includes('2期');
        if (p === 'Phase III') return t.phase_en.includes('Phase III') || t.phase.includes('III期') || t.phase.includes('3期');
        if (p === 'Phase IV') return t.phase_en.includes('Phase IV') || t.phase.includes('IV期') || t.phase.includes('4期');
        return t.phase_en.includes(p) || t.phase.includes(p);
      });
      if (!match) return false;
    }

    return true;
  });

  renderDatabaseTable(filtered);
}

function resetFilters() {
  document.getElementById("search-input").value = "";
  selectedPhases.clear();
  updatePhaseChipsUI();
  const overseasToggle = document.getElementById("overseas-filter");
  if (overseasToggle) overseasToggle.checked = false;
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
    let phaseBadgeColor = "bg-emerald-50 text-emerald-800 border-emerald-200";
    if (t.phase_en.includes("Phase III") || t.phase_en.includes("Phase IV")) {
      phaseBadgeColor = "bg-purple-50 text-purple-800 border-purple-200";
    } else if (t.phase_en.includes("Phase II")) {
      phaseBadgeColor = "bg-indigo-50 text-indigo-800 border-indigo-200";
    }

    return `
      <tr class="hover:bg-slate-50 transition border-b border-slate-100">
        <td class="px-4 py-3 whitespace-nowrap">
          <div class="font-mono font-bold text-xs text-slate-800">${t.registration_id}</div>
          <div class="text-[11px] text-slate-400">${t.first_disclosure_date}</div>
        </td>
        <td class="px-4 py-3 max-w-xs">
          <div class="font-semibold text-slate-900">${escapeHtml(t.drug_name_en || t.drug_name)}</div>
          <div class="text-[11px] text-slate-400 truncate">${escapeHtml(t.drug_type_en || t.drug_type)}</div>
        </td>
        <td class="px-4 py-3 max-w-sm">
          <div class="text-xs font-semibold text-slate-900 line-clamp-2">${escapeHtml(t.indication_en || t.indication)}</div>
          ${t.indication !== t.indication_en ? `<div class="text-[11px] text-slate-400 truncate">${escapeHtml(t.indication)}</div>` : ''}
        </td>
        <td class="px-4 py-3 max-w-xs text-xs text-slate-700">
          <div class="font-medium truncate">${escapeHtml(t.sponsor_en || t.sponsor)}</div>
          ${t.overseas_intent ? `
            <div class="mt-1">
              <span class="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200" title="Confirmed overseas signal: US site on ClinicalTrials.gov">
                <i data-lucide="globe" class="w-2.5 h-2.5 text-blue-600"></i>
                <span>Overseas Intent (US Site)</span>
              </span>
            </div>
          ` : ''}
        </td>
        <td class="px-4 py-3 whitespace-nowrap">
          <span class="px-2.5 py-0.5 text-xs rounded-full font-medium ${phaseBadgeColor} border">
            ${escapeHtml((t.phase_en || t.phase).slice(0, 15))}
          </span>
        </td>
        <td class="px-4 py-3 whitespace-nowrap text-center">
          <button onclick="openModal('${t.registration_id}')" 
                  class="text-xs px-2.5 py-1 bg-slate-100 hover:bg-emerald-50 hover:text-emerald-700 text-slate-700 font-medium rounded border border-slate-200 transition">
            View Protocol
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
          <span>Batch Archive: ${date} (${trials.length} new drugs)</span>
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
  document.getElementById("modal-institution").innerText = trial.lead_institution || "Leading Clinical Research Hospital";
  document.getElementById("modal-pi").innerText = trial.principal_investigator || "Principal Investigator";
  document.getElementById("modal-endpoints").innerText = trial.primary_endpoints || "PK, Safety & Tolerability";

  document.getElementById("modal-badge-phase").innerText = (trial.phase_en || trial.phase).replace(/[\n\t]/g, ' ').slice(0, 15);

  document.getElementById("modal-executive-summary").innerHTML = formatMarkdownSummary(trial.executive_summary);
  document.getElementById("modal-cde-link").href = "https://www.chinadrugtrials.org.cn/clinicaltrials.searchlist.dhtml";

  // Populate Overseas Intent & BD Outreach container
  const overseasEl = document.getElementById("modal-overseas-container");
  if (overseasEl) {
    if (trial.overseas_intent) {
      const signalsList = (trial.overseas_signals || []).map(s => {
        if (s === 'us_site') {
          return '<li class="flex items-center space-x-1.5"><i data-lucide="check-circle-2" class="w-3.5 h-3.5 text-blue-600 flex-shrink-0"></i><span><strong class="text-slate-900">US Clinical Site:</strong> Sponsor has confirmed clinical trial(s) in the United States registered on ClinicalTrials.gov (API v2).</span></li>';
        }
        if (s === 'dual_filing') {
          return '<li class="flex items-center space-x-1.5"><i data-lucide="check-circle-2" class="w-3.5 h-3.5 text-blue-600 flex-shrink-0"></i><span><strong class="text-slate-900">Dual FDA+CDE Filing:</strong> Phase II/III innovative new drug with international trial registration identifier.</span></li>';
        }
        return `<li>${s}</li>`;
      }).join("");

      overseasEl.className = "p-3.5 rounded-xl border bg-blue-50/70 border-blue-200 text-xs text-blue-900 mb-3 space-y-1.5";
      overseasEl.innerHTML = `
        <div class="flex items-center justify-between">
          <div class="flex items-center space-x-1.5 font-bold text-blue-900 text-xs uppercase tracking-wide">
            <i data-lucide="globe" class="w-3.5 h-3.5 text-blue-600"></i>
            <span>Overseas Intent Confirmed (BD Outreach Target)</span>
          </div>
          <span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-blue-600 text-white">Global Track</span>
        </div>
        <ul class="space-y-1 text-slate-700 mt-1">${signalsList}</ul>
      `;
    } else {
      overseasEl.className = "p-2.5 rounded-xl border bg-slate-50 border-slate-200 text-xs text-slate-500 mb-3 flex items-center space-x-1.5";
      overseasEl.innerHTML = `
        <i data-lucide="info" class="w-3.5 h-3.5 text-slate-400"></i>
        <span>No active overseas clinical sites or dual filings currently detected for this sponsor.</span>
      `;
    }
  }

  document.getElementById("trial-modal").classList.remove("hidden");
  lucide.createIcons();
}

function closeModal() {
  document.getElementById("trial-modal").classList.add("hidden");
}

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
    dlAnchor.setAttribute("download", `china_cde_new_drugs_${new Date().toISOString().slice(0,10)}.json`);
    dlAnchor.click();
  } else if (format === 'csv') {
    if (allTrials.length === 0) return;
    const headers = ["registration_id", "first_disclosure_date", "drug_name", "drug_name_en", "phase_en", "indication_en", "sponsor_en", "overseas_intent", "overseas_signals"];
    const csvRows = [headers.join(",")];
    
    allTrials.forEach(t => {
      const row = headers.map(h => {
        let val = "";
        if (h === 'overseas_signals') {
          val = (t[h] || []).join("; ");
        } else {
          val = (t[h] !== undefined ? t[h] : "").toString();
        }
        val = val.replace(/"/g, '""');
        return `"${val}"`;
      });
      csvRows.push(row.join(","));
    });

    const csvStr = "data:text/csv;charset=utf-8," + encodeURIComponent(csvRows.join("\n"));
    const dlAnchor = document.createElement('a');
    dlAnchor.setAttribute("href", csvStr);
    dlAnchor.setAttribute("download", `china_cde_new_drugs_${new Date().toISOString().slice(0,10)}.csv`);
    dlAnchor.click();
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
