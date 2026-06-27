"""Decision logic for the 10% Swing Scanner.

Given the account cash, current open positions, and per-symbol market data,
produce a deterministic set of buy/sell actions that honor every hard risk
constraint in the protocol. This module does NOT place orders.

Risk constraints (zero exceptions):
  * Never allocate more than 10% of total account cash to a single ticker.
  * Hold at most 5 concurrent positions.
  * Software stop: exit a position down >= 8% from its fill price.
  * Take profit: exit a position up >= 10% from its fill price.

Entry rule (per watchlist symbol):
  * Daily drop of >= 4% (current price vs prior session close), AND
  * 14-day Wilder RSI < 30.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .indicators import daily_change_pct, rsi
from .watchlist import is_tradable


@dataclass(frozen=True)
class StrategyConfig:
    max_position_pct: float = 0.10        # 10% of cash per ticker
    max_positions: int = 5                # concurrent position cap
    drop_threshold: float = -0.04         # >= 4% daily drop
    rsi_threshold: float = 30.0           # RSI must be strictly below this
    rsi_period: int = 14
    stop_loss_pct: float = -0.08          # software stop at -8%
    take_profit_pct: float = 0.10         # take profit at +10%


@dataclass
class SymbolData:
    """Real market data for one watchlist symbol (from MCP tools)."""

    symbol: str
    current_price: float
    prior_close: float
    closes: list[float]                   # chronological daily closes, oldest first


@dataclass
class Position:
    """An open position on the account (from get_equity_positions + a quote)."""

    symbol: str
    quantity: float
    average_buy_price: float              # used as the entry/fill reference
    current_price: float

    @property
    def pnl_pct(self) -> float:
        if self.average_buy_price <= 0:
            return 0.0
        return (self.current_price - self.average_buy_price) / self.average_buy_price


@dataclass
class Action:
    action: str                           # "buy" or "sell"
    symbol: str
    reason: str
    dollar_amount: Optional[float] = None  # set for buys (notional)
    quantity: Optional[float] = None       # set for sells (full position)
    metrics: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        d = {"action": self.action, "symbol": self.symbol, "reason": self.reason}
        if self.dollar_amount is not None:
            d["dollar_amount"] = round(self.dollar_amount, 2)
        if self.quantity is not None:
            d["quantity"] = self.quantity
        if self.metrics:
            d["metrics"] = self.metrics
        return d


@dataclass
class Decisions:
    sells: list[Action] = field(default_factory=list)
    buys: list[Action] = field(default_factory=list)
    skipped: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "sells": [a.as_dict() for a in self.sells],
            "buys": [a.as_dict() for a in self.buys],
            "skipped": self.skipped,
        }


def _manage_positions(positions: list[Position], cfg: StrategyConfig) -> list[Action]:
    """Stop-loss and take-profit exits for currently held positions.

    Stop-loss is checked before take-profit so a position that has somehow
    crossed both bounds is exited defensively.
    """
    actions: list[Action] = []
    for p in positions:
        pnl = p.pnl_pct
        if pnl <= cfg.stop_loss_pct:
            actions.append(
                Action(
                    "sell", p.symbol,
                    reason=f"software stop: {pnl:+.2%} <= {cfg.stop_loss_pct:.0%}",
                    quantity=p.quantity,
                    metrics={"pnl_pct": round(pnl, 4)},
                )
            )
        elif pnl >= cfg.take_profit_pct:
            actions.append(
                Action(
                    "sell", p.symbol,
                    reason=f"take profit: {pnl:+.2%} >= {cfg.take_profit_pct:.0%}",
                    quantity=p.quantity,
                    metrics={"pnl_pct": round(pnl, 4)},
                )
            )
    return actions


def decide(
    cash: float,
    positions: list[Position],
    market: list[SymbolData],
    cfg: StrategyConfig = StrategyConfig(),
) -> Decisions:
    """Produce buy/sell decisions for one scan run.

    ``cash`` should be the *settled, tradable* cash balance. Position sizing
    is 10% of this value. Exits (stop-loss / take-profit) are always evaluated;
    new entries are gated by the concurrent-position cap and skip any symbol
    already held.
    """
    decisions = Decisions()

    # 1. Manage existing positions (exits) first — risk control precedes entry.
    exits = _manage_positions(positions, cfg)
    decisions.sells.extend(exits)

    held = {p.symbol for p in positions}
    # Symbols being exited this run free up a slot but we do NOT re-enter them
    # in the same run (avoid churn / good-faith-violation risk on a cash acct).
    exiting = {a.symbol for a in exits}
    open_after_exits = len(held) - len(exiting)
    notional = round(cash * cfg.max_position_pct, 2)

    # 2. Evaluate entries.
    for d in market:
        if not is_tradable(d.symbol):
            decisions.skipped.append({"symbol": d.symbol, "reason": "not on watchlist"})
            continue
        if d.symbol in held:
            decisions.skipped.append({"symbol": d.symbol, "reason": "already held"})
            continue

        try:
            change = daily_change_pct(d.current_price, d.prior_close)
            r = rsi(d.closes, cfg.rsi_period)
        except ValueError as exc:
            decisions.skipped.append({"symbol": d.symbol, "reason": f"data error: {exc}"})
            continue

        metrics = {"daily_change": round(change, 4), "rsi": round(r, 2)}
        oversold = change <= cfg.drop_threshold and r < cfg.rsi_threshold
        if not oversold:
            decisions.skipped.append(
                {"symbol": d.symbol, "reason": "no signal", "metrics": metrics}
            )
            continue

        # Signal present — apply capacity and capital gates.
        if open_after_exits >= cfg.max_positions:
            decisions.skipped.append(
                {"symbol": d.symbol, "reason": "position cap reached", "metrics": metrics}
            )
            continue
        if notional <= 0:
            decisions.skipped.append(
                {"symbol": d.symbol, "reason": "no tradable cash", "metrics": metrics}
            )
            continue

        decisions.buys.append(
            Action(
                "buy", d.symbol,
                reason=f"oversold: {change:+.2%} drop, RSI {r:.1f}",
                dollar_amount=notional,
                metrics=metrics,
            )
        )
        open_after_exits += 1

    return decisions
