/* Poll the public, read-only quote API; provider credentials never reach this browser. */
(() => {
  const rows = document.getElementById("quote-rows");
  if (!rows) return;
  const status = document.getElementById("refresh-status");
  const retry = document.getElementById("retry-market");
  const query = document.getElementById("market-query")?.value || "";
  const money = new Intl.NumberFormat("en-US");
  const direction = quote => quote.change === null ? "unclassified" : Number(quote.change) > 0 ? "positive" : Number(quote.change) < 0 ? "negative" : "neutral";
  const sourceName = quote => quote.source === "dnse" ? "DNSE" : quote.source === "simulation" ? "Simulation / generated" : "Demo / seed";
  const quoteTime = value => {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("en-GB", {timeZone: "Asia/Ho_Chi_Minh", day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23"}).format(date) + " UTC+7";
  };
  let timer;

  function element(tag, text, className) { const node = document.createElement(tag); node.textContent = text; if (className) node.className = className; return node; }
  function update(quotes) {
    const fragment = document.createDocumentFragment();
    for (const quote of quotes) {
      const row = document.createElement("tr");
      const company = document.createElement("td");
      const detail = element("a", "", "quote-link"); detail.href = `/market/${encodeURIComponent(quote.symbol)}`; detail.append(element("strong", quote.symbol), element("small", quote.name)); company.append(detail);
      const hasReference = quote.change !== null && quote.previous_close_vnd !== null;
      const change = Number(quote.change);
      const changeCell = element("td", quote.change === null ? "—" : `${change > 0 ? "+" : ""}${quote.change}%`, `number ${direction(quote)}`);
      if (quote.change === null) changeCell.append(element("small", "Reference unavailable"));
      const timestamp = document.createElement("td"); const time = element("time", quoteTime(quote.quoted_at)); time.dateTime = quote.quoted_at; time.title = quote.quoted_at; timestamp.append(time);
      const source = document.createElement("td"); source.append(element("span", sourceName(quote), "source")); source.append(element("small", quote.stale ? "Price may be delayed" : "Freshness checked", quote.stale ? "delayed" : ""));
      const action = document.createElement("td"); const buy = element("a", "Buy ↗", "row-action"); buy.href = `/trade?symbol=${encodeURIComponent(quote.symbol)}`; buy.setAttribute("aria-label", `Buy ${quote.symbol}`); action.append(buy);
      const delta = hasReference ? quote.price_vnd - quote.previous_close_vnd : null;
      row.append(company, element("td", hasReference ? money.format(quote.previous_close_vnd) : "—", "number reference"), element("td", money.format(quote.price_vnd), `number price ${direction(quote)}`), element("td", delta === null ? "—" : `${delta > 0 ? "+" : ""}${money.format(delta)}`, `number ${direction(quote)}`), changeCell, timestamp, source, action);
      fragment.append(row);
    }
    if (!quotes.length) { const row = document.createElement("tr"); const cell = element("td", query ? `No stocks match “${query}”.` : "No quotes yet."); cell.colSpan = 8; row.append(cell); fragment.append(row); }
    rows.replaceChildren(fragment);
    document.getElementById("instrument-total").textContent = `${quotes.length} symbols`;
    document.getElementById("symbol-count").textContent = query ? `${quotes.length} matching symbols · VND` : `${quotes.length} symbols · VND`;
  }
  function schedule() { clearTimeout(timer); timer = setTimeout(refresh, 3000); }
  async function refresh() {
    status.textContent = "Refreshing quotes…";
    try {
      const controller = new AbortController(); const timeout = setTimeout(() => controller.abort(), 5000); let response; let data;
      try { const suffix = query ? `?q=${encodeURIComponent(query)}` : ""; response = await fetch(`/api/market/quotes${suffix}`, {cache: "no-store", signal: controller.signal}); data = await response.json(); } finally { clearTimeout(timeout); }
      if (!response.ok || !Array.isArray(data.quotes)) throw new Error("Unavailable");
      update(data.quotes); document.getElementById("market-error")?.setAttribute("hidden", ""); retry.hidden = true; status.classList.remove("delayed"); status.textContent = "Snapshot refreshed. Check each quote’s timestamp; prices may be delayed.";
    } catch { retry.hidden = false; status.classList.add("delayed"); status.textContent = "Could not refresh. Displaying the last snapshot; prices may be delayed."; } finally { schedule(); }
  }
  retry.addEventListener("click", refresh);
  for (const time of rows.querySelectorAll("time")) { time.title = time.dateTime; time.textContent = quoteTime(time.dateTime); }
  schedule();
})();
