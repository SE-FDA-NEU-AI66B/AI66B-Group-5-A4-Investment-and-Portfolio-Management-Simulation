/* Shared candlestick pieces for the stock chart and the watchlist: series setup,
   Vietnam time, simple moving averages and the saved MA choice. */
window.VirtuTradeCharts = (() => {
  const money = new Intl.NumberFormat("en-US");
  const VIETNAM_OFFSET = 7 * 3600;
  const UP = "#39d69c", DOWN = "#ff667b";
  const AVERAGES = [
    {period: 20, color: "#f1c65d"},
    {period: 50, color: "#5b9cf6"},
    {period: 200, color: "#c084fc"},
  ];
  const AVERAGES_KEY = "virtutrade:moving-averages";
  const DEFAULT_AVERAGES = [20, 50];

  // The chart draws in UTC; shift intraday bars so axes read in Vietnam time,
  // and give daily bars their Vietnam trading date.
  function chartTime(bar, resolution) {
    if (resolution !== "1D") return bar.time + VIETNAM_OFFSET;
    const day = new Date((bar.time + VIETNAM_OFFSET) * 1000);
    return {year: day.getUTCFullYear(), month: day.getUTCMonth() + 1, day: day.getUTCDate()};
  }

  // Simple moving average of closes; entry i averages candles i-period+1..i, null before that.
  function movingAverage(bars, period) {
    const result = new Array(bars.length).fill(null);
    let sum = 0;
    bars.forEach((bar, index) => {
      sum += bar.close;
      if (index >= period) sum -= bars[index - period].close;
      if (index >= period - 1) result[index] = sum / period;
    });
    return result;
  }

  const position = (close, average) => close > average ? "above" : close < average ? "below" : "at";

  function savedAverages() {
    try {
      const value = JSON.parse(localStorage.getItem(AVERAGES_KEY));
      if (Array.isArray(value)) return new Set(value.filter(period => AVERAGES.some(average => average.period === period)));
    } catch { /* storage may be blocked or hold old data */ }
    return new Set(DEFAULT_AVERAGES);
  }

  function saveAverages(periods) {
    try { localStorage.setItem(AVERAGES_KEY, JSON.stringify([...periods])); } catch { /* optional */ }
    document.dispatchEvent(new CustomEvent("virtutrade:averages", {detail: new Set(periods)}));
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

  function createCandleChart(container, {compact = false} = {}) {
    const {createChart, CandlestickSeries, HistogramSeries, LineSeries, CrosshairMode} = window.LightweightCharts;
    const chart = createChart(container, {
      autoSize: true,
      // Compact charts share one TradingView attribution link in their section.
      layout: {background: {color: "#15181f"}, textColor: "#a1a9b8", attributionLogo: !compact, fontSize: compact ? 10 : 12},
      grid: {vertLines: {color: "#20242d", visible: !compact}, horzLines: {color: compact ? "#1b1e26" : "#20242d"}},
      rightPriceScale: {borderColor: "#2a2e38"},
      timeScale: {borderColor: "#2a2e38", rightOffset: compact ? 2 : 4},
      crosshair: {mode: CrosshairMode.Normal},
      localization: {priceFormatter: value => money.format(Math.round(value))},
      // Small charts must not capture page scrolling on phones.
      handleScroll: !compact,
      handleScale: !compact,
    });
    const candles = chart.addSeries(CandlestickSeries, {
      upColor: UP, downColor: DOWN, borderUpColor: UP, borderDownColor: DOWN,
      wickUpColor: UP, wickDownColor: DOWN, priceLineColor: "#77808f",
    });
    const volume = chart.addSeries(HistogramSeries, {priceScaleId: "volume", priceFormat: {type: "volume"}, lastValueVisible: false, priceLineVisible: false});
    chart.priceScale("volume").applyOptions({scaleMargins: {top: compact ? 0.84 : 0.8, bottom: 0}});
    candles.priceScale().applyOptions({scaleMargins: {top: 0.08, bottom: compact ? 0.2 : 0.25}});
    const lines = new Map(AVERAGES.map(({period, color}) => [period, chart.addSeries(LineSeries, {
      color, lineWidth: compact ? 1 : 2, priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false,
    })]));

    let bars = [];
    let resolution = "1D";
    let enabled = savedAverages();
    let averages = new Map();
    const toCandle = bar => ({time: chartTime(bar, resolution), open: bar.open, high: bar.high, low: bar.low, close: bar.close});
    const toVolume = bar => ({time: chartTime(bar, resolution), value: bar.volume, color: bar.close >= bar.open ? "rgba(57,214,156,.35)" : "rgba(255,102,123,.35)"});

    function drawAverages() {
      for (const [period, line] of lines) {
        const values = averages.get(period) || [];
        line.setData(enabled.has(period)
          ? bars.flatMap((bar, index) => values[index] === null || values[index] === undefined ? [] : [{time: chartTime(bar, resolution), value: values[index]}])
          : []);
      }
    }

    return {
      chart,
      get bars() { return bars; },
      get enabled() { return new Set(enabled); },
      setBars(next, nextResolution, fresh) {
        const sameScale = nextResolution === resolution;
        resolution = nextResolution;
        chart.timeScale().applyOptions({timeVisible: resolution !== "1D", secondsVisible: false});
        if (!fresh && sameScale && appendOnly(bars, next)) {
          for (const bar of next.slice(bars.length - 1)) { candles.update(toCandle(bar)); volume.update(toVolume(bar)); }
        } else {
          candles.setData(next.map(toCandle));
          volume.setData(next.map(toVolume));
          if (fresh) chart.timeScale().fitContent();
        }
        bars = next;
        averages = new Map(AVERAGES.map(({period}) => [period, movingAverage(next, period)]));
        drawAverages();
      },
      setAverages(periods) { enabled = new Set(periods); drawAverages(); },
      // MA values for the candle at `index`, for enabled averages only.
      averagesAt(index) {
        return AVERAGES.filter(({period}) => enabled.has(period)).map(({period, color}) => ({
          period, color, value: averages.get(period)?.[index] ?? null,
        }));
      },
      indexAt(time) {
        const key = JSON.stringify(time);
        return bars.findIndex(bar => JSON.stringify(chartTime(bar, resolution)) === key);
      },
      clear() {
        bars = [];
        averages = new Map();
        candles.setData([]);
        volume.setData([]);
        for (const line of lines.values()) line.setData([]);
      },
    };
  }

  return {AVERAGES, money, chartTime, movingAverage, position, savedAverages, saveAverages, appendOnly, createCandleChart};
})();
