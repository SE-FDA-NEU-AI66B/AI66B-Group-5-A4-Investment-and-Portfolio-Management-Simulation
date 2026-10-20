/* Read-only stock discovery. Order prices are always revalidated by the server. */
(() => {
  const input = document.getElementById("symbol");
  const options = document.getElementById("stock-options");
  if (!input || !options) return;
  const status = document.getElementById("stock-picker-status");
  const retry = document.getElementById("retry-stocks");
  let quotes = [], matches = [], active = -1, loading = false, failed = false;
  const money = value => new Intl.NumberFormat("en-US").format(value) + " VND";
  const source = quote => quote.source === "dnse" ? "DNSE" :
    quote.source === "simulation" ? "Simulation / generated" : "Demo / seed";

  function close() {
    options.hidden = true;
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
    active = -1;
  }
  function showSelected() {
    const quote = quotes.find(q => q.symbol === input.value.trim().toUpperCase());
    document.getElementById("selected-stock").hidden = !quote;
    if (!quote) return;
    document.getElementById("selected-name").textContent = `${quote.symbol} · ${quote.name}`;
    document.getElementById("selected-price").textContent = money(quote.price_vnd);
    document.getElementById("selected-source").textContent =
      `${source(quote)} · Snapshot only; preview for the current price.` +
      (quote.stale ? " Price may be delayed." : "");
  }
  function choose(quote) {
    if (input.disabled) return;
    input.value = quote.symbol;
    input.dispatchEvent(new Event("input", {bubbles: true}));
    close();
    input.focus();
    // Focus opens the list; keep selection closed until another interaction.
    close();
    status.textContent = `${quote.symbol} selected. Enter the number of shares.`;
  }
  function highlight(index) {
    active = index;
    for (const [i, node] of [...options.children].entries()) {
      node.setAttribute("aria-selected", String(i === active));
    }
    const node = options.children[active];
    if (node) {
      input.setAttribute("aria-activedescendant", node.id);
      node.scrollIntoView({block: "nearest"});
    } else input.removeAttribute("aria-activedescendant");
  }
  function render() {
    if (loading || failed || input.disabled) { close(); return; }
    const term = input.value.trim().toLowerCase();
    matches = quotes.filter(q => `${q.symbol} ${q.name}`.toLowerCase().includes(term));
    options.replaceChildren();
    active = -1;
    input.removeAttribute("aria-activedescendant");
    for (const [index, quote] of matches.entries()) {
      const item = document.createElement("div");
      item.className = "stock-option";
      item.id = `stock-option-${index}`;
      item.setAttribute("role", "option");
      item.setAttribute("aria-selected", "false");
      const symbol = document.createElement("strong");
      symbol.textContent = quote.symbol;
      const name = document.createElement("span");
      name.textContent = quote.name;
      const detail = document.createElement("small");
      detail.textContent = `${money(quote.price_vnd)} · ${source(quote)}`;
      item.append(symbol, name, detail);
      // Keep focus on the combobox for keyboard/assistive-technology users.
      item.addEventListener("mousedown", event => event.preventDefault());
      item.addEventListener("click", () => choose(quote));
      options.append(item);
    }
    options.hidden = !matches.length;
    input.setAttribute("aria-expanded", String(matches.length > 0));
    status.textContent = matches.length ? `${matches.length} stocks. Use arrow keys and Enter to select.` :
      quotes.length ? "No matching stocks. Try another symbol or company name." :
      "No stocks available yet. Retry the list or return to Market.";
    retry.hidden = quotes.length > 0;
  }
  async function load() {
    if (loading || input.disabled) return;
    loading = true; failed = false; retry.hidden = true; close();
    status.textContent = "Loading available stocks…";
    input.setAttribute("aria-busy", "true");
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    try {
      const response = await fetch("/api/market/quotes", {cache: "no-store", signal: controller.signal});
      const data = await response.json();
      if (!response.ok || !Array.isArray(data.quotes)) throw new Error("Unavailable");
      quotes = data.quotes;
      showSelected();
      status.textContent = quotes.length ? `${quotes.length} stocks available. Search by symbol or company.` :
        "No stocks available yet. Retry the list or return to Market.";
      retry.hidden = quotes.length > 0;
    } catch {
      failed = true;
      status.textContent = "Could not load stocks. Retry the list, or enter a known symbol from Market.";
      retry.hidden = false;
    } finally {
      clearTimeout(timeout); loading = false; input.setAttribute("aria-busy", "false");
      if (document.activeElement === input) render();
    }
  }
  input.addEventListener("focus", render);
  input.addEventListener("click", render);
  input.addEventListener("input", () => { showSelected(); render(); });
  input.addEventListener("keydown", event => {
    if (event.key === "Escape") { close(); return; }
    if (event.key === "Tab") { close(); return; }
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      if (options.hidden) render();
      if (matches.length && !options.hidden) {
        const down = event.key === "ArrowDown";
        highlight(active < 0 ? (down ? 0 : matches.length - 1) :
          (active + (down ? 1 : -1) + matches.length) % matches.length);
      }
    } else if (event.key === "Enter" && !options.hidden && active >= 0) {
      event.preventDefault(); choose(matches[active]);
    }
  });
  input.addEventListener("blur", close);
  // Confirming an order disables the field; close any open suggestions too.
  new MutationObserver(() => { if (input.disabled) close(); }).observe(input, {attributes: true, attributeFilter: ["disabled"]});
  retry.addEventListener("click", load);
  load();
})();
