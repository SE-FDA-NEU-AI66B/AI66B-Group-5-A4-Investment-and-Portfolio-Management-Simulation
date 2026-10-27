# Buy journey state audit (Sprint 4, #116)

This is a code-and-test audit of `/trade?side=buy` on 27 October. Browser
screenshots and keyboard checks remain to be attached before #116 closes.

| State | Current user-visible behavior | Recovery or next action |
|---|---|---|
| Empty | Stock picker and quantity hint invite a choice; summary explains what preview will show. | Choose a stock and enter at least one whole share. |
| Loading | Picker says “Loading available stocks”; summary says “Loading preview…” or “Submitting virtual order…”. | Wait; duplicate confirmation is disabled. |
| Success | Preview shows price, available cash, estimated cost, quote source/time; a confirmed order shows a receipt. | Review the quote before confirmation; preview again before another order. |
| Error | Invalid quantity, insufficient cash, stale/changed quote, unavailable quote, picker/read failure and rejected confirmation appear in `role=alert`. | Correct quantity, reduce shares, regenerate *simulation* quotes or wait for a new market quote, retry a safe preview/read. Unknown POST result explicitly forbids resubmission until reconciled. |

The branch clears the previous success receipt and error when a new preview or
confirmation begins, so an old success cannot appear beside a newly rejected
order. A preview read failure retains symbol and quantity and names the safe
retry action. Neither change replays a Buy POST. The regression tests in
`tests/test_buy_m4.py` cover invalid quantity, cash shortage/correction,
900/901-second quote freshness and no-write refusal in temporary SQLite.

The visible picker and quote-read errors still need a manual desktop/mobile
browser pass, especially keyboard focus and the disabled-confirm state after a
failed read. Mark #116 done only after that evidence and independent review.
