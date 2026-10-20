/* Poll our read-only snapshot API; DNSE credentials never reach this browser. */
(() => {
  const rows = document.getElementById("quote-rows");
  if (!rows) return;
  const status = document.getElementById("refresh-status");
  const money = new Intl.NumberFormat("en-US");
  const direction = quote => quote.change === null ? "unclassified" :
    Number(quote.change) > 0 ? "positive" : Number(quote.change) < 0 ? "negative" : "neutral";
  const sourceName = quote => quote.source === "dnse" ? "DNSE" :
    quote.source === "simulation" ? "Simulation" : "Seed";
  let previousPrices = new Map();
  const quoteTime = value => {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? value : new Intl.DateTimeFormat("en-GB", {
      timeZone: "Asia/Ho_Chi_Minh", day: "2-digit", month: "short", hour: "2-digit",
      minute: "2-digit", second: "2-digit", hourCycle: "h23"
    }).format(date);
  };
  for (const time of rows.querySelectorAll("time")) {
    time.title = time.dateTime; time.textContent = quoteTime(time.dateTime);
  }

  function element(tag, text, className) {
    const node = document.createElement(tag);
    node.textContent = text;
    if (className) node.className = className;
    return node;
  }

  function update(quotes) {
    const focusedAction = rows.contains(document.activeElement) ?
      document.activeElement.getAttribute("aria-label") : null;
    const initialError = document.getElementById("market-error");
    if (initialError) initialError.hidden = true;
    const fragment = document.createDocumentFragment();
    for (const quote of quotes) {
      const row = document.createElement("tr");
      const previousPrice = previousPrices.get(quote.symbol);
      if (previousPrice !== undefined && previousPrice !== quote.price_vnd) {
        row.classList.add(quote.price_vnd > previousPrice ? "tick-up" : "tick-down");
      }
      const company = document.createElement("td");
      company.append(element("strong", quote.symbol), element("small", quote.name));
      const change = Number(quote.change);
      const changeCell = element("td", quote.change === null ? "—" :
        `${change > 0 ? "+" : ""}${quote.change}%`,
        `number ${change > 0 ? "positive" : change < 0 ? "negative" : "neutral"}`);
      if (quote.change === null) changeCell.append(element("small", "Reference unavailable"));
      const timestamp = document.createElement("td");
      const time = element("time", quoteTime(quote.quoted_at));
      time.dateTime = quote.quoted_at;
      time.title = quote.quoted_at;
      timestamp.append(time);
      const source = document.createElement("td");
      source.append(element("span", quote.source === "simulation" ? "Simulation / generated" : quote.source === "dnse" ? "DNSE" : "Demo / seed", "source"));
      if (quote.stale) source.append(element("small", "Price may be delayed", "delayed"));
      const action = document.createElement("td");
      const buy = element("a", "Buy ↗", "row-action");
      buy.href = `/trade?symbol=${encodeURIComponent(quote.symbol)}`;
      buy.setAttribute("aria-label", `Buy ${quote.symbol}`);
      action.append(buy);
      const hasReference = quote.change !== null && quote.previous_close_vnd !== null;
      const delta = hasReference ? quote.price_vnd - quote.previous_close_vnd : null;
      row.append(company,
        element("td", hasReference ? money.format(quote.previous_close_vnd) : "—", "number reference"),
        element("td", money.format(quote.price_vnd), `number price ${direction(quote)}`),
        element("td", delta === null ? "—" : `${delta > 0 ? "+" : ""}${money.format(delta)}`, `number ${direction(quote)}`),
        changeCell, timestamp, source, action);
      fragment.append(row);
    }
    if (!quotes.length) {
      const row = document.createElement("tr");
      const empty = element("td", "No quotes yet");
      empty.colSpan = 8;
      row.append(empty);
      fragment.append(row);
    }
    rows.replaceChildren(fragment);
    if (focusedAction) {
      [...rows.querySelectorAll("a")].find(a => a.getAttribute("aria-label") === focusedAction)?.focus({preventScroll: true});
    }
    document.getElementById("instrument-total").textContent = `${quotes.length} symbols`;
    document.getElementById("symbol-count").textContent = `${quotes.length} symbols · VND`;
    document.getElementById("data-notice").textContent = quotes.some(q => q.source === "simulation")
      ? "Simulation / generated · Scenario reference prices, not live DNSE data."
      : quotes.some(q => q.source === "dnse")
      ? "DNSE market data · Last received prices. Check timestamps and sources; some rows may still contain demo data. No real money or market orders."
      : "Demo data · Seeded example prices, not live DNSE quotes. No real money or market orders.";
    updateBoards(quotes);
    previousPrices = new Map(quotes.map(quote => [quote.symbol, quote.price_vnd]));
  }

  function updateBoards(quotes) {
    const strip = document.getElementById("ticker-strip");
    const focusedTile = strip.contains(document.activeElement) ? document.activeElement.getAttribute("aria-label") : null;
    const tiles = quotes.slice(0, 6).map(quote => {
      const tile = element("a", "", "ticker-tile");
      tile.href = `/trade?symbol=${encodeURIComponent(quote.symbol)}`;
      tile.setAttribute("aria-label", `Preview ${quote.symbol}`);
      const title = element("span", quote.symbol);
      title.append(element("small", sourceName(quote)));
      tile.append(title, element("strong", money.format(quote.price_vnd), direction(quote)),
        element("small", quote.change === null ? "Reference unavailable" :
          `${Number(quote.change) > 0 ? "+" : ""}${quote.change}%`, direction(quote)));
      return tile;
    });
    strip.replaceChildren(...tiles);
    if (focusedTile) tiles.find(tile => tile.getAttribute("aria-label") === focusedTile)?.focus({preventScroll: true});

    const counts = {positive: 0, negative: 0, neutral: 0, unclassified: 0};
    for (const quote of quotes) counts[direction(quote)]++;
    document.getElementById("breadth-board").replaceChildren(...[
      ["positive", "Advancing"], ["negative", "Declining"], ["neutral", "Unchanged"], ["unclassified", "No reference"]
    ].map(([key, label]) => {
      const cell = element("div", "", `breadth-cell ${key}`);
      cell.append(element("strong", String(counts[key])), element("span", label));
      return cell;
    }));
    const monitored = quotes.filter(q => q.change !== null).sort((a, b) =>
      Math.abs(Number(b.change)) - Math.abs(Number(a.change))).slice(0, 5);
    const monitorRows = monitored.map(quote => {
      const row = document.createElement("tr");
      row.append(element("td", quote.symbol), element("td", money.format(quote.price_vnd), "number"),
        element("td", `${Number(quote.change) > 0 ? "+" : ""}${quote.change}%`, `number ${direction(quote)}`),
        element("td", sourceName(quote)));
      return row;
    });
    if (!monitorRows.length) {
      const row = document.createElement("tr"), cell = element("td", "No comparable quotes. Waiting for reference prices.");
      cell.colSpan = 4; row.append(cell); monitorRows.push(row);
    }
    document.getElementById("movement-rows").replaceChildren(...monitorRows);
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
  const initial = document.getElementById("initial-quotes");
  if (initial) {
    const quotes = JSON.parse(initial.textContent);
    updateBoards(quotes);
    previousPrices = new Map(quotes.map(quote => [quote.symbol, quote.price_vnd]));
  }
  setTimeout(refresh, 3000);
})();
