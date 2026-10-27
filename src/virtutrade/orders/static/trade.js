/* Never retry order POSTs automatically; uncertain results require reconciliation. */
(() => {
  const byId = id => document.getElementById(id);
  const form = byId("buy-form"), confirm = byId("confirm-button");
  if (!form) return;
  const sideMeta = document.querySelector('meta[name="order-side"]');
  const side = sideMeta && sideMeta.content === "sell" ? "sell" : "buy";
  const selling = side === "sell";
  let preview = null, generation = 0, timer, submitting = false, uncertain = false;
  const cash = n => new Intl.NumberFormat("en-US").format(n) + " VND";
  const quantityMessage = "Quantity must be a whole number of at least 1 share.";
  const quantityField = byId("quantity");
  const input = () => ({symbol: byId("symbol").value.trim().toUpperCase(), quantity: Number(byId("quantity").value)});
  const validQuantity = x => Number.isSafeInteger(x.quantity) && x.quantity > 0;
  const valid = x => x.symbol && validQuantity(x);
  const invalidate = () => { preview = null; confirm.disabled = true; generation++; };
  function showEstimate(data) {
    const estimate = byId("estimate");
    const lines = document.createElement("dl");
    lines.className = "preview-lines";
    const values = [
      ["Stock", data.symbol], ["Quantity", `${data.quantity.toLocaleString("en-US")} shares`],
      ["Price per share", cash(data.quote.price_vnd)], ["Available cash", cash(data.cash_vnd)],
      [selling ? "Estimated proceeds" : "Estimated cost", cash(data.estimate_vnd)],
      [selling ? "Shares held" : data.shortfall_vnd ? "Shortfall" : "Cash after purchase", selling ? data.available_quantity.toLocaleString("en-US") : cash(data.shortfall_vnd || data.cash_vnd - data.estimate_vnd)]
    ];
    for (const [label, value] of values) {
      const row = document.createElement("div");
      row.className = "preview-line" + ((label === "Estimated cost" || label === "Estimated proceeds") ? " total" : "");
      const term = document.createElement("dt"), description = document.createElement("dd");
      term.textContent = label; description.textContent = value;
      row.append(term, description); lines.append(row);
    }
    const note = document.createElement("p");
    note.className = "quote-note";
    note.textContent = `Quote: ${data.quote.quoted_at} (${data.quote.source}). The server checks this quote again when you confirm.`;
    estimate.replaceChildren(lines, note);
    byId("preview-placeholder").hidden = true;
    estimate.hidden = false;
  }
  async function request(url, body) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch(url, {method:"POST", cache:"no-store", signal:controller.signal,
        headers:{"Content-Type":"application/json", "X-CSRF-Token":document.querySelector('meta[name="csrf-token"]').content},
        body:JSON.stringify(body)});
      const data = await response.json();
      if (!response.ok) {
        const hints = {AUTH_REQUIRED:" Sign in again, then return to trade.", CSRF_FAILED:" Reload the form before trying again.", ACCOUNT_DISABLED:" Contact the project operator."};
        const e = new Error((data.error?.message || "Request rejected. Reload the form and try again.") + (hints[data.error?.code] || ""));
        // A server/proxy 5xx may follow a commit; treat the result as uncertain.
        e.rejected = response.status < 500; throw e;
      }
      return data;
    } finally { clearTimeout(timeout); }
  }
  function orderCopy(data) {
    if (selling) {
      const holding = data.holding ? `Remaining holding: ${data.holding.quantity} shares; cost basis: ${cash(data.holding.cost_basis_vnd)}.` : "Holding fully sold.";
      return `Sold ${data.trade.quantity} ${data.trade.symbol} for ${cash(data.trade.fill_price_vnd * data.trade.quantity)}. Realised P&L: ${cash(data.trade.realised_pnl_vnd)}. Cash now: ${cash(data.cash_vnd)}. ${holding} Order #${data.trade.id}.`;
    }
    return `Bought ${data.trade.quantity} ${data.trade.symbol}. Cash remaining: ${cash(data.cash_vnd)}. Holding: ${data.holding.quantity} shares; cost basis: ${cash(data.holding.cost_basis_vnd)}. Order #${data.trade.id}.`;
  }
  async function refreshPreview() {
    invalidate();
    if (submitting || uncertain || byId("preview-button").disabled) return;
    const x = input(), sequence = generation;
    byId("estimate").hidden = true;
    byId("preview-placeholder").hidden = false;
    byId("result").textContent = "";
    byId("order-error").textContent = "";
    if (!valid(x)) {
      byId("order-error").textContent = !validQuantity(x) ? quantityMessage : "Choose a stock from Market.";
      byId("order-status").textContent = "Correct the input, then preview again.";
      return;
    }
    byId("order-status").textContent = "Loading preview…";
    try {
      const data = await request("/api/orders/preview", {side, ...x});
      if (sequence !== generation) return;
      preview = {input:x, data};
      showEstimate(data);
      byId("order-error").textContent = data.warning || "";
      byId("order-status").textContent = data.can_submit ? "Check the quote, then confirm." : "Adjust the quantity to continue.";
      confirm.disabled = !data.can_submit;
    } catch (e) {
      if (sequence === generation) {
        byId("order-error").textContent = e.rejected ? e.message : "Could not load a preview. Your stock and quantity are saved; select Preview order to retry.";
        byId("order-status").textContent = "Preview unavailable. Review the message below.";
      }
    }
  }
  form.addEventListener("input", event => {
    if (event.target === quantityField) {
      quantityField.setCustomValidity(validQuantity(input()) ? "" : quantityMessage);
    }
    invalidate();
    byId("order-error").textContent = "";
    byId("result").textContent = "";
    clearTimeout(timer); timer = setTimeout(refreshPreview, 300);
  });
  quantityField.addEventListener("invalid", () => {
    quantityField.setCustomValidity(validQuantity(input()) ? "" : quantityMessage);
    invalidate();
    byId("estimate").hidden = true;
    byId("order-error").textContent = quantityMessage;
    byId("order-status").textContent = "Correct the input, then preview again.";
  });
  form.addEventListener("submit", e => { e.preventDefault(); clearTimeout(timer); refreshPreview(); });
  confirm.addEventListener("click", async () => {
    if (!preview || submitting || uncertain || confirm.disabled) return;
    const accepted = preview; invalidate(); submitting = true;
    for (const element of form.elements) element.disabled = true;
    byId("order-error").textContent = "";
    byId("result").textContent = "";
    byId("order-status").textContent = "Submitting virtual order…";
    try {
      const result = await request("/api/orders/" + side, {...accepted.input, expected_quote_at:accepted.data.quote.quoted_at});
      byId("estimate").hidden = true;
      byId("result").textContent = orderCopy(result);
      byId("order-status").textContent = "Order completed. Preview again before another order.";
    } catch (e) {
      uncertain = !e.rejected;
      byId("order-error").textContent = e.rejected ? e.message : "Order result is unknown. Do not submit again; check your portfolio or contact the operator before trading again.";
      byId("order-status").textContent = e.rejected
        ? "Order was not placed. Review the message, then preview again."
        : "Order result unknown. Do not submit again.";
      if (e.rejected) byId("estimate").hidden = true;
    } finally {
      submitting = false;
      for (const element of form.elements) element.disabled = uncertain;
      confirm.disabled = true;
    }
  });
  byId("generate-quotes").addEventListener("click", async () => {
    if (submitting || uncertain) return;
    invalidate();
    const button = byId("generate-quotes"); button.disabled = true;
    try {
      await request("/api/simulation/quotes/refresh", {});
      byId("order-status").textContent = "New simulation quotes generated. Preview again before confirming.";
      await refreshPreview();
    } catch (e) { byId("order-error").textContent = e.rejected ? e.message : "Could not confirm quote refresh. Return to Market and check its timestamp."; }
    finally { button.disabled = false; }
  });
  // Restore a preview if fields were filled before deferred scripts attached.
  if (valid(input())) refreshPreview();
})();
