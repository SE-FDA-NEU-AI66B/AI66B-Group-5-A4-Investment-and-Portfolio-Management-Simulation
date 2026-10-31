# Buy journey browser audit (Sprint 4, #116)

On 31 October 2026, `python scripts/check_buy_ui.py --evidence-dir <local-path>`
ran the real Buy page in headless Microsoft Edge at 1200 x 850 and 390 x 844.
Each scenario used a temporary SQLite database, real register/login/logout,
the simulation quote adapter and a disposable password. Both disconnect and
gateway-error runs passed. No DNSE key, provider request or authentication
bypass was used. The script is a repeatable browser regression check; Long's
independent clean-clone verification remains separate under #123.

| State | Observed UI | Evidence and next action |
|---|---|---|
| Empty | Stock picker, quantity hint and order placeholder are visible; Confirm buy is disabled. | [Empty form](images/m4/buy-empty.png). Choose a stock and enter a whole-share quantity. |
| Loading | `Loading preview...` is announced through `role=status`; Confirm buy stays disabled. | [Loading](images/m4/buy-loading.png). Wait for the read to finish. |
| Success | Preview shows quote source/time, available cash and cost. A confirmed Buy displays one receipt with updated cash and holding. | [Receipt](images/m4/buy-receipt.png). Review the quote and confirm once. |
| Error | Each failure is displayed in `role=alert`, with the form still available for safe corrections unless the Buy POST result is unknown. | See the specific recovery checks below. |

| Failure checked | Browser result and recovery |
|---|---|
| Invalid quantity (0, -1, 1.5) | Native validity and visible alert say whole shares of at least 1; Confirm buy stays disabled. Correct the quantity. |
| Insufficient cash | 4,000 HPG shows the exact 12,000,000 VND shortfall and disables confirmation. Reducing to 1,000 shares clears the warning and re-enables it. [Before](images/m4/buy-shortfall.png) / [after](images/m4/buy-corrected-preview.png); [mobile view](images/m4/buy-shortfall-mobile.png) has no horizontal overflow. |
| Stale quote | A stored quote aged 20 minutes receives the real server refusal. Generate fresh **simulation** quotes, then preview again. |
| Changed quote | Changing the stored quote timestamp after preview makes confirmation fail with `Price changed`; the database still has zero trades. Preview again before confirming. [Changed quote](images/m4/buy-quote-changed.png). |
| Unavailable quote | An intercepted `503 QUOTE_UNAVAILABLE` displays the server message plus a simulation recovery action; symbol/quantity remain and confirmation is disabled. Generate demo quotes or wait for a market quote, then preview again. [Unavailable quote](images/m4/buy-quote-unavailable.png). |
| Picker read failure | An intercepted quote-list failure offers **Retry stock list**. The typed symbol survives the retry, and ArrowDown/Enter selects an option while focus remains in the combobox. [Picker failure](images/m4/buy-picker-read-failure.png). |
| Preview read failure | An intercepted network abort preserves both inputs, disables confirmation and names the safe **Preview order** retry. Retrying the read restores a valid preview. |
| Unknown Buy POST result | The server commits one virtual trade, but the browser sees a disconnect or gateway 502. Both Preview and Confirm stay disabled; the alert says not to resubmit and directs the user to Portfolio/operator reconciliation. The temporary database contains exactly one additional trade, not a retry. [Unknown result](images/m4/buy-unknown-result.png). |

The browser script asserts no page errors, verifies the temporary database's
cash/holding/trade counts, and repeats the unknown-result case for both a
disconnect and a gateway response. Quote-unavailable and read-failure responses
are deliberately intercepted to exercise the UI; stale/changed quote failures
come from controlled temporary-database changes. These are author QA page
captures without browser chrome, not the independent SETUP run or final PDF.
