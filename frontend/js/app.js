/**
 * Greenlight Simulator - Frontend Application Controller
 * Handles form synchronization, real-time predictions, OMDb auto-fill,
 * and Chart.js visualizations for both Simulator and Statistics sections.
 */

// Application State
const state = {
  options: {
    genres: [],
    directors: [],
    actors: [],
    companies: [],
    months: []
  },
  selectedCast: [],
  seasonalityChart: null,
  statsCharts: {},
  debounceTimer: null,
  lastOmdbData: null
};

document.addEventListener("DOMContentLoaded", () => {
  initNavigation();
  initSliderSync();
  initOmdbSearch();
  initCastSelector();
  loadOptions();
});

// ==================== 1. NAVIGATION ====================
function initNavigation() {
  const btnSimulator = document.getElementById("nav-simulator");
  const btnStatistics = document.getElementById("nav-statistics");
  const viewSimulator = document.getElementById("view-simulator");
  const viewStatistics = document.getElementById("view-statistics");

  btnSimulator.addEventListener("click", () => {
    btnSimulator.classList.add("active");
    btnStatistics.classList.remove("active");
    viewSimulator.classList.add("active");
    viewStatistics.classList.remove("active");
  });

  btnStatistics.addEventListener("click", () => {
    btnStatistics.classList.add("active");
    btnSimulator.classList.remove("active");
    viewStatistics.classList.add("active");
    viewSimulator.classList.remove("active");
    loadStatisticsOnce();
  });
}

// ==================== 2. SLIDER & INPUT SYNCHRONIZATION ====================
function initSliderSync() {
  const pairs = [
    { slider: "budget", input: "budget-input" },
    { slider: "runtime", input: "runtime-input" }
  ];

  pairs.forEach(({ slider, input }) => {
    const sEl = document.getElementById(slider);
    const iEl = document.getElementById(input);

    sEl.addEventListener("input", () => {
      iEl.value = sEl.value;
      triggerPredictionDebounced();
    });

    iEl.addEventListener("input", () => {
      sEl.value = iEl.value;
      triggerPredictionDebounced();
    });
  });

  // Regular input changes trigger prediction
  document.getElementById("month").addEventListener("change", triggerPredictionDebounced);
  document.getElementById("year").addEventListener("input", triggerPredictionDebounced);
  document.getElementById("release-location").addEventListener("change", triggerPredictionDebounced);
  document.getElementById("english").addEventListener("change", triggerPredictionDebounced);
  document.getElementById("sequel").addEventListener("change", triggerPredictionDebounced);
  document.getElementById("director").addEventListener("change", triggerPredictionDebounced);
  document.getElementById("company").addEventListener("change", triggerPredictionDebounced);
}

function triggerPredictionDebounced() {
  clearTimeout(state.debounceTimer);
  state.debounceTimer = setTimeout(() => {
    runPrediction();
  }, 120);
}

// ==================== 3. METADATA & OPTIONS ====================
async function loadOptions() {
  try {
    const res = await fetch("/api/options");
    if (!res.ok) throw new Error("Failed to load options");
    const data = await res.json();
    state.options = data;

    // 1. Populate Genres
    const genresContainer = document.getElementById("genres-container");
    genresContainer.innerHTML = "";
    data.genres.forEach(genre => {
      const chip = document.createElement("label");
      chip.className = "genre-chip" + (genre === "Action" ? " checked" : "");
      chip.innerHTML = `
        <input type="checkbox" name="genre" value="${genre}" ${genre === "Action" ? "checked" : ""}>
        <span>${genre}</span>
      `;
      chip.addEventListener("change", (e) => {
        if (e.target.checked) {
          chip.classList.add("checked");
        } else {
          chip.classList.remove("checked");
        }
        triggerPredictionDebounced();
      });
      genresContainer.appendChild(chip);
    });

    // 2. Populate Directors
    const dirSelect = document.getElementById("director");
    data.directors.forEach(name => {
      const opt = document.createElement("option");
      opt.value = name;
      opt.textContent = name;
      dirSelect.appendChild(opt);
    });

    // 3. Populate Actors in Cast Select
    populateActorDropdown(data.actors);

    // 4. Populate Companies
    const compSelect = document.getElementById("company");
    data.companies.forEach(name => {
      const opt = document.createElement("option");
      opt.value = name;
      opt.textContent = name;
      compSelect.appendChild(opt);
    });

    // Initial prediction run
    runPrediction();

  } catch (err) {
    console.error("Error loading options:", err);
  }
}

// ==================== 4. CAST SELECTION ====================
function initCastSelector() {
  const searchInput = document.getElementById("cast-search");
  const actorSelect = document.getElementById("cast-select");
  const addBtn = document.getElementById("add-actor-btn");

  searchInput.addEventListener("input", () => {
    const q = searchInput.value.toLowerCase().trim();
    const filtered = state.options.actors.filter(a => a.toLowerCase().includes(q));
    populateActorDropdown(filtered.slice(0, 100));
  });

  addBtn.addEventListener("click", () => {
    const val = actorSelect.value;
    if (val && !state.selectedCast.includes(val)) {
      if (state.selectedCast.length >= 3) {
        alert("You can select up to 3 lead actors.");
        return;
      }
      state.selectedCast.push(val);
      renderCastTags();
      triggerPredictionDebounced();
    }
  });
}

function populateActorDropdown(list) {
  const actorSelect = document.getElementById("cast-select");
  actorSelect.innerHTML = '<option value="">-- Choose actor to add --</option>';
  list.forEach(name => {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    actorSelect.appendChild(opt);
  });
}

function renderCastTags() {
  const container = document.getElementById("selected-cast-tags");
  container.innerHTML = "";
  if (state.selectedCast.length === 0) {
    container.innerHTML = '<span class="empty-tag-note">No actors selected yet.</span>';
    return;
  }
  state.selectedCast.forEach(name => {
    const tag = document.createElement("span");
    tag.className = "tag-badge";
    tag.innerHTML = `
      <span>${name}</span>
      <button type="button" class="tag-remove" title="Remove">&times;</button>
    `;
    tag.querySelector(".tag-remove").addEventListener("click", () => {
      state.selectedCast = state.selectedCast.filter(a => a !== name);
      renderCastTags();
      triggerPredictionDebounced();
    });
    container.appendChild(tag);
  });
}

// ==================== 5. PREDICTION LOGIC ====================
async function runPrediction() {
  const budget = parseFloat(document.getElementById("budget").value) * 1_000_000;
  const runtime = parseFloat(document.getElementById("runtime").value);
  const yearInput = document.getElementById("year").value;
  const year = parseInt(yearInput, 10) || 2024;
  const releaseLocation = document.getElementById("release-location").value;
  const month = parseInt(document.getElementById("month").value, 10);
  
  const checkedGenres = Array.from(document.querySelectorAll('#genres-container input[type="checkbox"]:checked'))
    .map(cb => cb.value);

  const english = document.getElementById("english").checked;
  const sequel = document.getElementById("sequel").checked;
  const director = document.getElementById("director").value;
  const company = document.getElementById("company").value;

  const payload = {
    budget,
    runtime,
    year,
    release_location: releaseLocation,
    month,
    genres: checkedGenres,
    english,
    sequel,
    director,
    cast: state.selectedCast,
    company
  };

  try {
    const res = await fetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error("Prediction API failed");
    const data = await res.json();
    renderPredictionResults(data);
  } catch (err) {
    console.error("Prediction error:", err);
  }
}

function renderPredictionResults(data) {
  const badge = document.getElementById("outcome-badge");
  const flopVal = document.getElementById("prob-flop-val");
  const modestVal = document.getElementById("prob-modest-val");
  const hitVal = document.getElementById("prob-hit-val");

  const flopBar = document.getElementById("prob-flop-bar");
  const modestBar = document.getElementById("prob-modest-bar");
  const hitBar = document.getElementById("prob-hit-bar");

  // Outcome Badge
  badge.textContent = data.most_likely;
  badge.className = "outcome-badge";
  if (data.most_likely_index === 0) badge.classList.add("flop");
  else if (data.most_likely_index === 1) badge.classList.add("modest");
  else if (data.most_likely_index === 2) badge.classList.add("hit");

  // Probabilities
  const pFlop = data.probabilities["Flop (<1x)"] || 0;
  const pModest = data.probabilities["Modest (1-3x)"] || 0;
  const pHit = data.probabilities["Hit (>=3x)"] || 0;

  flopVal.textContent = pFlop + "%";
  modestVal.textContent = pModest + "%";
  hitVal.textContent = pHit + "%";

  flopBar.style.width = pFlop + "%";
  modestBar.style.width = pModest + "%";
  hitBar.style.width = pHit + "%";

  // Seasonality Chart
  renderSeasonalityChart(data.seasonality);
}

function renderSeasonalityChart(seasonality) {
  const ctx = document.getElementById("seasonality-chart").getContext("2d");
  const labels = seasonality.map(s => s.month_name);
  const hitData = seasonality.map(s => s.hit_prob);

  if (state.seasonalityChart) {
    state.seasonalityChart.data.labels = labels;
    state.seasonalityChart.data.datasets[0].data = hitData;
    state.seasonalityChart.update();
    return;
  }

  state.seasonalityChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        label: "Chance of Hit (%)",
        data: hitData,
        borderColor: "#2563eb",
        backgroundColor: "rgba(37, 99, 235, 0.08)",
        borderWidth: 2.2,
        tension: 0.25,
        fill: true,
        pointBackgroundColor: "#2563eb",
        pointRadius: 3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => `Hit Probability: ${ctx.parsed.y}%`
          }
        }
      },
      scales: {
        y: {
          min: 0,
          max: 100,
          ticks: { callback: v => v + "%", font: { size: 10 } },
          grid: { color: "#f1f5f9" }
        },
        x: {
          ticks: { font: { size: 10 } },
          grid: { display: false }
        }
      }
    }
  });
}

// ==================== 6. OMDB MOVIE LOOKUP ====================
function initOmdbSearch() {
  const toggleBtn = document.getElementById("omdb-toggle-btn");
  const panel = document.getElementById("omdb-panel");
  const searchBtn = document.getElementById("omdb-search-btn");
  const applyBtn = document.getElementById("omdb-apply-btn");
  const statusEl = document.getElementById("omdb-status");
  const previewEl = document.getElementById("omdb-result");

  toggleBtn.addEventListener("click", () => {
    panel.classList.toggle("hidden");
  });

  searchBtn.addEventListener("click", async () => {
    const title = document.getElementById("omdb-title").value.trim();
    const year = document.getElementById("omdb-year").value.trim();
    if (!title) return;

    statusEl.className = "status-msg info";
    statusEl.textContent = "Searching movie database...";
    statusEl.classList.remove("hidden");
    previewEl.classList.add("hidden");

    try {
      const url = `/api/omdb?title=${encodeURIComponent(title)}${year ? `&year=${encodeURIComponent(year)}` : ""}`;
      const res = await fetch(url);
      const data = await res.json();

      if (data.Response === "True") {
        state.lastOmdbData = data;
        statusEl.classList.add("hidden");
        
        document.getElementById("omdb-result-title").textContent = `${data.Title} (${data.Year})`;
        document.getElementById("omdb-result-meta").textContent = `Rated: ${data.Rated} | Runtime: ${data.Runtime} | Released: ${data.Released}`;
        document.getElementById("omdb-result-plot").textContent = data.Plot || "";
        document.getElementById("omdb-result-credits").textContent = `Director: ${data.Director} | Cast: ${data.Actors} | Box Office: ${data.BoxOffice || 'N/A'}`;
        
        previewEl.classList.remove("hidden");
      } else {
        statusEl.className = "status-msg error";
        statusEl.textContent = data.Error || "Movie not found.";
      }
    } catch (err) {
      statusEl.className = "status-msg error";
      statusEl.textContent = "Error querying OMDb service: " + err.message;
    }
  });

  applyBtn.addEventListener("click", () => {
    if (!state.lastOmdbData) return;
    applyOmdbData(state.lastOmdbData);
    previewEl.classList.add("hidden");
    statusEl.className = "status-msg info";
    statusEl.textContent = "Movie details applied to form questions.";
    statusEl.classList.remove("hidden");
    setTimeout(() => statusEl.classList.add("hidden"), 3000);
  });
}

function applyOmdbData(info) {
  // Runtime
  const runtimeMatches = (info.Runtime || "").match(/\d+/);
  if (runtimeMatches) {
    const rt = Math.min(Math.max(parseInt(runtimeMatches[0], 10), 60), 210);
    document.getElementById("runtime").value = rt;
    document.getElementById("runtime-input").value = rt;
  }

  // Release Date -> Month & Year
  if (info.Released && info.Released !== "N/A") {
    const relDate = new Date(info.Released);
    if (!isNaN(relDate.getTime())) {
      const m = relDate.getMonth() + 1;
      document.getElementById("month").value = m.toString();
      const yr = relDate.getFullYear();
      document.getElementById("year").value = yr;
    }
  }

  // Genres
  const omdbGenres = (info.Genre || "").split(",").map(g => {
    const cleaned = g.trim();
    return cleaned === "Sci-Fi" ? "Science Fiction" : cleaned;
  });

  document.querySelectorAll('#genres-container input[type="checkbox"]').forEach(cb => {
    const match = omdbGenres.includes(cb.value);
    cb.checked = match;
    if (match) {
      cb.closest(".genre-chip").classList.add("checked");
    } else {
      cb.closest(".genre-chip").classList.remove("checked");
    }
  });

  // Language
  const isEnglish = (info.Language || "").includes("English");
  document.getElementById("english").checked = isEnglish;

  // Director
  if (info.Director) {
    const primaryDir = info.Director.split(",")[0].trim();
    const dirSelect = document.getElementById("director");
    const found = Array.from(dirSelect.options).some(o => o.value === primaryDir);
    if (found) {
      dirSelect.value = primaryDir;
    } else {
      dirSelect.value = "(unknown / new director)";
    }
  }

  // Cast
  if (info.Actors) {
    const rawActors = info.Actors.split(",").map(a => a.trim());
    state.selectedCast = [];
    rawActors.forEach(actor => {
      if (state.selectedCast.length < 3 && state.options.actors.includes(actor)) {
        state.selectedCast.push(actor);
      }
    });
    renderCastTags();
  }

  triggerPredictionDebounced();
}

// ==================== 7. STATISTICS SECTION ====================
let statsLoaded = false;
async function loadStatisticsOnce() {
  if (statsLoaded) return;

  try {
    const res = await fetch("/api/statistics");
    if (!res.ok) throw new Error("Failed to fetch statistics data");
    const data = await res.json();
    statsLoaded = true;

    // 1. Table: Highest-Earning Actors
    const tbody = document.querySelector("#table-actors tbody");
    tbody.innerHTML = "";
    (data.top_actors || []).forEach((a, idx) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>#${idx + 1}</strong></td>
        <td><strong>${a.actor}</strong></td>
        <td>$${a.total_revenue_billions}B</td>
        <td>$${a.avg_revenue_millions}M</td>
        <td>${a.movies_count}</td>
        <td>${a.hit_rate_pct}%</td>
      `;
      tbody.appendChild(tr);
    });

    // 2. Chart: Top Grossing Movies
    renderTopGrossingChart(data.top_grossing);

    // 3. Chart: Monthly Sales
    renderMonthlySalesChart(data.monthly_sales);

    // 4. Chart: Genre Sales
    renderGenreSalesChart(data.genre_sales);

    // 5. Chart: Leading Directors
    renderTopDirectorsChart(data.top_directors);

    // 6. Chart: Outcome Distributions
    renderOutcomeDistChart(data.outcome_distribution);

  } catch (err) {
    console.error("Error rendering statistics:", err);
  }
}

function renderTopGrossingChart(list) {
  const ctx = document.getElementById("chart-top-grossing").getContext("2d");
  const labels = list.map(m => m.title);
  const values = list.map(m => m.revenue_millions);

  new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [{
        label: "Worldwide Gross ($ Millions)",
        data: values,
        backgroundColor: "#2563eb",
        borderRadius: 4
      }]
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => `$${ctx.parsed.x.toLocaleString()} Million USD`
          }
        }
      },
      scales: {
        x: {
          title: { display: true, text: "Worldwide Revenue (USD Millions)", font: { size: 11 } },
          ticks: { font: { size: 10 } },
          grid: { color: "#f1f5f9" }
        },
        y: {
          ticks: { font: { size: 11, weight: "600" } },
          grid: { display: false }
        }
      }
    }
  });
}

function renderMonthlySalesChart(list) {
  const ctx = document.getElementById("chart-monthly-sales").getContext("2d");
  const labels = list.map(m => m.month_name);
  const totals = list.map(m => m.total_revenue_billions);

  new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [{
        label: "Total Sales ($ Billions)",
        data: totals,
        backgroundColor: labels.map(m => (m === "June" || m === "May" || m === "December") ? "#1d4ed8" : "#93c5fd"),
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => `$${ctx.parsed.y} Billion USD total industry gross`
          }
        }
      },
      scales: {
        y: {
          title: { display: true, text: "Cumulative Box Office ($ Billions)", font: { size: 11 } },
          ticks: { callback: v => "$" + v + "B", font: { size: 10 } },
          grid: { color: "#f1f5f9" }
        },
        x: {
          ticks: { font: { size: 11 } },
          grid: { display: false }
        }
      }
    }
  });
}

function renderGenreSalesChart(list) {
  const ctx = document.getElementById("chart-genre-sales").getContext("2d");
  const topGenres = list.slice(0, 10);
  const labels = topGenres.map(g => g.genre);
  const revenue = topGenres.map(g => g.total_revenue_billions);

  new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [{
        label: "Total Gross ($ Billions)",
        data: revenue,
        backgroundColor: "#0ea5e9",
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => `$${ctx.parsed.y} Billion total sales`
          }
        }
      },
      scales: {
        y: {
          title: { display: true, text: "Total Box Office ($ Billions)", font: { size: 11 } },
          ticks: { callback: v => "$" + v + "B", font: { size: 10 } },
          grid: { color: "#f1f5f9" }
        },
        x: {
          ticks: { font: { size: 10, weight: "500" } },
          grid: { display: false }
        }
      }
    }
  });
}

function renderTopDirectorsChart(list) {
  const ctx = document.getElementById("chart-top-directors").getContext("2d");
  const labels = list.map(d => d.director);
  const revenue = list.map(d => d.total_revenue_billions);

  new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [{
        label: "Cumulative Gross ($ Billions)",
        data: revenue,
        backgroundColor: "#6366f1",
        borderRadius: 4
      }]
    },
    options: {
      indexAxis: "y",
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const item = list[ctx.dataIndex];
              return `$${item.total_revenue_billions}B across ${item.movies_count} movies (${item.hit_rate_pct}% hit rate)`;
            }
          }
        }
      },
      scales: {
        x: {
          title: { display: true, text: "Cumulative Box Office ($ Billions)", font: { size: 11 } },
          ticks: { callback: v => "$" + v + "B", font: { size: 10 } },
          grid: { color: "#f1f5f9" }
        },
        y: {
          ticks: { font: { size: 11, weight: "600" } },
          grid: { display: false }
        }
      }
    }
  });
}

function renderOutcomeDistChart(dist) {
  const ctx = document.getElementById("chart-outcome-dist").getContext("2d");
  const labels = dist.map(d => d.name);
  const counts = dist.map(d => d.count);

  new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: labels,
      datasets: [{
        data: counts,
        backgroundColor: ["#dc2626", "#d97706", "#16a34a"],
        borderWidth: 2,
        borderColor: "#ffffff"
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
          labels: { font: { size: 11 }, boxWidth: 12 }
        },
        tooltip: {
          callbacks: {
            label: (ctx) => {
              const total = dist.reduce((acc, curr) => acc + curr.count, 0);
              const pct = ((ctx.parsed / total) * 100).toFixed(1);
              return `${ctx.label}: ${ctx.parsed.toLocaleString()} films (${pct}%)`;
            }
          }
        }
      },
      cutout: "62%"
    }
  });
}

