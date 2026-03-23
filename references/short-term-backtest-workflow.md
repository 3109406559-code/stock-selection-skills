# Short-Term Backtest Workflow

Use this file when you need to validate the short-term rule with historical data instead of trusting the narrative alone.

## Goal

Check whether the skill's short-term breakout logic has shown reasonable behavior on recent A-share history.

## Local Script

Run:

```powershell
& ".\.venv\Scripts\python.exe" ".codex\skills\a-share-stock-picker\scripts\backtest_short_term_rule.py" 600519 --start-date 20250101 --end-date 20260322 --source auto --pretty
```

The script uses:

- `AkShare stock_zh_a_hist` when available
- Tonghuashun `last.js` as the fallback history source when AkShare history fails
- `backtrader` for order simulation

## Rule Being Tested

The minimal rule is a short-term breakout confirmation rule:

- breakout above the prior `5`-day high
- same-day volume above the recent `5`-day average by a multiplier
- close positioned in the upper part of the day's range
- bullish body confirmation
- stop anchored to the recent `3`-day support low
- first target built from a `2.0` risk-reward multiple
- forced time exit after `3` bars if neither stop nor target hit

## How To Use The Result

Use the backtest output as a confidence check, not as proof.

Look at:

- total closed trades
- win rate
- total return
- max drawdown
- the tail of the trade log

If the sample size is tiny or the drawdown is poor, do not overstate confidence in the short-term recommendation.

## Important Limits

- This is a minimal validation harness, not an institutional research framework
- it uses daily bars, so intraday fill quality is approximated
- it tests one rule family, not the full qualitative stock-selection process
- results can change materially with ticker, window, and board regime
