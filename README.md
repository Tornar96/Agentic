# 10% Swing Scanner

A daily mean-reversion swing-trading routine for a Robinhood **Agentic**
(MCP-enabled) cash account. It scans a fixed large-cap watchlist once per
trading day and buys names that are sharply oversold, with a software stop and
a take-profit exit.

> ⚠️ **Real money.** This routine can place live orders on account ••••1821.
> Read [Risks & limitations](#risks--limitations) before going live.

## Strategy

| Rule | Value |
| --- | --- |
| Watchlist | Fixed 20 large-cap S&P 500 common stocks (`scanner/watchlist.py`) |
| Entry | Daily drop ≥ **4%** (vs prior close) **AND** 14-day RSI **< 30** |
| Position size | **10%** of settled cash per ticker (fractional/notional buy) |
| Max positions | **5** concurrent |
| Stop loss | **−8%** software stop (enforced each run) |
| Take profit | **+10%** market sell |
| Scan time | Trading days, 08:00 America/Denver |

## Architecture

Deterministic math lives in tested code; the scheduled agent only does I/O.

```
Cloud Routine (agent)                     scanner/ (this repo)
─────────────────────                     ────────────────────
get_portfolio / quotes / historicals  ─▶  indicators.py  (RSI, daily % change)
        │  writes market.json              strategy.py    (signals, sizing, exits)
        ▼                                   watchlist.py   (fixed symbol list)
python -m scanner.cli market.json     ◀──  cli.py          (JSON in → decisions out)
        │  reads {sells, buys, skipped}
        ▼
review_equity_order / place_equity_order   (order placement stays in the agent)
```

- `scanner/` — pure, network-free decision logic (standard library only).
- `routine/PROTOCOL.md` — the operating procedure to paste into the Cloud
  Routine, including the exact MCP call sequence.
- `tests/` — unit tests for indicators and strategy.

## Run the logic locally

```bash
python -m scanner.cli market.json     # see scanner/cli.py for the input shape
python -m pytest tests/ -q            # 17 tests
```

## Risks & limitations

- **Software stop only — no gap protection.** Positions are fractional, and
  Robinhood will not attach a resting stop to a fractional position, so the
  −8% exit fires *only when the routine runs*. A large overnight or intraday
  move between runs is not protected. (User-approved trade-off.)
- **Cash-account settlement.** Proceeds settle T+1; reusing unsettled cash can
  cause Good Faith Violations (3 → 90-day restriction). Buys are sized from
  settled buying power, and a symbol exited in a run is not re-entered that run.
- **Funding.** As of setup the account's $1,500 was a *pending deposit*
  (~$0 tradable). Nothing trades until it settles.
- **DRY_RUN defaults to true.** First runs report intended orders without
  placing them; live trading requires an explicit switch. See
  `routine/PROTOCOL.md`.
- **Not financial advice.** A naive RSI/drop strategy can and will have losing
  trades; size and supervise accordingly.

## Going live

1. Confirm the deposit has settled (`get_portfolio` buying power > 0).
2. Paste the **Agent Instructions** from `routine/PROTOCOL.md` into the Cloud
   Routine and set the schedule.
3. Leave `DRY_RUN=true` for the first scheduled run; review the report.
4. Flip to live only when you're satisfied with what it intended to do.
