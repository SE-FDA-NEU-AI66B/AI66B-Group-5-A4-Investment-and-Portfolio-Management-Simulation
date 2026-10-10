/* Poll our read-only snapshot API; DNSE credentials never reach this browser. */
(() => {
  const rows = document.getElementById("quote-rows");
  if (!rows) return;
  const status = document.getElementById("refresh-status");
  const money = new Intl.NumberFormat("en-US");

  function element(tag, text, className) {
    const node = document.createElement(tag);
    node.textContent = text;
    if (className) node.className = className;
    return node;
  }

  function update(quotes) {
    const initialError = document.getElementById("market-error");
    if (initialError) initialError.hidden = true;
    const fragment = document.createDocumentFragment();
    for (const quote of quotes) {
      const row = document.createElement("tr");
      const company = document.createElement("td");
      company.append(element("strong", quote.symbol), element("small", quote.name));
      const change = Number(quote.change);
      const changeCell = element("td", quote.change === null ? "—" :
        `${change > 0 ? "+" : ""}${quote.change}%`,
        `number ${change > 0 ? "positive" : change < 0 ? "negative" : "neutral"}`);
      if (quote.change === null) changeCell.append(element("small", "Reference unavailable"));
      const timestamp = document.createElement("td");
      const time = element("time", quote.quoted_at);
      time.dateTime = quote.quoted_at;
      timestamp.append(time);
      const source = document.createElement("td");
      source.append(element("span", quote.source === "dnse" ? "DNSE" : "Demo / seed", "source"));
      if (quote.stale) source.append(element("small", "Price may be delayed", "delayed"));
      row.append(company, element("td", money.format(quote.price_vnd), "number price"),
        changeCell, timestamp, source);
      fragment.append(row);
    }
    if (!quotes.length) {
      const row = document.createElement("tr");
      const empty = element("td", "No quotes yet");
      empty.colSpan = 5;
      row.append(empty);
      fragment.append(row);
    }
    rows.replaceChildren(fragment);
    document.getElementById("symbol-count").textContent = `${quotes.length} symbols · VND`;
    document.getElementById("data-notice").textContent = quotes.some(q => q.source === "dnse")
      ? "DNSE market data · Last received prices. Check timestamps and sources; some rows may still contain demo data. No real money or market orders."
      : "Demo data · Seeded example prices, not live DNSE quotes. No real money or market orders.";
  }

  async function refresh() {
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 5000);
      let response;
      let data;
      try {
        response = await fetch("/api/market/quotes", {cache: "no-store", signal: controller.signal});
        data = await response.json();
      } finally {
        clearTimeout(timeout);
      }
      if (!response.ok || !Array.isArray(data.quotes)) throw new Error("Unavailable");
      update(data.quotes);
      status.textContent = "Snapshot refreshed. Check each quote's timestamp; prices may be delayed.";
    } catch {
      status.textContent = "Could not refresh. Displaying the last snapshot; prices may be delayed.";
      status.classList.add("delayed");
      return;
    } finally {
      setTimeout(refresh, 3000);
    }
    status.classList.remove("delayed");
  }
  setTimeout(refresh, 3000);
})();
