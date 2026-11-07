/* Watchlist board: mini candlestick charts at the top of Market, chosen with ☆ in the
   price board. The list lives in this browser only, so guests can use it too. */
(() => {
  const board = document.getElementById("watchboard");
  if (!board) return;
  // Tells market.js to show ☆ buttons on rows it rebuilds.
  document.documentElement.dataset.watchlist = "ready";
  const grid = document.getElementById("watch-grid");
  const status = document.getElementById("watch-status");
  const resolutionButtons = Array.from(board.querySelectorAll("[data-resolution]"));
  const averageButtons = Array.from(board.querySelectorAll("[data-average]"));
  const LIST_KEY = "virtutrade:watchlist";
  const RESOLUTION_KEY = "virtutrade:watch-resolution";
  const MAX = 6;
  const PREFERRED = ["HPG", "FPT", "VNM", "MWG"];
  const SYMBOL = /^[A-Z][A-Z0-9]{2,9}$/;
  const kit = window.VirtuTradeCharts;
  const chartsReady = Boolean(window.LightweightCharts && kit);
  const money = new Intl.NumberFormat("en-US");

  let known = [];
  try { known = JSON.parse(document.getElementById("initial-quotes").textContent).map(quote => quote.symbol); } catch { /* table still works */ }

  function loadList() {
    try {
      const saved = JSON.parse(localStorage.getItem(LIST_KEY));
      if (Array.isArray(saved)) return [...new Set(saved.filter(symbol => typeof symbol === "string" && SYMBOL.test(symbol)))].slice(0, MAX);
    } catch { /* storage may be blocked or hold old data */ }
    const preferred = PREFERRED.filter(symbol => known.includes(symbol));
    return preferred.length ? preferred : known.slice(0, 4);
  }
  let symbols = loadList();
  const saveList = () => { try { localStorage.setItem(LIST_KEY, JSON.stringify(symbols)); } catch { /* optional */ } };

  let resolution = "1D";
  try { resolution = localStorage.getItem(RESOLUTION_KEY) || "1D"; } catch { /* optional */ }
  if (!resolutionButtons.some(button => button.dataset.resolution === resolution)) resolution = "1D";
  let enabled = chartsReady ? kit.savedAverages() : new Set();

  const cards = new Map();
  const element = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const sourceName = source => source === "dnse" ? "DNSE" : source === "simulation" ? "Simulated" : "Illustrative";
  const tone = value => value === null ? "unclassified" : value > 0 ? "positive" : value < 0 ? "negative" : "neutral";

  function createCard(symbol) {
    const card = element("article", "watch-card");
    card.setAttribute("aria-labelledby", `watch-${symbol}`);
    const head = element("div", "watch-card-head");
    const link = element("a", "watch-symbol");
    link.id = `watch-${symbol}`;
    link.href = `/market/${encodeURIComponent(symbol)}`;
    const name = element("small", "", "Loading…");
    link.append(element("strong", "", symbol), name);
    link.setAttribute("aria-label", `${symbol}: open the full chart`);
    const price = element("div", "watch-price");
    const value = element("strong", "", "—");
    const change = element("small", "unclassified", "");
    price.append(value, change);
    const remove = element("button", "watch-remove", "×");
    remove.type = "button";
    remove.dataset.unwatch = symbol;
    remove.setAttribute("aria-label", `Remove ${symbol} from watchlist`);
    head.append(link, price, remove);
    const chartBox = element("div", "watch-chart");
    chartBox.setAttribute("role", "img");
    chartBox.setAttribute("aria-label", `${symbol} chart loading`);
    const foot = element("div", "watch-card-foot");
    const averages = element("span", "watch-averages");
    const source = element("span", "source", "");
    foot.append(averages, source);
    card.append(head, chartBox, foot);
    const entry = {symbol, card, name, value, change, chartBox, averages, source, request: 0, timer: null, view: null};
    if (chartsReady) {
      entry.view = kit.createCandleChart(chartBox, {compact: true});
      entry.view.setAverages(enabled);
    } else {
      chartBox.textContent = "Chart library unavailable.";
    }
    return entry;
  }

  function showPrice(entry, quote) {
    if (!quote) return;
    entry.name.textContent = quote.name;
    entry.value.textContent = money.format(quote.price_vnd);
    const change = quote.change === null || quote.change === undefined ? null : Number(quote.change);
    entry.value.className = tone(change);
    entry.change.className = tone(change);
    entry.change.textContent = change === null ? "No reference" : `${change > 0 ? "+" : ""}${quote.change}%`;
  }

  function showAverages(entry) {
    if (!entry.view || !entry.view.bars.length) { entry.averages.replaceChildren(); return; }
    const index = entry.view.bars.length - 1;
    const close = entry.view.bars[index].close;
    entry.averages.replaceChildren(...entry.view.averagesAt(index).map(({period, color, value}) => {
      const chip = element("span", "average-chip");
      chip.style.setProperty("--average-color", color);
      if (value === null) {
        chip.textContent = `MA${period} —`;
        chip.title = `MA${period} needs ${period} candles`;
      } else {
        const place = kit.position(close, value);
        chip.textContent = `MA${period} ${place === "above" ? "▲" : place === "below" ? "▼" : "="}`;
        chip.title = `Close ${money.format(close)} is ${place} MA${period} (${money.format(Math.round(value))})`;
        chip.classList.add(place);
      }
      return chip;
    }));
  }

  async function refresh(entry, fresh) {
    clearTimeout(entry.timer);
    const mine = ++entry.request;
    let poll = true;
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 8000);
      let response, data;
      try {
        response = await fetch(`/api/market/bars/${encodeURIComponent(entry.symbol)}?resolution=${encodeURIComponent(resolution)}`, {cache: "no-store", signal: controller.signal});
        data = await response.json();
      } finally { clearTimeout(timeout); }
      if (mine !== entry.request || !cards.has(entry.symbol)) return;
      if (response.status === 404) {
        poll = false;
        entry.name.textContent = "Not in the stored market";
        entry.chartBox.setAttribute("aria-label", `${entry.symbol} is not in the stored market; remove it from the watchlist.`);
        return;
      }
      if (!response.ok || !Array.isArray(data.bars)) throw new Error("Unavailable");
      showPrice(entry, data.quote);
      entry.source.textContent = sourceName(data.source);
      entry.source.title = data.source === "dnse" ? "DNSE market data" : "Generated practice data, not real market data";
      if (entry.view) {
        if (data.bars.length) entry.view.setBars(data.bars, resolution, fresh); else entry.view.clear();
        showAverages(entry);
      }
      const last = data.bars.at(-1);
      entry.chartBox.setAttribute("aria-label", last
        ? `${entry.symbol} ${resolution} candles, ${data.bars.length} shown, latest close ${money.format(last.close)} VND, ${sourceName(data.source)} data.`
        : `${entry.symbol}: no candles yet.`);
      entry.card.classList.remove("stale");
    } catch {
      if (mine === entry.request) entry.card.classList.add("stale");
    } finally {
      if (poll && mine === entry.request && cards.has(entry.symbol) && !document.hidden) {
        entry.timer = setTimeout(() => refresh(entry, false), resolution === "1D" ? 60000 : 15000);
      }
    }
  }

  function render() {
    for (const [symbol, entry] of cards) {
      if (symbols.includes(symbol)) continue;
      clearTimeout(entry.timer);
      entry.view?.chart.remove();
      entry.card.remove();
      cards.delete(symbol);
    }
    symbols.forEach((symbol, index) => {
      let entry = cards.get(symbol);
      if (!entry) {
        entry = createCard(symbol);
        cards.set(symbol, entry);
        // Stagger first loads so several cards do not hit the server at once.
        setTimeout(() => refresh(entry, true), index * 120);
      }
      grid.append(entry.card);
    });
    grid.querySelector(".watch-empty")?.remove();
    if (!symbols.length) {
      grid.append(element("p", "watch-empty", "Your watchlist is empty. Select ☆ next to a stock in the price board to add it here."));
    }
    syncStars();
  }

  function syncStars() {
    for (const button of document.querySelectorAll("[data-watch]")) {
      const watched = symbols.includes(button.dataset.watch);
      button.hidden = false;
      button.textContent = watched ? "★" : "☆";
      button.setAttribute("aria-pressed", String(watched));
    }
  }

  function toggle(symbol) {
    if (symbols.includes(symbol)) {
      symbols = symbols.filter(item => item !== symbol);
      status.textContent = `${symbol} removed from your watchlist.`;
    } else if (symbols.length >= MAX) {
      status.textContent = `Your watchlist holds up to ${MAX} stocks. Remove one with × first.`;
      return;
    } else {
      symbols = [...symbols, symbol];
      status.textContent = `${symbol} added to your watchlist.`;
    }
    saveList();
    render();
  }

  document.addEventListener("click", event => {
    const star = event.target.closest("[data-watch]");
    if (star) { toggle(star.dataset.watch); return; }
    const remove = event.target.closest("[data-unwatch]");
    if (remove && board.contains(remove)) {
      const next = remove.closest(".watch-card")?.nextElementSibling?.querySelector("[data-unwatch]");
      toggle(remove.dataset.unwatch);
      // Keep keyboard focus inside the board after the card disappears.
      (next || board.querySelector("[data-unwatch]") || resolutionButtons[0])?.focus();
    }
  });

  function selectResolution(next) {
    resolution = next;
    for (const button of resolutionButtons) button.setAttribute("aria-pressed", String(button.dataset.resolution === next));
    try { localStorage.setItem(RESOLUTION_KEY, next); } catch { /* optional */ }
    for (const entry of cards.values()) { entry.view?.clear(); refresh(entry, true); }
  }
  for (const button of resolutionButtons) button.addEventListener("click", () => selectResolution(button.dataset.resolution));

  function applyAverages(periods) {
    enabled = new Set(periods);
    for (const button of averageButtons) button.setAttribute("aria-pressed", String(enabled.has(Number(button.dataset.average))));
    for (const entry of cards.values()) { entry.view?.setAverages(enabled); showAverages(entry); }
  }
  for (const button of averageButtons) {
    button.hidden = !chartsReady;
    button.addEventListener("click", () => {
      const periods = new Set(enabled);
      const period = Number(button.dataset.average);
      if (periods.has(period)) periods.delete(period); else periods.add(period);
      kit.saveAverages(periods);
    });
  }
  document.addEventListener("virtutrade:averages", event => applyAverages(event.detail));

  // The price board polls every three seconds; reuse it for card prices and star states.
  document.addEventListener("virtutrade:quotes", event => {
    for (const quote of event.detail) { const entry = cards.get(quote.symbol); if (entry) showPrice(entry, quote); }
    syncStars();
  });
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) for (const entry of cards.values()) refresh(entry, false);
  });

  for (const button of resolutionButtons) button.setAttribute("aria-pressed", String(button.dataset.resolution === resolution));
  applyAverages(enabled);
  render();
})();
