/* Refresh only the public, read-only quote snapshot; no provider credentials reach the browser. */
(() => {
  const rows = document.getElementById("quote-rows");
  if (!rows) return;
  const status = document.getElementById("refresh-status");
  const retry = document.getElementById("retry-market");
  const query = (rows.dataset.query || "").trim();
  const money = new Intl.NumberFormat("en-US");
  let timer;

  const sourceName = quote => quote.source === "simulation" ? "Simulation / generated" :
    quote.source === "dnse" ? "DNSE" : "Demo / seed";
  const quoteTime = value => {
    const time = new Date(value);
    if (Number.isNaN(time.getTime())) return value;
    return new Intl.DateTimeFormat("en-GB", {
      timeZone: "Asia/Ho_Chi_Minh", day: "2-digit", month: "2-digit", year: "numeric",
      hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
    }).format(time) + " (UTC+7)";
  };
  const direction = quote => quote.change === null ? "neutral" :
    Number(quote.change) > 0 ? "positive" : Number(quote.change) < 0 ? "negative" : "neutral";

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

  function update(quotes) {
    const focused = rows.contains(document.activeElement) ? document.activeElement.getAttribute("aria-label") : null;
    const fragment = document.createDocumentFragment();
    for (const quote of quotes) {
      const row = document.createElement("tr");
      const company = cell("Symbol / Company");
      company.append(element("strong", quote.symbol), element("small", quote.name));
      const change = Number(quote.change);
      const changeCell = cell("Change vs reference", `number ${direction(quote)}`);
      changeCell.textContent = quote.change === null ? "—" : `${change > 0 ? "+" : ""}${quote.change}%`;
      if (quote.change === null) changeCell.append(element("small", "Reference unavailable"));
      const timestamp = cell("Last quote (UTC+7)");
      const time = element("time", quoteTime(quote.quoted_at));
      time.dateTime = quote.quoted_at;
      time.title = quote.quoted_at;
      timestamp.append(time);
      const source = cell("Source / Status");
      source.append(element("span", sourceName(quote), "source"));
      source.append(element("small", quote.stale ? "Price may be delayed" : "Freshness checked", quote.stale ? "delayed" : ""));
      const action = cell("Details");
      const link = element("a", "View");
      link.href = `/market/${encodeURIComponent(quote.symbol)}`;
      link.setAttribute("aria-label", `View ${quote.symbol} details`);
      action.append(link);
      row.append(company, cell("Price (VND)", "number price"), changeCell, timestamp, source, action);
      row.children[1].textContent = money.format(quote.price_vnd);
      fragment.append(row);
    }
    if (!quotes.length) {
      const row = document.createElement("tr");
      const empty = element("td", query ? `No stocks match “${query}”.` : "No quotes yet.");
      empty.colSpan = 6;
      row.append(empty);
      fragment.append(row);
    }
    rows.replaceChildren(fragment);
    if (focused) [...rows.querySelectorAll("a")].find(link => link.getAttribute("aria-label") === focused)?.focus({preventScroll: true});
    document.getElementById("symbol-count").textContent = query ? `${quotes.length} matching symbols · VND` : `${quotes.length} symbols · VND`;
  }

  function schedule() {
    clearTimeout(timer);
    timer = setTimeout(refresh, 3000);
  }

  async function refresh() {
    status.textContent = "Refreshing quotes…";
    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 5000);
      let response;
      let data;
      try {
        const suffix = query ? `?q=${encodeURIComponent(query)}` : "";
        response = await fetch(`/api/market/quotes${suffix}`, {cache: "no-store", signal: controller.signal});
        data = await response.json();
      } finally {
        clearTimeout(timeout);
      }
      if (!response.ok || !Array.isArray(data.quotes)) throw new Error("Market unavailable");
      update(data.quotes);
      document.getElementById("market-error")?.setAttribute("hidden", "");
      retry.hidden = true;
      status.classList.remove("delayed");
      status.textContent = "Snapshot refreshed. Check each quote’s timestamp; prices may be delayed.";
    } catch {
      retry.hidden = false;
      status.classList.add("delayed");
      status.textContent = "Could not refresh. Displaying the last snapshot; prices may be delayed.";
    } finally {
      schedule();
    }
  }

  retry.addEventListener("click", refresh);
  schedule();
})();
