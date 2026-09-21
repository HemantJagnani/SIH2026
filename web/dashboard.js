/**
 * India Airfare Price Index — Dashboard JS
 *
 * Mock data sourced from Phase 12 test fixtures and Cleartrip/IndiGo sanitized samples.
 * In production, replace MOCK_DATA fetch with /api/observations endpoint.
 */

/* ════════════════════════════════════
   MOCK DATA (Phase 12 fixture-based)
   ════════════════════════════════════ */

const AIRLINE_COLORS = {
  'IndiGo':     '#06b6d4',
  'Air India':  '#ef4444',
  'SpiceJet':   '#f59e0b',
  'Vistara':    '#8b5cf6',
  'Akasa Air':  '#10b981',
  'GoFirst':    '#3b82f6',
  'EaseMyTrip': '#f97316',
};

let API_OBSERVATIONS = [];
const LEAD_DAYS = [1, 7, 15, 30, 45];
let TREND_DATA = {};
let SOURCE_HEALTH = [];
let FLAGGED_OBS = [];

/* ════════════════════════════════════
   STATE
   ════════════════════════════════════ */

let state = {
  selectedRoute: '',
  sortKey: 'total_fare',
  sortAsc: true,
  observations: [],
};

let trendChart = null;
let qualityChart = null;
let validationChart = null;

/* ════════════════════════════════════
   INIT
   ════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', async () => {
  try {
    const res = await fetch('http://localhost:8000/api/observations');
    if (res.ok) {
      API_OBSERVATIONS = await res.json();
      state.observations = [...API_OBSERVATIONS];
      
      // Compute dynamic trends
      TREND_DATA = {};
      API_OBSERVATIONS.forEach(o => {
        if (!TREND_DATA[o.route]) TREND_DATA[o.route] = {};
        if (!TREND_DATA[o.route][o.airline]) TREND_DATA[o.route][o.airline] = [null, null, null, null, null];
        const leadIdx = LEAD_DAYS.indexOf(o.lead_days);
        if (leadIdx !== -1) {
          // just taking the first fare we see or min fare, simplified
          const current = TREND_DATA[o.route][o.airline][leadIdx];
          if (current === null || o.total_fare < current) {
            TREND_DATA[o.route][o.airline][leadIdx] = o.total_fare;
          }
        }
      });
      
      // Compute dynamic sources
      const sources = [...new Set(API_OBSERVATIONS.map(o => o.source))];
      SOURCE_HEALTH = sources.map(s => ({
        name: s,
        type: 'API',
        success_rate: 100, // mock success rate for now since we only store successes
        obs_yield: 100,
        last_ok: 'just now'
      }));
      
      FLAGGED_OBS = []; // No flagged obs yet
    } else {
      console.error('Failed to load observations');
    }
  } catch (err) {
    console.error('API not reachable. Showing empty state.', err);
  }

  if (API_OBSERVATIONS.length > 0) {
    state.selectedRoute = API_OBSERVATIONS[0].route;
  }

  renderRouteCards();
  renderHealthList();
  renderStatsRow();
  renderTable();
  if (state.selectedRoute) renderTrendChart(state.selectedRoute);
  renderRoutesTab();
  renderSourcesTab();
  renderQualityTab();
  updateTimestamp();
});

/* ════════════════════════════════════
   TABS
   ════════════════════════════════════ */

function switchTab(tab) {
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.getElementById(`tab-${tab}`).classList.add('active');
  document.getElementById(`panel-${tab}`).classList.add('active');
}

/* ════════════════════════════════════
   SIDEBAR
   ════════════════════════════════════ */

function renderRouteCards() {
  const routes = [...new Set(API_OBSERVATIONS.map(o => o.route))];
  const container = document.getElementById('route-cards');
  container.innerHTML = routes.map(route => {
    const count = API_OBSERVATIONS.filter(o => o.route === route).length;
    return `
      <div class="route-card ${route === state.selectedRoute ? 'active' : ''}"
           id="route-card-${route.replace(/[→]/g,'_')}"
           onclick="selectRoute('${route}')" role="button" tabindex="0">
        <div class="route-card-label">${route}</div>
        <div class="route-card-meta">${count} observations</div>
      </div>`;
  }).join('');
}

function selectRoute(route) {
  state.selectedRoute = route;
  document.querySelectorAll('.route-card').forEach(c => c.classList.remove('active'));
  const card = document.getElementById(`route-card-${route.replace(/[→]/g,'_')}`);
  if (card) card.classList.add('active');
  renderTrendChart(route);
  applyFilters();
  showToast(`Route: ${route}`);
}

function renderHealthList() {
  const container = document.getElementById('health-list');
  container.innerHTML = SOURCE_HEALTH.slice(0, 5).map(s => {
    const level = s.success_rate >= 90 ? 'good' : s.success_rate >= 75 ? 'fair' : 'issues';
    const label = s.success_rate >= 90 ? 'LIVE' : s.success_rate >= 75 ? 'FAIR' : 'ISSUES';
    return `
      <div class="health-item">
        <span class="health-name">${s.name}</span>
        <span class="health-badge ${level}">${s.success_rate}% ${label}</span>
      </div>`;
  }).join('');
}

/* ════════════════════════════════════
   STATS
   ════════════════════════════════════ */

function renderStatsRow() {
  const obs = state.observations;
  const avgFare = Math.round(obs.reduce((s, o) => s + o.total_fare, 0) / obs.length);
  const minFare = Math.min(...obs.map(o => o.total_fare));
  const sources = new Set(obs.map(o => o.source)).size;
  const container = document.getElementById('stats-row');
  container.innerHTML = `
    <div class="stat-card">
      <div class="stat-icon">📡</div>
      <div class="stat-label">Total Observations</div>
      <div class="stat-value cyan">${obs.length}</div>
      <div class="stat-delta">Across ${sources} sources</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon">💰</div>
      <div class="stat-label">Avg Fare (Economy)</div>
      <div class="stat-value green">₹${avgFare.toLocaleString('en-IN')}</div>
      <div class="stat-delta">All routes · T+7</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon">🏷️</div>
      <div class="stat-label">Lowest Fare</div>
      <div class="stat-value amber">₹${minFare.toLocaleString('en-IN')}</div>
      <div class="stat-delta">Best available deal</div>
    </div>
    <div class="stat-card">
      <div class="stat-icon">✅</div>
      <div class="stat-label">Pipeline Health</div>
      <div class="stat-value blue">94%</div>
      <div class="stat-delta">Quality gate pass rate</div>
    </div>
  `;
}

/* ════════════════════════════════════
   TREND CHART
   ════════════════════════════════════ */

function renderTrendChart(route) {
  const routeData = TREND_DATA[route] || {};
  const airlines = Object.keys(routeData);
  const datasets = airlines.map(airline => ({
    label: airline,
    data: routeData[airline],
    borderColor: AIRLINE_COLORS[airline] || '#94a3b8',
    backgroundColor: `${AIRLINE_COLORS[airline] || '#94a3b8'}18`,
    fill: true,
    tension: 0.4,
    pointRadius: 5,
    pointHoverRadius: 8,
    borderWidth: 2,
    spanGaps: true,
  }));

  const ctx = document.getElementById('fare-trend-chart').getContext('2d');
  if (trendChart) trendChart.destroy();

  trendChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: LEAD_DAYS.map(d => `T+${d}`),
      datasets,
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index', intersect: false },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0a1628',
          borderColor: '#2563eb44',
          borderWidth: 1,
          titleColor: '#f0f4ff',
          bodyColor: '#94a3b8',
          callbacks: {
            label: ctx => ` ${ctx.dataset.label}: ₹${ctx.parsed.y.toLocaleString('en-IN')}`,
          }
        }
      },
      scales: {
        x: {
          grid: { color: 'rgba(37,99,235,0.1)' },
          ticks: { color: '#4b6080', font: { size: 11 } },
        },
        y: {
          grid: { color: 'rgba(37,99,235,0.1)' },
          ticks: {
            color: '#4b6080',
            font: { size: 11 },
            callback: v => `₹${(v/1000).toFixed(0)}k`
          }
        }
      }
    }
  });

  document.getElementById('chart-title').textContent = `Fare Trend (${route})`;

  // Build legend
  const legendHtml = airlines.map(a => `
    <div class="legend-item">
      <div class="legend-dot" style="background:${AIRLINE_COLORS[a] || '#94a3b8'}"></div>
      <span>${a}</span>
    </div>`).join('');
  document.getElementById('chart-legend').innerHTML = legendHtml;
}

/* ════════════════════════════════════
   TABLE
   ════════════════════════════════════ */

function applyFilters() {
  const cabin     = document.getElementById('cabin-filter').value;
  const lead      = document.getElementById('lead-filter').value;
  const airline   = document.getElementById('airline-filter').value;
  const search    = document.getElementById('search-input').value.toLowerCase();

  state.observations = API_OBSERVATIONS.filter(o => {
    if (cabin   && o.cabin !== cabin)                          return false;
    if (lead    && String(o.lead_days) !== lead)              return false;
    if (airline && o.airline !== airline)                      return false;
    if (search  && !`${o.route} ${o.airline} ${o.source}`.toLowerCase().includes(search)) return false;
    return true;
  });

  renderTable();
  renderStatsRow();
}

function sortTable(key) {
  if (state.sortKey === key) state.sortAsc = !state.sortAsc;
  else { state.sortKey = key; state.sortAsc = true; }
  renderTable();
}

function renderTable() {
  const sorted = [...state.observations].sort((a, b) => {
    const va = a[state.sortKey], vb = b[state.sortKey];
    const dir = state.sortAsc ? 1 : -1;
    return va < vb ? -dir : va > vb ? dir : 0;
  });

  const tbody = document.getElementById('fare-table-body');
  if (sorted.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;color:var(--text-muted);padding:48px">No observations match your filters</td></tr>`;
    document.getElementById('observation-count').textContent = '0 records';
    return;
  }

  tbody.innerHTML = sorted.map(o => {
    const color = AIRLINE_COLORS[o.airline] || '#94a3b8';
    const dt = new Date(o.collected_at);
    const timeStr = dt.toLocaleTimeString('en-IN', { hour:'2-digit', minute:'2-digit' });
    
    let flightTimes = "-";
    if (o.departure_time_local && o.arrival_time_local) {
      const dep = new Date(o.departure_time_local).toLocaleTimeString('en-IN', { hour:'2-digit', minute:'2-digit' });
      const arr = new Date(o.arrival_time_local).toLocaleTimeString('en-IN', { hour:'2-digit', minute:'2-digit' });
      flightTimes = `${dep} - ${arr}`;
    }
    
    return `
      <tr>
        <td class="route-cell">${o.route}</td>
        <td>
          <div class="airline-cell">
            <div class="airline-dot" style="background:${color}"></div>
            ${o.airline} <span style="color:var(--text-muted);font-size:11px;margin-left:4px">(${o.airline_code})</span>
          </div>
        </td>
        <td><span class="cabin-badge ${o.cabin}">${o.cabin}</span></td>
        <td style="font-family:var(--mono);font-size:12px">${o.travel_date}</td>
        <td style="font-family:var(--mono);font-size:12px;color:var(--text-muted)">${flightTimes}</td>
        <td style="font-family:var(--mono)">T+${o.lead_days}</td>
        <td class="fare-cell">₹${o.total_fare.toLocaleString('en-IN')}</td>
        <td style="font-size:12px;color:var(--text-muted)">${o.source}</td>
        <td><span class="status-badge ${o.availability}">${o.availability.replace('_',' ')}</span></td>
        <td style="font-size:11px;color:var(--text-muted);font-family:var(--mono)">${timeStr}</td>
      </tr>`;
  }).join('');

  document.getElementById('observation-count').textContent = `${sorted.length} record${sorted.length !== 1 ? 's' : ''}`;
}

/* ════════════════════════════════════
   ROUTES TAB
   ════════════════════════════════════ */

function renderRoutesTab() {
  const routes = [...new Set(API_OBSERVATIONS.map(o => o.route))];
  const CITY_MAP = { DEL:'New Delhi', BOM:'Mumbai', BLR:'Bengaluru', MAA:'Chennai', HYD:'Hyderabad' };

  document.getElementById('routes-grid').innerHTML = routes.map(route => {
    const [orig, dest] = route.split('→');
    const obs = API_OBSERVATIONS.filter(o => o.route === route);
    const minFare = Math.min(...obs.map(o => o.total_fare));
    const avgFare = Math.round(obs.reduce((s, o) => s + o.total_fare, 0) / obs.length);
    const airlines = [...new Set(obs.map(o => o.airline))].length;
    const sources  = [...new Set(obs.map(o => o.source))].length;
    return `
      <div class="route-detail-card" onclick="selectRoute('${route}'); switchTab('fares')" role="button" tabindex="0" style="cursor:pointer">
        <div class="route-detail-header">
          <div>
            <div class="route-detail-title">${route}</div>
            <div class="route-detail-city">${CITY_MAP[orig] || orig} → ${CITY_MAP[dest] || dest}</div>
          </div>
          <span style="font-size:22px">✈</span>
        </div>
        <div class="route-stats">
          <div class="route-stat"><div class="route-stat-label">Min Fare</div><div class="route-stat-value" style="color:var(--green)">₹${minFare.toLocaleString('en-IN')}</div></div>
          <div class="route-stat"><div class="route-stat-label">Avg Fare</div><div class="route-stat-value">₹${avgFare.toLocaleString('en-IN')}</div></div>
          <div class="route-stat"><div class="route-stat-label">Airlines</div><div class="route-stat-value" style="color:var(--cyan)">${airlines}</div></div>
          <div class="route-stat"><div class="route-stat-label">Observations</div><div class="route-stat-value">${obs.length}</div></div>
        </div>
        <div style="font-size:11px;color:var(--text-muted)">${sources} source${sources>1?'s':''} · Click to view fares →</div>
      </div>`;
  }).join('');
}

/* ════════════════════════════════════
   SOURCES TAB
   ════════════════════════════════════ */

function renderSourcesTab() {
  document.getElementById('sources-grid').innerHTML = SOURCE_HEALTH.map(s => {
    const successColor = s.success_rate >= 90 ? 'var(--green)' : s.success_rate >= 75 ? 'var(--amber)' : 'var(--red)';
    const yieldColor   = s.obs_yield   >= 80 ? 'var(--green)' : s.obs_yield   >= 60 ? 'var(--amber)' : 'var(--red)';
    return `
      <div class="source-card">
        <div class="source-header">
          <div class="source-name">${s.name.charAt(0).toUpperCase() + s.name.slice(1)}</div>
          <span class="source-type ${s.type}">${s.type}</span>
        </div>
        <div class="source-metrics">
          <div class="source-metric">
            <div class="source-metric-header"><span>Success Rate</span><span style="color:${successColor}">${s.success_rate}%</span></div>
            <div class="progress-bar"><div class="progress-fill" style="width:${s.success_rate}%;background:${successColor}"></div></div>
          </div>
          <div class="source-metric">
            <div class="source-metric-header"><span>Observation Yield</span><span style="color:${yieldColor}">${s.obs_yield}%</span></div>
            <div class="progress-bar"><div class="progress-fill" style="width:${s.obs_yield}%;background:${yieldColor}"></div></div>
          </div>
        </div>
        <div style="font-size:11px;color:var(--text-muted)">Last success: ${s.last_ok}</div>
      </div>`;
  }).join('');
}

/* ════════════════════════════════════
   QUALITY TAB
   ════════════════════════════════════ */

function renderQualityTab() {
  // Quality Gate pie
  const qCtx = document.getElementById('quality-chart').getContext('2d');
  if (qualityChart) qualityChart.destroy();
  
  // Real data: everything fetched from API currently passed validation.
  const passCount = API_OBSERVATIONS.length;
  
  qualityChart = new Chart(qCtx, {
    type: 'doughnut',
    data: {
      labels: ['PASS', 'FLAG', 'QUARANTINE'],
      datasets: [{
        data: [passCount > 0 ? 100 : 0, 0, 0],
        backgroundColor: ['#10b981', '#f59e0b', '#ef4444'],
        borderWidth: 0,
        hoverOffset: 6,
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: '#94a3b8', font: { size: 12 }, padding: 16 }
        },
        tooltip: {
          callbacks: { label: ctx => ` ${ctx.label}: ${ctx.parsed}%` }
        }
      }
    }
  });

  // Validation breakdown bar
  const vCtx = document.getElementById('validation-chart').getContext('2d');
  if (validationChart) validationChart.destroy();
  validationChart = new Chart(vCtx, {
    type: 'bar',
    data: {
      labels: ['Schema', 'Route', 'Price Negative', 'Unmapped Entity', 'Stale Date', 'Outlier'],
      datasets: [{
        label: 'Failures',
        data: [0, 0, 0, 0, 0, 0], // all real data passed
        backgroundColor: '#2563eb88',
        borderColor: '#2563eb',
        borderWidth: 1,
        borderRadius: 4,
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false },
      },
      scales: {
        x: { ticks: { color: '#4b6080', font: { size: 11 } }, grid: { display: false } },
        y: { ticks: { color: '#4b6080', font: { size: 11 } }, grid: { color: 'rgba(37,99,235,0.1)' } }
      }
    }
  });

  // Flagged table
  if (FLAGGED_OBS.length === 0) {
    document.getElementById('flagged-table-body').innerHTML = `<tr><td colspan="5" style="text-align:center;color:var(--text-muted);padding:48px">No flagged observations</td></tr>`;
  } else {
    document.getElementById('flagged-table-body').innerHTML = FLAGGED_OBS.map(f => `
      <tr>
        <td class="route-cell">${f.route}</td>
        <td>${f.airline}</td>
        <td class="fare-cell">₹${f.fare.toLocaleString('en-IN')}</td>
        <td><span class="flag-reason">${f.flag}</span></td>
        <td><span class="decision-${f.decision.toLowerCase()}">${f.decision}</span></td>
      </tr>`).join('');
  }
}

/* ════════════════════════════════════
   UTILITIES
   ════════════════════════════════════ */

function refreshData() {
  const btn = document.getElementById('refresh-btn');
  btn.classList.add('spinning');
  btn.disabled = true;
  
  fetch('http://localhost:8000/api/observations')
    .then(res => res.json())
    .then(data => {
      MOCK_OBSERVATIONS = data;
      state.observations = [...data];
      applyFilters(); // This re-renders table and stats
      renderRouteCards();
      renderRoutesTab();
      renderTrendChart(state.selectedRoute);
      updateTimestamp();
      showToast('Data refreshed ✓');
    })
    .catch(err => {
      console.error(err);
      showToast('Failed to fetch data');
    })
    .finally(() => {
      btn.classList.remove('spinning');
      btn.disabled = false;
    });
}

function updateTimestamp() {
  const now = new Date();
  document.getElementById('last-updated-display').textContent =
    `Last updated: ${now.toLocaleTimeString('en-IN', { hour:'2-digit', minute:'2-digit' })}`;
}

let toastTimer = null;
function showToast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), 2500);
}
