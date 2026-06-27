"""Orchestration entrypoint for the swing scanner.

The routine agent gathers real data via the Robinhood MCP tools, writes it
to a JSON file in the shape below, then runs:

    python -m scanner.cli market.json

and reads the decisions JSON from stdout. This keeps all deterministic math
in tested code; the agent only does I/O (MCP fetch + order placement).

Input JSON shape:
{
  "cash": 1500.00,                     # settled tradable cash
  "positions": [
    {"symbol": "AAPL", "quantity": 0.5,
     "average_buy_price": 280.0, "current_price": 250.0}
  ],
  "market": [
    {"symbol": "AAPL", "current_price": 250.0, "prior_close": 281.0,
     "closes": [/* >= rsi_period+1 chronological daily closes */]}
  ]
}

Output JSON shape:
{"sells": [...], "buys": [...], "skipped": [...]}
"""

from __future__ import annotations

import json
import sys

from .strategy import Decisions, Position, StrategyConfig, SymbolData, decide


def _load(payload: dict) -> tuple[float, list[Position], list[SymbolData]]:
    cash = float(payload["cash"])
    positions = [
        Position(
            symbol=p["symbol"],
            quantity=float(p["quantity"]),
            average_buy_price=float(p["average_buy_price"]),
            current_price=float(p["current_price"]),
        )
        for p in payload.get("positions", [])
    ]
    market = [
        SymbolData(
            symbol=m["symbol"],
            current_price=float(m["current_price"]),
            prior_close=float(m["prior_close"]),
            closes=[float(c) for c in m["closes"]],
        )
        for m in payload.get("market", [])
    ]
    return cash, positions, market


def run(payload: dict, cfg: StrategyConfig = StrategyConfig()) -> Decisions:
    cash, positions, market = _load(payload)
    return decide(cash, positions, market, cfg)


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        with open(argv[1], "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    else:
        payload = json.load(sys.stdin)

    decisions = run(payload)
    json.dump(decisions.as_dict(), sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
