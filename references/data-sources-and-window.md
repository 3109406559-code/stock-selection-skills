# Data Sources And Window

Use this file when collecting price anchors, history, and timing context for the A-share stock picker.

## Default Window

This skill is built for:

- previous trading day close
- overnight policy, company, and macro news
- up to the next trading day open

Treat the latest completed session as the primary price anchor.

## Preferred Local Entry Point

If the helper script exists locally, use it first:

```powershell
& ".\.venv\Scripts\python.exe" ".codex\skills\a-share-stock-picker\scripts\fetch_a_share_data.py" 600519 --days 120 --include-intraday --pretty
```

Use the script to fetch:

- latest completed-session open, high, low, close
- previous session open and close
- recent 5/10/20/60/120-session structure
- latest minute-path summary
- AkShare cross-check rows from `stock_zh_a_hist`
- AkShare individual company metadata from `stock_individual_info_em`
- AkShare next-trading-date context from `tool_trade_date_hist_sina`
- hard-filter warnings
- merged anchor-session structure after the cash close when `today.js` is newer than `last.js`

If Tonghuashun and AkShare agree on the latest session, confidence is higher. If they disagree, trust Tonghuashun as the primary anchor for this skill, then explicitly mention the discrepancy and the exact date.

## Source Priority

For A-shares, collect data in this order:

1. local helper script output
2. Tonghuashun machine-readable K-line and time-series endpoints
3. AkShare daily history, company metadata, and trading calendar helpers
4. Tonghuashun stock, quote, concept, industry, and market pages
5. official exchange or company disclosures
6. official policy releases
7. reputable financial media for context

Primary Tonghuashun entry points:

- `https://d.10jqka.com.cn/v2/line/<market>_<ticker>/01/today.js`
- `https://d.10jqka.com.cn/v2/line/<market>_<ticker>/01/last.js`
- `https://d.10jqka.com.cn/v6/time/hs_<ticker>/defer/last.js`
- `https://stockpage.10jqka.com.cn/<ticker>/`
- `https://basic.10jqka.com.cn/<ticker>/`
- `https://q.10jqka.com.cn/`

Market code mapping used by this skill:

- `sh_<ticker>` for Shanghai A-shares
- `sz_<ticker>` for Shenzhen A-shares
- `hs_<ticker>` for Tonghuashun time-series endpoints

## Required Data Pull

For every final candidate, proactively retrieve:

- previous trading session open
- previous trading session close
- latest completed-session open
- latest completed-session close
- the relevant historical window, not just the anchor day
- recent highs and lows
- turnover and amount
- sector or concept strength
- one catalyst from policy, news, or company events
- one official disclosure when available

Minimum history windows:

- short term: at least 5 sessions, preferably 10
- medium term: at least 20 sessions, preferably 60
- long term: at least 6 months, preferably 12 months

Do not use user-supplied prices as the source of truth.

## Freshness Rules

- short-term exact prices must be anchored to the latest completed session
- medium-term exact prices must be anchored to the latest completed session plus recent 20-60 session structure
- long-term entry zones must be anchored to recent 6-12 month valuation and price context
- if `today.js` is available, use it as the price anchor for the latest completed session
- after the cash close, make sure the structure windows include the just-finished session rather than stopping one trading day earlier
- if `last.js` contains a trailing incomplete or synthetic row, ignore it
- if the machine-readable endpoint and visible HTML disagree, trust the machine-readable endpoint first and mention the exact date
- use `v6/time/.../defer/last.js` only to confirm short-term execution quality, not as the sole source of daily OHLC

If the latest verified price is stale or inconsistent, switch to conditional language instead of fake precision.
