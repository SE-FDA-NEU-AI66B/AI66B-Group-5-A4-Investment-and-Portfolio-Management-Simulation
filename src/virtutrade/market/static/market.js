/* Poll our read-only snapshot API; DNSE credentials never reach this browser. */
(() => {
  const rows = document.getElementById("quote-rows");
  if (!rows) return;
  const status = document.getElementById("refresh-status");
  const money = new Intl.NumberFormat("en-US");
  const query = (rows.dataset.query || "").trim();
  const needle = query.toLowerCase();

  function element(tag, text, className) {
    const node = document.createElement(tag);
    node.textContent = text;
    if (className) node.className = className;
    return node;
  }

  function cell(label, className) {
    const node = document.createElement("td");
    node.dataset.label = label;
    if (className) node.className = className;
    return node;
  }

  function matches(quote) {
    return !needle || quote.symbol.toLowerCase().includes(needle) ||
      quote.name.toLowerCase().includes(needle);
  }

  function update(quotes) {
    const initialError = document.getElementById("market-error");
    if (initialError) initialError.hidden = true;
    const shown = quotes.filter(matches);
    const fragment = document.createDocumentFragment();
    for (const quote of shown) {
      const row = document.createElement("tr");
      const company = cell("Symbol / Company");
      company.append(element("strong", quote.symbol), element("small", quote.name));
      const price = cell("Price (VND)", "number price");
      price.textContent = money.format(quote.price_vnd);
      const change = Number(quote.change);
      const changeCell = cell("Change vs reference",
        `number ${change > 0 ? "positive" : change < 0 ? "negative" : "neutral"}`);
      changeCell.textContent = quote.change === null ? "—" :
        `${change > 0 ? "+" : ""}${quote.change}%`;
      if (quote.change === null) changeCell.append(element("small", "Reference unavailable"));
      const timestamp = cell("Last quote (UTC)");
      const time = element("time", quote.quoted_at);
      time.dateTime = quote.quoted_at;
      timestamp.append(time);
      const source = cell("Source / Status");
      source.append(element("span", quote.source === "simulation" ? "Simulation / generated" : quote.source === "dnse" ? "DNSE" : "Demo / seed", "source"));
      if (quote.stale) source.append(element("small", "Price may be delayed", "delayed"));
      const action = cell("Details");
      const link = element("a", "View");
      link.href = "/market/" + encodeURIComponent(quote.symbol);
      link.setAttribute("aria-label", `View ${quote.symbol} details`);
      action.append(link);
      row.append(company, price, changeCell, timestamp, source, action);
      fragment.append(row);
    }
    if (!shown.length) {
      const row = document.createElement("tr");
      const empty = document.createElement("td");
      empty.colSpan = 6;
      if (quotes.length) {
        const clear = element("a", "Clear search");
        clear.href = "/market";
        empty.append(element("strong", `No stocks match "${query}"`),
          document.createElement("br"), clear);
      } else {
        empty.append(element("strong", "No quotes yet"));
      }
      row.append(empty);
      fragment.append(row);
    }
    rows.replaceChildren(fragment);
    document.getElementById("symbol-count").textContent = query
      ? `${shown.length} of ${quotes.length} symbols · VND`
      : `${quotes.length} symbols · VND`;
    document.getElementById("data-notice").textContent = quotes.some(q => q.source === "simulation")
      ? "Simulation / generated · Scenario reference prices, not live DNSE data."
      : quotes.some(q => q.source === "dnse")
      ? "DNSE market data · Last received prices. Check timestamps and sources; some rows may still contain demo data. No real money or market orders."
      : "Demo data · Seeded example prices, not live DNSE quotes. No real money or market orders.";
  }

  const searchForm = document.getElementById("search-form");
  if (searchForm) {
    searchForm.addEventListener("submit", () => {
      status.textContent = "Loading prices…";
    });
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