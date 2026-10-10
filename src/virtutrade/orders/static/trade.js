/* Never retry order POSTs automatically; uncertain results require reconciliation. */
(() => {
  const byId = id => document.getElementById(id);
  const form = byId("buy-form"), confirm = byId("confirm-button");
  if (!form) return;
  let preview = null, generation = 0, timer, submitting = false, uncertain = false;
  const cash = n => new Intl.NumberFormat("en-US").format(n) + " VND";
  const input = () => ({symbol: byId("symbol").value.trim().toUpperCase(), quantity: Number(byId("quantity").value)});
  const valid = x => x.symbol && Number.isSafeInteger(x.quantity) && x.quantity > 0;
  const invalidate = () => { preview = null; confirm.disabled = true; generation++; };
  async function request(url, body) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch(url, {method:"POST", cache:"no-store", signal:controller.signal,
        headers:{"Content-Type":"application/json", "X-CSRF-Token":document.querySelector('meta[name="csrf-token"]').content},
        body:JSON.stringify(body)});
      const data = await response.json();
      if (!response.ok) { const e = new Error(data.error?.message || "Request rejected. Reload the form and try again."); e.rejected = true; throw e; }
      return data;
    } finally { clearTimeout(timeout); }
  }
  async function refreshPreview() {
    invalidate();
    if (submitting || uncertain || byId("preview-button").disabled) return;
    const x = input(), sequence = generation;
    byId("estimate").hidden = true; byId("order-error").textContent = "";
    if (!valid(x)) { byId("order-status").textContent = "Enter a symbol and a whole number of at least 1 share."; return; }
    byId("order-status").textContent = "Loading preview…";
    try {
      const data = await request("/api/orders/preview", {side:"buy", ...x});
      if (sequence !== generation) return;
      preview = {input:x, data};
      byId("estimate").textContent = `Estimated cost: ${cash(data.estimate_vnd)}. Available cash: ${cash(data.cash_vnd)}. Quote: ${data.quote.quoted_at} (${data.quote.source}).`;
      byId("estimate").hidden = false;
      byId("order-error").textContent = data.warning || "";
      byId("order-status").textContent = data.can_submit ? "Check the quote, then confirm." : "Adjust the quantity to continue.";
      confirm.disabled = !data.can_submit;
    } catch (e) { if (sequence === generation) byId("order-error").textContent = e.rejected ? e.message : "Could not load a preview. Try Preview order again."; }
  }
  form.addEventListener("input", () => { invalidate(); clearTimeout(timer); timer = setTimeout(refreshPreview, 300); });
  form.addEventListener("submit", e => { e.preventDefault(); clearTimeout(timer); refreshPreview(); });
  confirm.addEventListener("click", async () => {
    if (!preview || submitting || uncertain || confirm.disabled) return;
    const accepted = preview; invalidate(); submitting = true;
    for (const element of form.elements) element.disabled = true;
    byId("order-status").textContent = "Submitting virtual order…";
    try {
      const result = await request("/api/orders/buy", {...accepted.input, expected_quote_at:accepted.data.quote.quoted_at});
      byId("result").textContent = `Bought ${result.trade.quantity} ${result.trade.symbol}. Cash remaining: ${cash(result.cash_vnd)}. Order #${result.trade.id}.`;
      byId("order-status").textContent = "Order completed. Preview again before another purchase.";
    } catch (e) {
      uncertain = !e.rejected;
      byId("order-error").textContent = e.rejected ? e.message : "Order result is unknown. Do not submit again; check your portfolio or contact the operator before making another purchase.";
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
})();
