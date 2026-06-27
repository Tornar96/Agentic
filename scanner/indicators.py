"""Technical indicators computed from real price history.

Pure functions, standard library only. Inputs are chronological lists of
daily closing prices (oldest first). These are fed from real OHLCV bars
returned by the Robinhood MCP `get_equity_historicals` tool.
"""

from __future__ import annotations

from typing import Sequence


def daily_change_pct(current_price: float, prior_close: float) -> float:
    """Fractional change of the current price vs. the prior session close.

    A 4% drop is returned as -0.04. ``prior_close`` must be positive.
    """
    if prior_close <= 0:
        raise ValueError("prior_close must be positive")
    return (current_price - prior_close) / prior_close


def rsi(closes: Sequence[float], period: int = 14) -> float:
    """Wilder's Relative Strength Index over ``closes``.

    Uses Wilder's smoothing (the standard RSI). Requires at least
    ``period + 1`` closes so there are ``period`` price changes to seed the
    first average. Returns a value in [0, 100].

    Edge cases:
      * No losses across the window  -> RSI 100 (maximally overbought).
      * No gains across the window   -> RSI 0   (maximally oversold).
    """
    if period < 1:
        raise ValueError("period must be >= 1")
    if len(closes) < period + 1:
        raise ValueError(
            f"need at least {period + 1} closes to compute RSI({period}), "
            f"got {len(closes)}"
        )

    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]

    # Seed: simple average of the first `period` gains/losses.
    gains = [d if d > 0 else 0.0 for d in deltas[:period]]
    losses = [-d if d < 0 else 0.0 for d in deltas[:period]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    # Wilder smoothing across the remaining deltas.
    for d in deltas[period:]:
        gain = d if d > 0 else 0.0
        loss = -d if d < 0 else 0.0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    if avg_gain == 0:
        return 0.0

    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))
