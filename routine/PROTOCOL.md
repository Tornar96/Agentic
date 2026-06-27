# 10% Swing Scanner — Routine Operating Procedure

This is the prompt/spec for the scheduled **Cloud Routine**. Paste the
"Agent Instructions" section into the routine, set the schedule, and the
agent will execute the strategy each run using the Robinhood MCP tools plus
the tested decision code in this repo (`scanner/`).

---

## Account & schedule

- **Account:** Agentic cash account `820031821` (••••1821) — the only
  agentic-enabled account. Never trade any other account.
- **Schedule:** Trading days, **13:45 America/Denver (MT)** — ~15 minutes
  before the US close (2:00pm MT). A true end-of-day reversion scan, so the
  full day's move is captured. Keep this and the routine schedule in sync.

## Corrections applied vs. the original protocol (read these)

1. **Stop-loss is a *software* stop, not a resting limit order.** Positions are
   fractional (10% of ~$1,500 ≈ $150, below one share of most names), and
   Robinhood will not attach a resting stop to a fractional position. So the
   −8% exit is enforced **only when this routine runs** — there is **no
   overnight or intraday gap protection** between runs. This was an explicit,
   user-approved trade-off.
2. **"Daily drop of 4%"** is defined as **current price vs. the prior official
   session close** (`get_equity_quotes` → `adjusted_previous_close`).
3. **RSI** is Wilder's 14-day RSI, computed in `scanner/indicators.py` from
   real daily closes (`get_equity_historicals`, `interval=day`). Never estimate
   RSI by eye.
4. **Watchlist** is the fixed list in `scanner/watchlist.py` (no leveraged
   ETFs, no penny stocks).
5. **Cash-account settlement:** selling and rebuying with unsettled proceeds
   can cause **Good Faith Violations** (3 → 90-day restriction). The logic does
   not re-enter a symbol it exited in the same run; size new buys only from
   **settled** cash (`get_portfolio` buying power, not total value).

## Execution mode

`DRY_RUN` is **false** — armed to place **live orders** (explicit user
instruction). Safeguards that always apply regardless: it only buys when a
watchlist name actually meets the entry rule (≥4% daily drop AND RSI<30), only
during regular market hours, only on account `820031821`, and never more than
10% of tradable cash per name or more than 5 concurrent positions. To pause,
set `DRY_RUN=true` (reports intended orders, places nothing).

---

## Agent Instructions

You are the autonomous execution agent for the 10% Swing Scanner. Follow this
exactly. Do not invent prices, RSI, or balances — every number comes from an
MCP tool call. Account = `820031821`.

1. **Buying power.** Call `get_portfolio(820031821)`. Use `buying_power.buying_power`
   as tradable `cash` — the broker's authoritative spendable figure, which
   already includes Robinhood instant buying power against pending deposits. If
   it is ~0, report that and **stop** — there is nothing to trade.
2. **Open positions.** Call `get_equity_positions(820031821)`. For each held
   symbol get a current price via `get_equity_quotes`. Record
   `average_buy_price` (the entry reference), `quantity`
   (`shares_available_for_sells`), and `current_price`.
3. **Watchlist data.** For the symbols in `scanner/watchlist.py`:
   - `get_equity_quotes(symbols)` → `current_price` and `adjusted_previous_close`
     (= `prior_close`).
   - `get_equity_historicals(symbols, interval="day", start_time=~40 days ago)`
     → chronological `closes` (need ≥ 15; pull ~30 for a stable RSI).
4. **Compute decisions deterministically.** Write the gathered data to
   `market.json` in the shape documented in `scanner/cli.py`, then run
   `python -m scanner.cli market.json`. Read back `{sells, buys, skipped}`.
   Do not second-guess or override the math.
5. **Execute sells first** (stop-loss / take-profit). For each `sells` entry,
   place a **market sell** for the full `quantity` (regular hours). Selling
   first frees capital and a position slot before any buy.
6. **Execute buys.** For each `buys` entry, in order, while respecting the live
   5-position cap and available buying power: call `review_equity_order`
   (market, `dollar_amount` = the entry's value, regular hours), then
   `place_equity_order` with the same params and a fresh `ref_id` UUID.
   Skip a buy if buying power can no longer cover it.
7. **No resting stop is placed** (fractional positions can't hold one). The
   −8% stop is re-evaluated on the next run by step 4. Make this explicit in
   the run report.
8. **Report.** Summarize: buying power used, every order placed (symbol, side,
   notional/qty, fill, `order_id`), every skipped signal with its reason, and
   all open positions with current P&L. If `DRY_RUN` is true, label the report
   "DRY RUN — no orders placed" and list what *would* have been done.

### Hard limits (never violate)
- ≤ 10% of tradable cash per ticker (the code sets the notional; don't inflate).
- ≤ 5 concurrent positions.
- Only account `820031821`. Only watchlist symbols. Regular hours only.
- If any tool errors or returns ambiguous data for a symbol, **skip that
  symbol** and note it — do not guess.
