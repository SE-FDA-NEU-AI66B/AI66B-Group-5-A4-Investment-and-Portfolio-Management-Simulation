# Buy UI evidence — 20 October 2026

Issue #76, owner @bianh13. Runtime/test revision `c6c78bd`, based on main
`46d6a7b`. Author QA on Windows, Python 3.10, Playwright 1.63.0 and headless
Microsoft Edge; each scenario creates a fresh temporary SQLite database and
uses real registration, cookie sessions and CSRF. No auth callbacks are replaced.

## Observed journeys

Both disconnect and gateway-response scenarios passed. The only direct page
navigation is the documented home URL; subsequent navigation uses visible links.

| Step | Observed result | Evidence |
|------|-----------------|----------|
| Home → Market → Buy as guest | Preview disabled; Register/Login available | [Guest guard](images/ui/buy-2026-10-20/buy-disconnect-guest-guard.png) |
| Register → Market → Buy, 4,000 HPG | 12,000,000 VND shortfall; correction guidance; confirm disabled | [Shortfall](images/ui/buy-2026-10-20/buy-disconnect-shortfall.png) |
| Correct to 1,000 → Confirm | 28,000,000 VND purchase; cash 72,000,000; holding 1,000; old estimate hidden | [Receipt](images/ui/buy-2026-10-20/buy-disconnect-receipt.png) |
| Age the temporary quote by 20 minutes → Preview | Actual server rejection; exact recovery message; no stuck loading status | [Stale quote](images/ui/buy-2026-10-20/buy-disconnect-stale-quote.png) |
| Generate demo quotes | Preview recovers and confirmation becomes available |
| Market → Logout → Login → Buy | Cash remains 72,000,000; no repeated initial grant |
| Confirm one more share, lose response after server commit | Form locks, no automatic retry, explicit unknown-result guidance | [Disconnect](images/ui/buy-2026-10-20/buy-disconnect-unknown-result.png), [HTTP 502](images/ui/buy-2026-10-20/buy-gateway-unknown-result.png) |

After each complete scenario, direct SQLite assertions confirm exactly two
trades, 71,972,000 VND cash and 1,001 held shares. The stale quote is an explicit
test fixture in that temporary database, not a provider observation. The second
purchase really commits before the response is dropped/replaced.

Machine-readable observations: [disconnect](images/ui/buy-2026-10-20/buy-disconnect.json)
and [gateway](images/ui/buy-2026-10-20/buy-gateway.json). Timestamps are UTC;
the runs occurred on 20 October in UTC+7. The captures were visually inspected.

## Reproduce

Follow SETUP, install the optional `playwright==1.63.0` QA dependency and use
Windows with Microsoft Edge installed, then run:

```text
python scripts/check_buy_ui.py --evidence-dir docs/images/ui/buy-local-check
```

The command creates isolated temporary state and a random disposable password;
it does not print credentials, touch the configured database or call DNSE.
Without `--evidence-dir`, the same behavioral checks run without saving images.

## Acceptance boundary

These are author page captures, without browser chrome or an address bar.
They do not satisfy the PDF page-3 screenshot requirement (#88), independent
machine verification (#83), independent review or the complete P0 audit (#82).
The real Portfolio screen/transition still depends on #81. #76 must remain
open until its recorded complete-journey handoff is verified and reviewed;
US04/US10 remain partly works. No extra story points are created for this fix.
