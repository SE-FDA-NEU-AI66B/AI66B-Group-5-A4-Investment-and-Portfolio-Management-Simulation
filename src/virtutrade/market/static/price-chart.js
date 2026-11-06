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
  const retry = document.getElementById("chart-retry");
  const livePrice = document.getElementById("detail-price");
  const buttons = Array.from(panel.querySelectorAll("[data-resolution]"));
  const money = new Intl.NumberFormat("en-US");
  const VIETNAM_OFFSET = 7 * 3600;
  const LABELS = {"1": "1-minute", "5": "5-minute", "15": "15-minute", "1H": "hourly", "1D": "daily"};
  const UP = "#39d69c", DOWN = "#ff667b";

  if (!window.LightweightCharts) {
    status.textContent = "The chart library could not load. Prices above are still current.";
    container.hidden = true;
    return;
  }
  const {createChart, CandlestickSeries, HistogramSeries, CrosshairMode} = window.LightweightCharts;
  const chart = createChart(container, {
    autoSize: true,
    layout: {background: {color: "#15181f"}, textColor: "#a1a9b8", attributionLogo: true},
    grid: {vertLines: {color: "#20242d"}, horzLines: {color: "#20242d"}},
    rightPriceScale: {borderColor: "#2a2e38"},
    timeScale: {borderColor: "#2a2e38", rightOffset: 4},
    crosshair: {mode: CrosshairMode.Normal},
    localization: {priceFormatter: value => money.format(Math.round(value))},
  });
  const candles = chart.addSeries(CandlestickSeries, {
    upColor: UP, downColor: DOWN, borderUpColor: UP, borderDownColor: DOWN,
    wickUpColor: UP, wickDownColor: DOWN, priceLineColor: "#77808f",
  });
  const volume = chart.addSeries(HistogramSeries, {priceScaleId: "volume", priceFormat: {type: "volume"}, lastValueVisible: false, priceLineVisible: false});
  chart.priceScale("volume").applyOptions({scaleMargins: {top: 0.8, bottom: 0}});
  candles.priceScale().applyOptions({scaleMargins: {top: 0.08, bottom: 0.25}});

  let resolution = "1D";
  try { resolution = localStorage.getItem("virtutrade:chart-resolution") || "1D"; } catch { /* storage may be blocked */ }
  if (!buttons.some(button => button.dataset.resolution === resolution)) resolution = "1D";
  let loaded = [];
  let timer;
  let request = 0;

  // The chart draws in UTC; shift intraday bars so axes read in Vietnam time.
  function chartTime(bar) {
    if (resolution !== "1D") return bar.time + VIETNAM_OFFSET;
    const day = new Date((bar.time + VIETNAM_OFFSET) * 1000);
    return {year: day.getUTCFullYear(), month: day.getUTCMonth() + 1, day: day.getUTCDate()};
  }
  const toCandle = bar => ({time: chartTime(bar), open: bar.open, high: bar.high, low: bar.low, close: bar.close});
  const toVolume = bar => ({time: chartTime(bar), value: bar.volume, color: bar.close >= bar.open ? "rgba(57,214,156,.35)" : "rgba(255,102,123,.35)"});

  function showLegend(bar) {
    if (!bar) { legend.textContent = ""; return; }
    const change = bar.close - bar.open;
    legend.replaceChildren(...[["O", bar.open], ["H", bar.high], ["L", bar.low], ["C", bar.close]].map(([label, value]) => {
      const item = document.createElement("span");
      item.append(`${label} `);
      const number = document.createElement("strong");
      number.textContent = money.format(value);
      number.className = change > 0 ? "positive" : change < 0 ? "negative" : "neutral";
      item.append(number);
      return item;
    }), Object.assign(document.createElement("span"), {textContent: `Vol ${money.format(bar.volume)}`}));
  }
  chart.subscribeCrosshairMove(param => {
    if (!param.time) { showLegend(loaded.at(-1)); return; }
    const key = JSON.stringify(param.time);
    showLegend(loaded.find(bar => JSON.stringify(chartTime(bar)) === key));
  });

  function updateQuote(quote) {
    if (!livePrice || !quote) return;
    livePrice.firstChild.textContent = `${money.format(quote.price_vnd)} `;
    const change = quote.change === null ? null : Number(quote.change);
    livePrice.className = `detail-price ${change === null ? "unclassified" : change > 0 ? "positive" : change < 0 ? "negative" : "neutral"}`;
  }

  const sameBar = (a, b) => a.time === b.time && a.open === b.open && a.high === b.high &&
    a.low === b.low && a.close === b.close && a.volume === b.volume;

  // True when only the newest candle changed or new candles were appended:
  // the chart can then update in place, which only accepts the newest time.
  function appendOnly(previous, next) {
    if (!previous.length || next.length < previous.length || next.length - previous.length > 2) return false;
    const last = previous.length - 1;
    return next[last].time === previous[last].time && previous.slice(0, last).every((bar, index) => sameBar(bar, next[index]));
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
      candles.setData([]); volume.setData([]); loaded = [];
      status.textContent = generated ? "No candles to draw." : "Waiting for DNSE candles. They appear once the market-data worker has received history for this stock.";
      container.setAttribute("aria-label", `${symbol} price chart: no candles yet`);
      showLegend(null);
      return;
    }
    if (!fresh && appendOnly(loaded, bars)) {
      for (const bar of bars.slice(loaded.length - 1)) { candles.update(toCandle(bar)); volume.update(toVolume(bar)); }
    } else {
      candles.setData(bars.map(toCandle)); volume.setData(bars.map(toVolume));
      if (fresh) chart.timeScale().fitContent();
    }
    loaded = bars;
    const last = bars.at(-1);
    showLegend(last);
    const daily = resolution === "1D";
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
      status.textContent = loaded.length ? "Could not refresh the chart. Showing the last candles loaded." : "The chart could not load. Prices above are still available.";
    } finally {
      // Hidden tabs stop polling; visibilitychange reloads when the tab returns.
      if (mine === request && !document.hidden) timer = setTimeout(() => load(false), resolution === "1D" ? 30000 : 5000);
    }
  }

  function select(next) {
    resolution = next;
    chart.timeScale().applyOptions({timeVisible: next !== "1D", secondsVisible: false});
    for (const button of buttons) button.setAttribute("aria-pressed", String(button.dataset.resolution === next));
    try { localStorage.setItem("virtutrade:chart-resolution", next); } catch { /* optional */ }
    loaded = [];
    load(true);
  }
  for (const button of buttons) button.addEventListener("click", () => select(button.dataset.resolution));
  retry.addEventListener("click", () => load(loaded.length === 0));
  document.addEventListener("visibilitychange", () => { if (!document.hidden) load(false); });
  select(resolution);
})();
