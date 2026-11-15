/* Candlestick chart for one stock: reads the public bars API, never provider credentials. */
(() => {
  const panel = document.getElementById("price-chart-panel");
  const container = document.getElementById("price-chart");
  if (!panel || !container) return;
  const symbol = panel.dataset.symbol;
  const status = document.getElementById("chart-status");
  const source = document.getElementById("chart-source");
  const notice = document.getElementById("chart-notice");
  const legend = document.getElementById("chart-legend");
  const summary = document.getElementById("chart-ma-summary");
  const retry = document.getElementById("chart-retry");
  const livePrice = document.getElementById("detail-price");
  const interval = panel.querySelector("[data-interval]");
  const averageButtons = Array.from(panel.querySelectorAll("[data-average]"));
  const LABELS = {"15": "15-minute", "1H": "hourly", "4H": "4-hour", "1D": "daily", "1W": "weekly", "1M": "monthly"};

  if (!window.LightweightCharts || !window.VirtuTradeCharts) {
    status.textContent = "The chart library could not load. Prices above are still current.";
    container.hidden = true;
    return;
  }
  const {DAILY, money, position, savedAverages, saveAverages, createCandleChart} = window.VirtuTradeCharts;
  const view = createCandleChart(container);

  let resolution = "1D";
  try { resolution = localStorage.getItem("virtutrade:chart-resolution") || "1D"; } catch { /* storage may be blocked */ }
  // A saved interval that no longer exists (for example 1m or 5m) falls back to daily.
  if (!Array.from(interval.options).some(option => option.value === resolution)) resolution = "1D";
  let timer;
  let request = 0;

  const tone = (a, b) => a > b ? "positive" : a < b ? "negative" : "neutral";
  const arrow = place => place === "above" ? "▲" : place === "below" ? "▼" : "=";

  function showLegend(index) {
    const bar = view.bars[index];
    if (!bar) { legend.textContent = ""; return; }
    const items = [["O", bar.open], ["H", bar.high], ["L", bar.low], ["C", bar.close]].map(([label, value]) => {
      const item = document.createElement("span");
      item.append(`${label} `);
      item.append(Object.assign(document.createElement("strong"), {textContent: money.format(value), className: tone(bar.close, bar.open)}));
      return item;
    });
    items.push(Object.assign(document.createElement("span"), {textContent: `Vol ${money.format(bar.volume)}`}));
    for (const {period, color, value} of view.averagesAt(index)) {
      const item = document.createElement("span");
      item.className = "legend-average";
      item.style.setProperty("--average-color", color);
      if (value === null) {
        item.textContent = `MA${period} —`;
      } else {
        const place = position(bar.close, value);
        item.append(`MA${period} ${money.format(Math.round(value))} `);
        item.append(Object.assign(document.createElement("strong"), {
          textContent: arrow(place), className: place === "above" ? "positive" : place === "below" ? "negative" : "neutral",
          title: `Close is ${place} MA${period}`,
        }));
      }
      items.push(item);
    }
    legend.replaceChildren(...items);
  }

  // One sentence on where the latest close sits against each enabled average.
  function describeAverages() {
    const index = view.bars.length - 1;
    const last = view.bars[index];
    const parts = view.averagesAt(index).map(({period, value}) => value === null
      ? `MA${period} needs ${period} candles`
      : `${position(last.close, value)} MA${period} (${money.format(Math.round(value))})`);
    summary.textContent = last && parts.length
      ? `Latest close ${money.format(last.close)}: ${parts.join(", ")}.`
      : "Turn on MA20, MA50 or MA200 to compare the price with its moving averages.";
  }

  view.chart.subscribeCrosshairMove(param => {
    showLegend(param.time ? view.indexAt(param.time) : view.bars.length - 1);
  });

  function updateQuote(quote) {
    if (!livePrice || !quote) return;
    livePrice.firstChild.textContent = `${money.format(quote.price_vnd)} `;
    const change = quote.change === null ? null : Number(quote.change);
    livePrice.className = `detail-price ${change === null ? "unclassified" : change > 0 ? "positive" : change < 0 ? "negative" : "neutral"}`;
  }

  function render(data, fresh) {
    const bars = data.bars;
    const generated = data.source !== "dnse";
    notice.hidden = !generated;
    notice.textContent = data.source === "simulation"
      ? "Simulated market: prices and candles come from the practice simulator, not a real exchange. Earlier candles are illustrative."
      : generated ? "Illustrative history: generated from the stored demo price, not real market data. Orders use the stored quote only." : "";
    source.textContent = `${LABELS[resolution]} candles · ${data.source === "simulation" ? "practice simulator" : generated ? "generated for practice" : "DNSE market data"}`;
    if (!bars.length) {
      view.clear();
      status.textContent = generated ? "No candles to draw." : "Waiting for DNSE candles. They appear once the market-data worker has received history for this stock.";
      container.setAttribute("aria-label", `${symbol} price chart: no candles yet`);
      showLegend(-1);
      summary.textContent = "";
      return;
    }
    view.setBars(bars, resolution, fresh);
    const last = bars.at(-1);
    showLegend(bars.length - 1);
    describeAverages();
    const daily = DAILY.has(resolution);
    const stamp = new Intl.DateTimeFormat("en-GB", daily
      ? {timeZone: "Asia/Ho_Chi_Minh", day: "2-digit", month: "short", year: "numeric"}
      : {timeZone: "Asia/Ho_Chi_Minh", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", hourCycle: "h23"}).format(new Date(last.time * 1000)) + (daily ? "" : " UTC+7");
    container.setAttribute("aria-label", `${symbol} ${LABELS[resolution]} candlestick chart, ${bars.length} candles. Latest candle ${stamp}: open ${money.format(last.open)}, high ${money.format(last.high)}, low ${money.format(last.low)}, close ${money.format(last.close)} VND.`);
    status.textContent = `${bars.length} candles · latest ${stamp} · updates automatically`;
  }

  async function load(fresh) {
    clearTimeout(timer);
    const mine = ++request;
    if (fresh) status.textContent = "Loading candles…";
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 8000);
      let response, data;
      try {
        response = await fetch(`/api/market/bars/${encodeURIComponent(symbol)}?resolution=${encodeURIComponent(resolution)}`, {cache: "no-store", signal: controller.signal});
        data = await response.json();
      } finally { clearTimeout(timeout); }
      if (mine !== request) return;
      if (!response.ok || !Array.isArray(data.bars)) throw new Error("Unavailable");
      render(data, fresh);
      updateQuote(data.quote);
      retry.hidden = true;
      status.classList.remove("delayed");
    } catch {
      if (mine !== request) return;
      retry.hidden = false;
      status.classList.add("delayed");
      status.textContent = view.bars.length ? "Could not refresh the chart. Showing the last candles loaded." : "The chart could not load. Prices above are still available.";
    } finally {
      // Hidden tabs stop polling; visibilitychange reloads when the tab returns.
      if (mine === request && !document.hidden) timer = setTimeout(() => load(false), DAILY.has(resolution) ? 30000 : 5000);
    }
  }

  function choose(next) {
    resolution = next;
    interval.value = next;
    try { localStorage.setItem("virtutrade:chart-resolution", next); } catch { /* optional */ }
    view.clear();
    load(true);
  }

  function applyAverages(periods) {
    view.setAverages(periods);
    for (const button of averageButtons) button.setAttribute("aria-pressed", String(periods.has(Number(button.dataset.average))));
    showLegend(view.bars.length - 1);
    if (view.bars.length) describeAverages();
  }

  interval.addEventListener("change", () => choose(interval.value));
  for (const button of averageButtons) button.addEventListener("click", () => {
    const periods = view.enabled;
    const period = Number(button.dataset.average);
    if (periods.has(period)) periods.delete(period); else periods.add(period);
    saveAverages(periods);
    applyAverages(periods);
  });
  retry.addEventListener("click", () => load(view.bars.length === 0));
  document.addEventListener("visibilitychange", () => { if (!document.hidden) load(false); });
  applyAverages(savedAverages());
  choose(resolution);
})();
