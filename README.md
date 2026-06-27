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
| Scan time | Trading days, 13:45 America/Denver (≈15 min before close) |

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
- **Funding.** The $1,500 shows as a pending deposit, but Robinhood instant
  buying power makes it spendable; the routine sizes from the broker's
  `buying_power` figure. Cash-account settlement still applies to sale
  *proceeds* (T+1), so rapid sell→rebuy can trigger Good Faith Violations.
- **DRY_RUN is false (armed live).** The routine places real orders when the
  entry rule fires during market hours. Set `DRY_RUN=true` to pause. See
  `routine/PROTOCOL.md`.
- **Not financial advice.** A naive RSI/drop strategy can and will have losing
  trades; size and supervise accordingly.

## Going live

1. In the app's **Routines** panel, create a routine and paste the **Agent
   Instructions** from `routine/PROTOCOL.md`.
2. Set the schedule to **13:45 America/Denver, trading days**.
3. It is armed live (`DRY_RUN=false`) — it will place real orders when a signal
   fires. Set `DRY_RUN=true` first if you'd rather start with a dry run.

> The scheduled trigger must be created in the app — there is no tool to create
> it programmatically, and each scheduled run is a fresh, independent agent that
> reads this repo's spec.
