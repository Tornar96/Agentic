"""10% Swing Scanner — deterministic strategy logic.

This package contains the *pure*, testable decision logic for the daily
mean-reversion swing strategy. It performs no network I/O and never places
orders. Market data is fetched by the routine agent through the Robinhood
MCP tools and passed in; this package only computes indicators and decides
what *should* happen. Order placement stays in the agent/MCP layer.
"""

from .strategy import StrategyConfig, decide

__all__ = ["StrategyConfig", "decide"]
