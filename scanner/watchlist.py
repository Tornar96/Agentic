"""Fixed watchlist for the swing scanner.

The protocol says "top 20 holdings of the S&P 500". To satisfy the
"do not hallucinate external data" rule we pin an explicit, hand-maintained
list of large-cap common stocks rather than inferring index weights at
runtime. No leveraged ETFs, no penny stocks. Edit deliberately.
"""

# 20 large, liquid S&P 500 common stocks (no leveraged ETFs, no penny stocks).
WATCHLIST: tuple[str, ...] = (
    "AAPL",
    "MSFT",
    "NVDA",
    "AMZN",
    "GOOGL",
    "META",
    "AVGO",
    "TSLA",
    "JPM",
    "LLY",
    "V",
    "XOM",
    "UNH",
    "MA",
    "COST",
    "JNJ",
    "HD",
    "PG",
    "WMT",
    "ORCL",
)

# Symbols that must never be traded by this routine, regardless of signal.
DENYLIST: frozenset[str] = frozenset()


def is_tradable(symbol: str) -> bool:
    """Return True if the symbol is on the watchlist and not denied."""
    return symbol in WATCHLIST and symbol not in DENYLIST
