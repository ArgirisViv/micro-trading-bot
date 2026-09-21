"use strict";

const dashboard = {
  charts: {},
  backtest: [],
  walkforward: [],
  paperEquity: [],
  config: {},
  chartMode: "equity",
  range: "all",
  refreshing: false,
  csrf: null,
  runtime: {},
};

const $ = (id) => document.getElementById(id);
const number = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });
const integer = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const money = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const price = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 4 });

function setText(id, value) {
  const node = $(id);
  if (node) node.textContent = value;
}

function finite(value) {
  if (value === null || value === undefined || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatPercent(value, signed = false) {
  const parsed = finite(value);
  if (parsed === null) return "—";
  const prefix = signed && parsed > 0 ? "+" : "";
  return `${prefix}${number.format(parsed)}%`;
}

function formatDate(value, withTime = false) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  const options = withTime
    ? { dateStyle: "medium", timeStyle: "short" }
    : { month: "short", day: "numeric", year: "numeric" };
  return new Intl.DateTimeFormat("en-GB", options).format(date);
}

function formatMonth(value) {
  const date = new Date(`${value}-01T00:00:00Z`);
  return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("en", { month: "short", year: "2-digit", timeZone: "UTC" }).format(date);
}

function metricTone(id, value) {
  const node = $(id);
  if (!node) return;
  node.classList.remove("positive", "negative");
  const parsed = finite(value);
  if (parsed > 0) node.classList.add("positive");
  if (parsed < 0) node.classList.add("negative");
}

async function requestJson(path) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch(path, { headers: { Accept: "application/json" }, signal: controller.signal });
    if (response.status === 401) showAuth();
    if (!response.ok) throw new Error(`${path} returned ${response.status}`);
    return await response.json();
  } finally {
    window.clearTimeout(timer);
  }
}

async function postJson(path, payload, authenticated = true) {
  const headers = { "Content-Type": "application/json", "X-Requested-With": "Orbit" };
  if (authenticated) headers["X-Orbit-CSRF"] = dashboard.csrf;
  const response = await fetch(path, { method: "POST", headers, body: JSON.stringify(payload) });
  if (response.status === 401 && authenticated) showAuth();
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}

function showAuth(message = "") {
  dashboard.csrf = null;
  $("auth-screen").hidden = false;
  setText("login-error", message);
  $("login-password").focus();
}

function hideAuth(csrf) {
  dashboard.csrf = csrf;
  $("login-password").value = "";
  $("auth-screen").hidden = true;
}

async function checkAuth() {
  try {
    const status = await requestJson("/api/auth/status");
    if (!status.configured) return showAuth("Configure dashboard credentials in .env.local first.");
    if (!status.authenticated) return showAuth();
    hideAuth(status.csrf);
    await refreshDashboard();
  } catch (_) { showAuth("Cannot reach the dashboard server."); }
}

function renderControl(value = {}) {
  const locked = dashboard.runtime.execution_uncertain === true;
  const staged = dashboard.runtime.paper_entries_approved === false;
  const paused = value.paused !== false || locked || staged;
  const indicator = $("control-indicator");
  indicator.textContent = paused ? "PAUSED" : "ALLOWED";
  indicator.className = `control-indicator ${paused ? "paused" : "active"}`;
  setText("control-message", paused
    ? "New entries are paused. Existing positions can still be monitored and exited by the running bot."
    : "New entries are allowed when the bot is running and all risk checks pass.");
  setText("control-updated", value.updated_at ? `Last change: ${formatDate(value.updated_at, true)}` : "Default safety state · Resume manually to allow entries");
  if (locked || staged) setText("control-message", locked
    ? "Execution locked: an order outcome is unconfirmed. Broker reconciliation is required; do not clear runtime state."
    : "Hardening stage: new entries are locked pending execution validation. Dashboard monitoring remains available.");
  $("pause-button").disabled = paused;
  $("resume-button").disabled = !paused || locked || staged;
}

function showToast(message) {
  const toast = $("toast");
  toast.textContent = message;
  toast.classList.add("visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove("visible"), 3200);
}

function heartbeatCopy(runtime) {
  const seconds = finite(runtime?.heartbeat_age_seconds);
  if (seconds === null) return "No recent heartbeat";
  if (seconds < 60) return `${integer.format(seconds)}s ago`;
  if (seconds < 3600) return `${integer.format(seconds / 60)}m ago`;
  return `${integer.format(seconds / 3600)}h ago`;
}

function updateStatus(runtime = {}) {
  dashboard.runtime = runtime;
  const status = ["online", "offline", "halted", "paused"].includes(runtime.status) ? runtime.status : "offline";
  const label = status === "online" ? "System online" : status === "halted" ? "Trading halted" : status === "paused" ? "Entries paused" : "System offline";
  [$("sidebar-status-dot"), $("header-status-orb")].forEach((node) => {
    node.classList.remove("online", "offline", "halted");
    node.classList.add(status);
  });
  setText("sidebar-status", label);
  setText("header-status", label);
  setText("sidebar-heartbeat", heartbeatCopy(runtime));
  setText("runtime-heartbeat", runtime.last_heartbeat ? heartbeatCopy(runtime) : "Not received");
  const badge = $("runtime-badge");
  badge.classList.remove("online", "offline", "halted");
  badge.classList.add(status);
  badge.textContent = status.toUpperCase();
}

function sourceLabel(source) {
  const labels = {
    "live-percent-pnl": ["PAPER TRADES", "Paper close events with calculated percentage P&L"],
    "live-dollar-pnl": ["PAPER TRADES", "Paper close events with recorded P&L"],
    "paper-ledger-gross-usd": ["PAPER FILLS · GROSS", "Completed owned trades from broker fills; fees not reconciled"],
    "backtest-trades": ["BACKTEST", "Position-level backtest trades"],
  };
  return labels[source] || ["NO DATA", "Requires completed trades with P&L"];
}

function updateTradeQuality(stats = {}) {
  const available = Boolean(stats.available);
  const rate = available ? finite(stats.win_rate_pct) : null;
  const [badge, description] = sourceLabel(stats.source);
  setText("trade-source-badge", badge);
  setText("win-rate-source", description);
  setText("metric-win-rate", formatPercent(rate));
  setText("gauge-win-rate", formatPercent(rate));
  setText("trade-wins", String(stats.wins || 0));
  setText("trade-losses", String(stats.losses || 0));
  setText("trade-flat", String(stats.breakeven || 0));
  const factor = finite(stats.profit_factor);
  setText("metric-profit-factor", factor === null ? "—" : number.format(factor));
  const streak = Number(stats.current_streak || 0);
  setText("trade-streak", streak ? `${streak} ${stats.current_streak_type === "win" ? "wins" : "losses"}` : "—");
  const circumference = 289.03;
  const clamped = Math.max(0, Math.min(100, rate || 0));
  $("win-gauge").setAttribute("stroke-dashoffset", String(circumference * (1 - clamped / 100)));
}

function updateOverview(data) {
  updateStatus(data.runtime || {});
  const backtest = data.backtest || {};
  const walkforward = data.walkforward || {};
  const performance = data.performance || {};
  const activity = data.activity || {};
  const totalReturn = finite(backtest.total_return_pct);
  setText("metric-return", formatPercent(totalReturn, true));
  metricTone("metric-return", totalReturn);
  setText("metric-drawdown", formatPercent(backtest.max_drawdown_pct));
  metricTone("metric-drawdown", backtest.max_drawdown_pct);
  const accountEquity = finite(activity.account_equity);
  const dailyPnl = finite(activity.daily_pnl);
  setText("metric-growth", accountEquity === null ? "—" : money.format(accountEquity));
  metricTone("metric-growth", dailyPnl);
  setText("equity-daily-pnl", dailyPnl === null ? "Awaiting account state" : `${dailyPnl >= 0 ? "+" : ""}${money.format(dailyPnl)} today (${formatPercent(activity.daily_pnl_pct, true)})`);
  setText("backtest-range", backtest.start ? `${formatDate(backtest.start)} — ${formatDate(backtest.end)}` : "Awaiting backtest history");
  setText("wf-sharpe", finite(walkforward.avg_sharpe) === null ? "—" : number.format(walkforward.avg_sharpe));
  setText("wf-win-rate", formatPercent(walkforward.avg_win_rate_pct));
  setText("wf-cagr", formatPercent(walkforward.avg_cagr_pct, true));
  setText("wf-drawdown", formatPercent(walkforward.avg_max_drawdown_pct));
  setText("wf-periods", walkforward.periods == null ? "—" : String(walkforward.periods));
  setText("positive-periods", walkforward.periods ? `${walkforward.positive_periods || 0} / ${walkforward.periods} positive periods` : "No validation periods");
  setText("metric-positions", `${activity.open_positions || 0} / ${dashboard.config.max_portfolio_positions ?? "—"}`);
  setText("daily-orders", `${activity.daily_order_count || 0} / ${dashboard.config.max_daily_orders ?? "—"}`);
  setText("pending-orders", String(activity.open_orders_count || 0));
  setText("account-cash", finite(activity.account_cash) === null ? "—" : money.format(activity.account_cash));
  updateTradeQuality(performance.trades || {});
  renderMonths(performance.monthly_returns || []);
}

function chartTheme() {
  const css = getComputedStyle(document.documentElement);
  return {
    text: css.getPropertyValue("--muted").trim(),
    grid: css.getPropertyValue("--line").trim(),
    green: css.getPropertyValue("--green").trim(),
    blue: css.getPropertyValue("--blue").trim(),
    red: css.getPropertyValue("--red").trim(),
    violet: css.getPropertyValue("--violet").trim(),
  };
}

function destroyChart(name) {
  if (dashboard.charts[name]) dashboard.charts[name].destroy();
  dashboard.charts[name] = null;
}

function renderPaperChart() {
  destroyChart("paper");
  const rows = dashboard.paperEquity;
  const empty = $("paper-chart-empty");
  setText("paper-points", rows.length ? `${integer.format(rows.length)} broker snapshots` : "No snapshots");
  if (!rows.length || !window.Chart) {
    empty.classList.add("visible");
    if (!window.Chart) empty.querySelector("strong").textContent = "Chart library unavailable";
    return;
  }
  empty.classList.remove("visible");
  const theme = chartTheme();
  dashboard.charts.paper = new window.Chart($("paper-chart"), {
    type: "line",
    data: {
      labels: rows.map((row) => formatDate(row.timestamp, true)),
      datasets: [{ label: "Paper account equity", data: rows.map((row) => finite(row.equity)),
        borderColor: theme.blue, backgroundColor: `${theme.blue}18`, fill: true,
        borderWidth: 2, pointRadius: 0, tension: .18, spanGaps: false }],
    },
    options: { responsive: true, maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: (item) => `Paper equity: ${price.format(item.parsed.y)}` } } },
      scales: { x: { ticks: { color: theme.text, maxTicksLimit: 7 }, grid: { display: false } },
        y: { ticks: { color: theme.text, callback: (value) => money.format(value) }, grid: { color: theme.grid } } } },
  });
}

function filteredBacktest() {
  if (dashboard.range === "all" || !dashboard.backtest.length) return dashboard.backtest;
  const last = new Date(dashboard.backtest.at(-1).timestamp);
  const cutoff = new Date(last);
  cutoff.setUTCDate(cutoff.getUTCDate() - Number(dashboard.range));
  return dashboard.backtest.filter((row) => new Date(row.timestamp) >= cutoff);
}

function renderMainChart() {
  destroyChart("equity");
  const rows = filteredBacktest();
  const empty = $("equity-empty");
  setText("chart-points", `${integer.format(rows.length)} observations`);
  $("benchmark-legend").hidden = dashboard.chartMode === "drawdown";
  if (!window.Chart || !rows.length) {
    empty.classList.add("visible");
    if (!window.Chart) empty.querySelector("strong").textContent = "Chart library unavailable";
    return;
  }
  empty.classList.remove("visible");
  const theme = chartTheme();
  const canvas = $("equity-chart");
  const gradient = canvas.getContext("2d").createLinearGradient(0, 0, 0, 360);
  gradient.addColorStop(0, `${theme.green}35`);
  gradient.addColorStop(1, `${theme.green}00`);
  const isDrawdown = dashboard.chartMode === "drawdown";
  const datasets = isDrawdown
    ? [{ label: "Drawdown", data: rows.map((row) => finite(row.drawdown_pct) || 0), borderColor: theme.red, backgroundColor: `${theme.red}18`, fill: true, borderWidth: 1.8, pointRadius: 0, tension: .18 }]
    : [
        { label: "Strategy", data: rows.map((row) => ((finite(row.equity) || 1) - 1) * 100), borderColor: theme.green, backgroundColor: gradient, fill: true, borderWidth: 2.1, pointRadius: 0, tension: .22 },
        { label: "Market", data: rows.map((row) => ((finite(row.benchmark) || 1) - 1) * 100), borderColor: theme.blue, borderWidth: 1.3, borderDash: [5, 5], pointRadius: 0, tension: .2 },
      ];
  dashboard.charts.equity = new window.Chart(canvas, {
    type: "line",
    data: { labels: rows.map((row) => row.timestamp), datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 550 },
      interaction: { intersect: false, mode: "index" },
      plugins: {
        legend: { display: false },
        tooltip: {
          displayColors: true,
          callbacks: {
            title: (items) => formatDate(items[0]?.label),
            label: (item) => `${item.dataset.label}: ${formatPercent(item.raw, true)}`,
          },
        },
      },
      scales: {
        x: { grid: { display: false }, border: { display: false }, ticks: { color: theme.text, maxTicksLimit: 7, callback: (_, index) => formatDate(rows[index]?.timestamp), font: { size: 11 } } },
        y: { grid: { color: theme.grid }, border: { display: false }, ticks: { color: theme.text, callback: (value) => `${value}%`, font: { size: 11 } } },
      },
    },
  });
}

function renderWalkforward() {
  destroyChart("walkforward");
  const rows = dashboard.walkforward;
  const empty = $("walkforward-empty");
  if (!window.Chart || !rows.length) {
    empty.classList.add("visible");
    if (!window.Chart) empty.querySelector("strong").textContent = "Chart library unavailable";
    return;
  }
  empty.classList.remove("visible");
  const theme = chartTheme();
  dashboard.charts.walkforward = new window.Chart($("walkforward-chart"), {
    type: "bar",
    data: {
      labels: rows.map((row) => row.TestStart),
      datasets: [{ data: rows.map((row) => finite(row.Sharpe) || 0), backgroundColor: rows.map((row) => (finite(row.Sharpe) || 0) >= 0 ? `${theme.violet}bb` : `${theme.red}bb`), borderRadius: 4, maxBarThickness: 34 }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { title: (items) => `Test ${formatDate(items[0]?.label)}`, label: (item) => `Sharpe: ${number.format(item.raw)}` } } },
      scales: {
        x: { grid: { display: false }, border: { display: false }, ticks: { color: theme.text, maxTicksLimit: 9, callback: (_, index) => formatDate(rows[index]?.TestStart), font: { size: 11 } } },
        y: { grid: { color: theme.grid }, border: { display: false }, ticks: { color: theme.text, font: { size: 11 } } },
      },
    },
  });
}

function renderMonths(rows) {
  const grid = $("monthly-grid");
  grid.replaceChildren();
  if (!Array.isArray(rows) || !rows.length) {
    const empty = document.createElement("div");
    empty.className = "empty-inline";
    empty.textContent = "No monthly history available.";
    grid.append(empty);
    return;
  }
  rows.forEach((row) => {
    const value = finite(row.return_pct) || 0;
    const intensity = Math.min(5, Math.max(1, Math.ceil(Math.abs(value) / 2)));
    const cell = document.createElement("div");
    cell.className = `month-cell ${value >= 0 ? "positive" : "negative"} heat-${intensity}`;
    const month = document.createElement("span"); month.textContent = formatMonth(row.month);
    const result = document.createElement("strong"); result.textContent = formatPercent(value, true);
    cell.append(month, result); grid.append(cell);
  });
}

function renderPositions(payload) {
  const positions = Array.isArray(payload.positions) ? payload.positions : [];
  const container = $("positions-list");
  setText("position-count", String(positions.length));
  container.replaceChildren();
  if (!positions.length) {
    container.className = "empty-state";
    const icon = document.createElement("span"); icon.className = "empty-icon"; icon.textContent = "◇";
    const title = document.createElement("strong"); title.textContent = "Portfolio is flat";
    const copy = document.createElement("small"); copy.textContent = "Confirmed entries will appear here automatically.";
    container.append(icon, title, copy);
    return;
  }
  container.className = "positions-list";
  positions.forEach((position) => {
    const row = document.createElement("div"); row.className = "position-row";
    const symbolWrap = document.createElement("div"); symbolWrap.className = "position-symbol";
    const avatar = document.createElement("span"); avatar.className = "symbol-avatar"; avatar.textContent = String(position.symbol).slice(0, 2);
    const symbol = document.createElement("strong"); symbol.textContent = position.symbol;
    symbolWrap.append(avatar, symbol);
    const entry = document.createElement("span"); entry.className = "position-price"; entry.textContent = price.format(Number(position.entry_price));
    const entryLabel = document.createElement("small"); entryLabel.textContent = position.ownership === "ledger"
      ? (position.broker_quantity_verified ? "Owned fills · quantity matched" : "Owned fills · quantity UNVERIFIED")
      : "Legacy cached entry · ownership unverified";
    const trailing = document.createElement("small"); trailing.textContent = position.trailing_high == null ? "Trailing high unavailable" : `Trailing high ${price.format(Number(position.trailing_high))}`;
    row.append(symbolWrap, entry, entryLabel, trailing); container.append(row);
  });
}

function firstValue(row, keys) {
  for (const key of keys) if (row[key] !== undefined && row[key] !== null && row[key] !== "") return row[key];
  return "—";
}

function renderTrades(rows) {
  const trades = Array.isArray(rows) ? [...rows].reverse().slice(0, 40) : [];
  const tbody = $("trades-body"); tbody.replaceChildren();
  setText("trade-count", String(Array.isArray(rows) ? rows.length : 0));
  if (!trades.length) {
    const tr = document.createElement("tr"); const td = document.createElement("td");
    td.colSpan = 6; td.className = "empty-cell"; td.textContent = "No order submissions recorded."; tr.append(td); tbody.append(tr); return;
  }
  trades.forEach((trade) => {
    const values = [
      formatDate(firstValue(trade, ["timestamp", "time", "date", "created_at"]), true),
      String(firstValue(trade, ["side", "action", "signal"])),
      String(firstValue(trade, ["symbol", "ticker"])),
      firstValue(trade, ["price", "fill_price", "close"]),
      firstValue(trade, ["qty", "quantity", "size"]),
      String(firstValue(trade, ["source", "reason", "strategy"])),
    ];
    const tr = document.createElement("tr");
    values.forEach((value, index) => {
      const td = document.createElement("td");
      if (index === 1) {
        const tag = document.createElement("span");
        tag.className = `side-tag${String(value).toLowerCase().includes("sell") ? " sell" : ""}`;
        tag.textContent = value; td.append(tag);
      } else if (index === 3 && finite(value) !== null) td.textContent = price.format(Number(value));
      else td.textContent = String(value);
      tr.append(td);
    });
    tbody.append(tr);
  });
}

function renderExecution(value = {}) {
  setText("execution-status", !value.available ? "NOT INITIALIZED" : value.blocked ? "REVIEW REQUIRED" : "JOURNALED");
  const pending = value.pending_entries || 0;
  const faults = (value.faults || []).length + (value.read_errors || []).length + (value.position_mismatches || []).length;
  setText("execution-summary", !value.available ? value.reason :
    `${value.fill_checkpoints || 0} broker fill checkpoints · ${pending} pending entries · ${faults} reconciliation issues · ${value.closed_trades?.length || 0} completed owned trades. Gross P&L only; fees are not reconciled. Last poll: ${formatDate(value.reconciled_at, true)}.`);
  const external = (value.external_positions || []).map(row => `${row.symbol} (${row.qty})`).join(", ");
  setText("execution-external", !value.available || value.positions_unavailable
    ? "External positions: account snapshot unavailable; ownership must not be assumed."
    : external ? `External / not managed: ${external}` : "No external positions in the last available account snapshot. This is not an adoption policy.");
  const tbody = $("execution-body"); tbody.replaceChildren();
  const rows = (value.orders || []).slice(-60).reverse();
  if (!rows.length) {
    const tr = document.createElement("tr"); const td = document.createElement("td");
    td.colSpan = 7; td.className = "empty-cell"; td.textContent = "No ledger orders.";
    tr.append(td); tbody.append(tr); return;
  }
  rows.forEach(row => {
    const tr = document.createElement("tr");
    [row.symbol, row.side, row.status, row.requested_qty, row.filled_qty,
      row.avg_price == null ? "—" : price.format(Number(row.avg_price)),
      row.intent_key?.startsWith("exit|") ? "Software crypto exit" : row.parent_id ? "Linked bracket exit" : "Local entry intent"].forEach(value => {
        const td = document.createElement("td"); td.textContent = String(value ?? "—"); tr.append(td);
      });
    tbody.append(tr);
  });
}

function configCard(icon, title, pairs) {
  const card = document.createElement("article"); card.className = "config-card";
  const head = document.createElement("div"); head.className = "config-card-head";
  const iconNode = document.createElement("span"); iconNode.className = "config-icon"; iconNode.textContent = icon;
  const heading = document.createElement("h3"); heading.textContent = title;
  head.append(iconNode, heading);
  const list = document.createElement("dl");
  pairs.forEach(([label, value]) => {
    const row = document.createElement("div"); const dt = document.createElement("dt"); const dd = document.createElement("dd");
    dt.textContent = label; dd.textContent = String(value ?? "—"); row.append(dt, dd); list.append(row);
  });
  card.append(head, list); return card;
}

function renderConfig(config) {
  dashboard.config = config || {};
  const grid = $("config-grid"); grid.replaceChildren();
  grid.append(
    configCard("UN", "Trading universe", [["Primary symbol", config.symbol], ["Timeframe", config.timeframe], ["Asset classes", (config.asset_classes || []).join(", ")], ["Stocks", (config.stock_watchlist || []).join(", ")], ["Crypto", (config.crypto_watchlist || []).join(", ")]]),
    configCard("RK", "Risk limits", [["Risk per trade", formatPercent(Number(config.risk_per_trade) * 100)], ["Stop loss", formatPercent(Number(config.stop_loss_pct) * 100)], ["Take profit", formatPercent(Number(config.take_profit_pct) * 100)], ["Trailing stop", formatPercent(Number(config.trailing_stop_pct) * 100)], ["Daily drawdown halt", formatPercent(Number(config.max_daily_drawdown_pct) * 100)]]),
    configCard("EX", "Execution policy", [["Environment", config.paper_trading ? "Paper trading" : "Verify endpoint"], ["Position limit", config.max_portfolio_positions], ["Daily order limit", config.max_daily_orders], ["Market hours only", config.market_hours_only ? "Enabled" : "Disabled"], ["Dashboard access", "Authenticated entry control"]])
  );
}

async function refreshDashboard() {
  if (dashboard.refreshing) return;
  dashboard.refreshing = true;
  $("refresh-button").classList.add("loading");
  try {
    const [config, overview, backtest, walkforward, runtime, trades, control, paperEquity, execution, cryptoExits] = await Promise.all([
      requestJson("/api/config"), requestJson("/api/overview"), requestJson("/api/backtest"), requestJson("/api/walkforward"), requestJson("/api/state"), requestJson("/api/trades"), requestJson("/api/control"), requestJson("/api/paper-equity"),
      requestJson("/api/execution"),
      requestJson("/api/crypto-exits"),
    ]);
    renderConfig(config);
    dashboard.backtest = Array.isArray(backtest) ? backtest : [];
    dashboard.walkforward = Array.isArray(walkforward) ? walkforward : [];
    dashboard.paperEquity = Array.isArray(paperEquity) ? paperEquity : [];
    updateOverview(overview);
    renderPositions(runtime);
    renderTrades(trades);
    renderExecution(execution);
    setText("crypto-exit-status", !cryptoExits.available ? "Crypto exit supervisor: disabled / not initialized."
      : `Crypto exit supervisor: ${cryptoExits.fresh ? "recent poll" : "STALE"} · ${(cryptoExits.issues || []).length} issues. Software exits are not broker-side protection.`);
    renderControl(control);
    renderMainChart();
    renderPaperChart();
    renderWalkforward();
    setText("last-updated", new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(new Date()));
  } catch (error) {
    updateStatus({ status: "offline" });
    showToast(error.name === "AbortError" ? "Dashboard request timed out." : "Could not refresh dashboard data.");
  } finally {
    dashboard.refreshing = false;
    $("refresh-button").classList.remove("loading");
  }
}

function setupControls() {
  $("login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    $("login-button").disabled = true;
    setText("login-error", "");
    try {
      const result = await postJson("/api/auth/login", { password: $("login-password").value }, false);
      hideAuth(result.csrf);
      await refreshDashboard();
    } catch (error) { setText("login-error", error.message); }
    finally { $("login-button").disabled = false; }
  });
  $("logout-button").addEventListener("click", async () => {
    try { await postJson("/api/auth/logout", {}); } catch (_) { /* session expires automatically */ }
    showAuth();
  });
  for (const [id, action] of [["pause-button", "pause"], ["resume-button", "resume"]]) {
    $(id).addEventListener("click", async () => {
      $("pause-button").disabled = $("resume-button").disabled = true;
      try {
        const control = await postJson("/api/control", { action });
        renderControl(control);
        await refreshDashboard();
        showToast(action === "pause" ? "New entries paused." : "New entries allowed when risk checks pass.");
      } catch (error) { showToast(error.message); await refreshDashboard(); }
    });
  }
  document.querySelectorAll("[data-chart-mode]").forEach((button) => button.addEventListener("click", () => {
    dashboard.chartMode = button.dataset.chartMode;
    document.querySelectorAll("[data-chart-mode]").forEach((item) => item.classList.toggle("active", item === button));
    renderMainChart();
  }));
  document.querySelectorAll("[data-range]").forEach((button) => button.addEventListener("click", () => {
    dashboard.range = button.dataset.range;
    document.querySelectorAll("[data-range]").forEach((item) => item.classList.toggle("active", item === button));
    renderMainChart();
  }));
  const closeMenu = () => {
    document.body.classList.remove("menu-open");
    $("menu-button").setAttribute("aria-expanded", "false");
  };
  $("menu-button").addEventListener("click", () => {
    const open = document.body.classList.toggle("menu-open");
    $("menu-button").setAttribute("aria-expanded", String(open));
  });
  $("mobile-overlay").addEventListener("click", closeMenu);
  document.querySelectorAll(".nav-item").forEach((link) => link.addEventListener("click", closeMenu));
  $("refresh-button").addEventListener("click", refreshDashboard);
}

function setupTheme() {
  const saved = localStorage.getItem("orbit-theme");
  if (saved === "light" || saved === "dark") document.documentElement.dataset.theme = saved;
  $("theme-button").addEventListener("click", () => {
    const theme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("orbit-theme", theme);
    renderMainChart(); renderPaperChart(); renderWalkforward();
  });
}

function setupNavigation() {
  const observer = new IntersectionObserver((entries) => {
    entries.filter((entry) => entry.isIntersecting).forEach((entry) => {
      document.querySelectorAll(".nav-item").forEach((link) => link.classList.toggle("active", link.dataset.section === entry.target.id));
    });
  }, { rootMargin: "-18% 0px -70%", threshold: 0 });
  document.querySelectorAll("main section[id]").forEach((section) => observer.observe(section));
}

function updateClock() {
  setText("utc-clock", new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false, timeZone: "UTC" }).format(new Date()));
}

document.addEventListener("DOMContentLoaded", () => {
  setupControls(); setupTheme(); setupNavigation(); updateClock(); checkAuth();
  window.setInterval(updateClock, 1000);
  window.setInterval(() => { if (dashboard.csrf) refreshDashboard(); }, 60000);
});
