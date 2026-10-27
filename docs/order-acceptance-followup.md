# Order acceptance clarification - #106 / #107

## Quote timing (#106)

The existing US05 example describes a quote movement **after** the sell was
submitted and filled. The reported reproduction moves the quote **between
preview and confirmation**. These are separate cases, so the clarified AC and
BR3 state both rather than changing the transaction to silently accept a
different observation.

- Preview does not place an order.
- Confirm revalidates the exact preview timestamp inside the transaction.
- A changed timestamp returns 409 `QUOTE_CHANGED` without changing cash,
  holdings or trades, even when the numeric price is the same.
- Preview again and explicitly confirm the new price to place the order.
- A tick after commit never rewrites the stored fill.

No sell backend behavior changes in this follow-up. This is the proposed
requirements clarification for the PO-assigned defect; independent review must
confirm it before merging and closing #106.
The client also clears its obsolete "Submitting" status and hides the rejected
estimate, so a failed confirmation clearly tells the user to preview again.
An ambiguous response still locks the form and never retries automatically.

## Quantity message (#107)

Zero, negative and fractional quantities now show the existing server message:
`Quantity must be a whole number of at least 1 share.`
The inline alert and native browser validity message agree, Confirm stays
disabled, and correcting the quantity clears custom validity so preview works.
The requirements and API example include the server's existing final period.

## Reproduce and evidence

Follow SETUP in simulation mode. For optional Windows/Edge browser QA with
`playwright==1.63.0` installed:

```text
python scripts/check_buy_ui.py --evidence-dir docs/images/ui/local-order-qa
python scripts/check_quote_change_ui.py --evidence-dir docs/images/ui/local-order-qa
pytest -q
ruff check .
```

The browser checks use real registration, CSRF, service calls and SQLite.
Only the quote change is injected directly into the disposable database to
make its timing reproducible. No provider is contacted; no auth is bypassed.
The changed sell receives a real HTTP 409 with unchanged money state, then
fills 1,000 HPG at 27,500 VND after a new preview, leaving 99,500,000 VND cash.
A subsequent quote change leaves that recorded fill unchanged.

- [Zero-share message](images/ui/order-acceptance-2026-10-20/buy-disconnect-zero-quantity.png)
- [Quote changed](images/ui/order-acceptance-2026-10-20/sell-quote-changed.png)
- [Re-preview and fill](images/ui/order-acceptance-2026-10-20/sell-repreview-filled.png)

These are author page captures. They do not replace #82's independent checks,
#83's independent-machine run or #88's required address-bar screenshots.

Validation on 20 October: **196 passed, 2 existing skips**; Ruff, JavaScript
syntax and whitespace checks pass. Both buy-browser response-loss scenarios
and the changed-quote sell browser scenario pass.
