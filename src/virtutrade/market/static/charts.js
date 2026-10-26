/* Present one stored quote per symbol; no historical prices are inferred. */
(() => {
  const chart = document.getElementById("change-chart");
  const summary = document.getElementById("change-chart-summary");
  const initial = document.getElementById("initial-quotes");
  if (!chart || !summary || !initial) return;

  const sourceName = source => source === "dnse" ? "DNSE" :
    source === "simulation" ? "Simulation" : "Demo";
  const empty = message => {
    const item = document.createElement("li");
    item.className = "chart-empty";
    item.textContent = message;
    chart.replaceChildren(item);
  };

  function render(quotes) {
    if (!Array.isArray(quotes)) throw new TypeError("Expected stored quotes");
    const ranked = quotes
      .filter(quote => quote && typeof quote.symbol === "string" &&
        quote.change !== null && quote.change !== undefined &&
        Number.isFinite(Number(quote.change)))
      .map(quote => ({...quote, movement: Number(quote.change)}))
      .sort((a, b) => Math.abs(b.movement) - Math.abs(a.movement) ||
        a.symbol.localeCompare(b.symbol))
      .slice(0, 8);

    if (!ranked.length) {
      summary.textContent = "No valid reference";
      empty("No comparison is available for these stocks. Their prices remain in the table above.");
      return;
    }

    const scale = Math.max(1, ...ranked.map(quote => Math.abs(quote.movement)));
    const fragment = document.createDocumentFragment();
    for (const quote of ranked) {
      const tone = quote.movement > 0 ? "positive" : quote.movement < 0 ? "negative" : "neutral";
      const item = document.createElement("li");
      item.className = "change-chart-row";
      const identity = document.createElement("span");
      identity.className = "change-chart-symbol";
      const symbol = document.createElement("strong");
      symbol.textContent = quote.symbol;
      const source = document.createElement("small");
      source.textContent = sourceName(quote.source);
      identity.append(symbol, source);

      const axis = document.createElement("span");
      axis.className = "change-chart-axis";
      axis.setAttribute("aria-hidden", "true");
      for (const half of ["negative", "positive"]) {
        const track = document.createElement("span");
        track.className = `change-chart-half ${half}`;
        if (tone === half || (tone === "neutral" && half === "positive")) {
          const bar = document.createElement("span");
          bar.className = `change-chart-bar ${tone}`;
          bar.style.width = quote.movement === 0 ? "3px" :
            `${Math.max(2, Math.abs(quote.movement) / scale * 100)}%`;
          track.append(bar);
        }
        axis.append(track);
      }

      const value = document.createElement("span");
      value.className = `change-chart-value ${tone}`;
      value.textContent = `${quote.movement > 0 ? "+" : ""}${quote.movement.toFixed(2)}%`;
      item.append(identity, axis, value);
      fragment.append(item);
    }
    chart.replaceChildren(fragment);
    summary.textContent = `${ranked.length} ranked / ${quotes.length} displayed`;
  }

  function renderSafely(quotes) {
    try { render(quotes); }
    catch {
      summary.textContent = "Chart unavailable";
      empty("The chart could not be drawn. The price table above is still available.");
    }
  }

  try { renderSafely(JSON.parse(initial.textContent)); }
  catch { renderSafely(null); }
  document.addEventListener("virtutrade:quotes", event => renderSafely(event.detail));
  document.addEventListener("virtutrade:quotes-error", () => {
    summary.textContent = "Last available snapshot; refresh failed";
  });
})();
