from scanner.strategy import Position, StrategyConfig, SymbolData, decide

CFG = StrategyConfig()


def _oversold_symbol(symbol: str) -> SymbolData:
    """Build a symbol that both drops >=4% today and has RSI < 30."""
    closes = [100.0] * 14 + [97.0, 94.0, 91.0, 88.0, 85.0]
    return SymbolData(
        symbol=symbol,
        current_price=85.0,
        prior_close=90.0,            # -5.6% on the day
        closes=closes,
    )


def _calm_symbol(symbol: str) -> SymbolData:
    closes = [float(100 + (i % 3)) for i in range(20)]
    return SymbolData(symbol=symbol, current_price=101.0, prior_close=100.5, closes=closes)


def test_entry_signal_sizes_at_ten_percent():
    d = decide(cash=1500.0, positions=[], market=[_oversold_symbol("AAPL")], cfg=CFG)
    assert len(d.buys) == 1
    assert d.buys[0].symbol == "AAPL"
    assert d.buys[0].dollar_amount == 150.0  # 10% of 1500


def test_no_signal_when_calm():
    d = decide(cash=1500.0, positions=[], market=[_calm_symbol("MSFT")], cfg=CFG)
    assert d.buys == []


def test_drop_without_oversold_rsi_is_skipped():
    # Big one-day drop but RSI healthy (long uptrend) -> no entry.
    closes = [float(80 + i) for i in range(20)]  # strong uptrend, high RSI
    sym = SymbolData("NVDA", current_price=95.0, prior_close=100.0, closes=closes)
    d = decide(cash=1500.0, positions=[], market=[sym], cfg=CFG)
    assert d.buys == []


def test_position_cap_blocks_sixth_entry():
    held = [
        Position(s, quantity=1.0, average_buy_price=100.0, current_price=100.0)
        for s in ("AAPL", "MSFT", "NVDA", "AMZN", "GOOGL")
    ]
    d = decide(cash=1500.0, positions=held, market=[_oversold_symbol("META")], cfg=CFG)
    assert d.buys == []
    assert any(s["reason"] == "position cap reached" for s in d.skipped)


def test_already_held_symbol_not_rebought():
    held = [Position("AAPL", quantity=0.5, average_buy_price=100.0, current_price=85.0)]
    d = decide(cash=1500.0, positions=held, market=[_oversold_symbol("AAPL")], cfg=CFG)
    assert all(b.symbol != "AAPL" for b in d.buys)


def test_software_stop_triggers_sell():
    held = [Position("AAPL", quantity=0.5, average_buy_price=100.0, current_price=91.0)]
    d = decide(cash=1500.0, positions=held, market=[], cfg=CFG)
    assert len(d.sells) == 1
    assert "software stop" in d.sells[0].reason


def test_take_profit_triggers_sell():
    held = [Position("MSFT", quantity=0.5, average_buy_price=100.0, current_price=110.0)]
    d = decide(cash=1500.0, positions=held, market=[], cfg=CFG)
    assert len(d.sells) == 1
    assert "take profit" in d.sells[0].reason


def test_non_watchlist_symbol_skipped():
    sym = _oversold_symbol("GME")  # not on the fixed watchlist
    d = decide(cash=1500.0, positions=[], market=[sym], cfg=CFG)
    assert d.buys == []
    assert any(s["reason"] == "not on watchlist" for s in d.skipped)


def test_zero_cash_blocks_entry():
    d = decide(cash=0.0, positions=[], market=[_oversold_symbol("AAPL")], cfg=CFG)
    assert d.buys == []
