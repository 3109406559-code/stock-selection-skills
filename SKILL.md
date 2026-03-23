---
name: a-share-stock-picker
description: Capital-aware mainland A-share recommendation, position management, and pre-open selection for the window between the previous trading day's close and the next trading day's open. Use when Codex needs to recommend short-term, medium-term, or long-term A-share ideas, manage an existing holding, estimate whether the user has enough capital for a board lot, or persist an approximate portfolio state in 股票日志. Trigger on requests such as "推荐股票", "选三只短线票", "我只有3000本金", "我今天满仓买了某只票", "明天该怎么操作", "按收盘后信息选股", or any request for A-share picks with buy/sell time, price, cash, or仓位.
---

# A-Share Stock Picker

## Overview

Recommend mainland A-shares for three horizons in one pass:

- 3 short-term picks
- 3 medium-term picks
- 3 long-term picks

Use the latest completed trading session as the price anchor, then add overnight information available before the answer is produced. Every final name must include clear entry timing, structure-aware buy levels or entry zones, risk controls, targets, and concise evidence.

Default scope:

- Mainland common A-shares only
- Focus on Shanghai and Shenzhen listings
- Do not recommend Hong Kong stocks, US equities, ETFs, LOFs, funds, bonds, or convertibles unless the user explicitly asks

This skill is also responsible for:

- tracking the user's approximate available cash, current holdings, and rough board-lot capacity
- refusing to pretend that an A-share is executable when one lot does not fit the user's deployable cash
- updating the persistent portfolio state under `股票日志/portfolio_state.json` whenever the user clearly states a buy, sell, full-position, partial-position, cash top-up, or cash withdrawal event

## Operating Window

This skill is optimized for:

- Start: after the previous trading day officially closes
- End: before the next trading day opens

Use exact dates when discussing the anchor session, catalyst dates, or the intended buy window. Do not leave timing ambiguous with only "today" or "tomorrow".

If the user asks during live trading hours, say clearly that the framework is optimized for the post-close to pre-open window and that intraday conclusions are provisional.

## Local Helper Scripts

If the local helper scripts exist, use them before manual parsing:

- `scripts/fetch_a_share_data.py`
- `scripts/backtest_short_term_rule.py`
- `scripts/portfolio_state.py`
- `scripts/smoke_test.py`
- `scripts/requirements.txt`

Preferred usage:

```powershell
& ".\.venv\Scripts\python.exe" ".codex\skills\a-share-stock-picker\scripts\fetch_a_share_data.py" 600519 --days 120 --include-intraday --pretty
```

Use `fetch_a_share_data.py` first whenever you need:

- latest completed-session open, high, low, close
- previous session open and close
- recent 5/10/20/60/120-session structure
- latest minute-path summary
- AkShare cross-check of the latest completed session
- AkShare trading-calendar context and basic company metadata
- a quick hard-filter sanity check

Use `backtest_short_term_rule.py` when you need to validate whether the current short-term breakout rule has worked on recent history before trusting it in the narrative answer.

Use `portfolio_state.py` whenever:

- the user mentions current本金, available cash, full-position, half-position, buy, sell, clear, or add-position events
- you need to decide whether one board lot is actually affordable
- you need to tell the user whether a new trade is executable given current仓位
- the user asks to write or refresh the stock log

Preferred usage:

```powershell
& ".\.venv\Scripts\python.exe" ".codex\skills\a-share-stock-picker\scripts\portfolio_state.py" show
& ".\.venv\Scripts\python.exe" ".codex\skills\a-share-stock-picker\scripts\portfolio_state.py" buy 000862 --price 8.27 --budget 3000 --date 2026-03-23 --estimated
```

If the project has a local virtual environment, prefer `D:\CODE\stock\.venv\Scripts\python.exe` so `akshare` and `backtrader` stay project-local rather than global.

If AkShare enrichment fails while Tonghuashun still works, continue with Tonghuashun as the primary source and explicitly note that AkShare degraded or timed out.

## Capital State And Logging

Before giving any capital-sensitive recommendation, load:

- `references/capital-and-position-management.md`

Default persistent state path:

- `股票日志/portfolio_state.json`

Rules:

- If the state file exists, read it first.
- If the state file is missing but the user has already stated capital or trades in this conversation, initialize an approximate state and mark the relevant transaction as estimated.
- Always distinguish exact facts from estimates when the fill price, share count, or remaining cash is uncertain.
- When a user says "满仓", "半仓", "卖了一半", "清仓", or similar, update the state file after you finish the analysis.
- When the user asks to write the stock log, write both the narrative log file and the persistent portfolio state if it changed.

## Workflow

### 0. Load capital context first

When the user mentions cash,持仓, or asks whether to add, switch, or open a new position:

1. read `股票日志/portfolio_state.json` with `scripts/portfolio_state.py show` if it exists
2. reconcile it with any newer user statement in the conversation
3. update the state file if the conversation clearly implies a new buy, sell, or cash change
4. compute executable lot size before recommending a specific stock

If the user has less deployable cash than one board lot for a candidate, say so directly and downgrade that name.

### 1. Confirm the scope

Default assumption:

- exactly 3 short-term picks
- exactly 3 medium-term picks
- exactly 3 long-term picks

But if the user explicitly asks for only one horizon, honor that exact scope instead of padding the other horizons.

Do not duplicate names across horizons by default. Reuse a name only if it is unusually strong and you explicitly justify the overlap.

### 2. Pull data proactively

Always fetch market data yourself. Do not rely on user-supplied prices as the source of truth.

Preferred order:

1. `scripts/fetch_a_share_data.py` when available
2. Tonghuashun machine-readable endpoints
3. AkShare for cross-checks, calendar context, and metadata
4. Tonghuashun stock pages for context
5. official exchange or company disclosures
6. official policy releases and reputable financial media

Core Tonghuashun endpoints:

- `https://d.10jqka.com.cn/v2/line/<market>_<ticker>/01/today.js`
- `https://d.10jqka.com.cn/v2/line/<market>_<ticker>/01/last.js`
- `https://d.10jqka.com.cn/v6/time/hs_<ticker>/defer/last.js`
- `https://stockpage.10jqka.com.cn/<ticker>/`
- `https://basic.10jqka.com.cn/<ticker>/`
- `https://q.10jqka.com.cn/`

Where:

- `<market>` is `sh` for Shanghai tickers and `sz` for Shenzhen tickers
- `<ticker>` is the 6-digit stock code

Minimum history windows:

- short term: at least 5 trading days, preferably 10
- medium term: at least 20 trading days, preferably 60
- long term: at least 6 months, preferably 12 months

Never base a recommendation on the latest completed session alone. The anchor day only matters in the context of recent structure.

### 3. Apply hard filters before scoring

Before ranking candidates, load:

- `references/universe-and-risk-filters.md`
- `references/trading-window-and-calendar.md`
- `references/capital-and-position-management.md`

At minimum, reject or downgrade:

- `ST` or `*ST` names
- suspended names
- delisting-risk situations
- one-word limit-up names that are not realistically tradable for a short-term plan
- names with insufficient history for the target horizon
- names where the latest verified data is stale or inconsistent
- names whose one-board-lot cost obviously exceeds the user's deployable cash when the user has asked for executable ideas rather than a watchlist

If the market environment is weak and you cannot justify 3 strong names for a horizon, say so instead of padding with low-quality ideas.

### 4. Build the evidence pack

For each candidate, collect evidence from three buckets:

1. price and market structure
2. policy, news, or company-specific catalysts
3. official disclosures or fundamentals

Every final pick should have at least:

- one price/volume reason
- one catalyst or event reason
- one structural or fundamental reason

### 5. Score by horizon

Use the horizon framework in:

- `references/horizon-selection-framework.md`

When the user wants exact buy, stop, or target levels, also load:

- `references/price-plan-rules.md`

When price-level math depends on exact recent structure, inspect the script output or raw endpoints again before writing numbers.

### 6. Produce exactly 9 picks

Default output:

- 3 short-term picks
- 3 medium-term picks
- 3 long-term picks

If you genuinely cannot support 3 high-quality names for a horizon, say that clearly and explain what evidence or tradability is missing.

When the user asked only for one horizon, produce exactly that horizon only.

## Output Standard

When capital context exists, start with a compact `资金与仓位前提` block containing:

- total equity estimate or latest known本金
- deployable cash estimate
- current open positions
- whether the output is `可执行新仓` or `仅观察名单`
- what assumptions are estimated rather than confirmed

Default multi-horizon order:

1. Short-term picks
2. Medium-term picks
3. Long-term picks

If the user asked only for short-term picks, output only the short-term section.

Each section should start with this compact Markdown table:

`股票 | 上个交易日开盘价 | 上个交易日收盘价 | 形态类型 | 关键支撑 | 关键阻力 | 核心逻辑 | 买入时间 | 触发买价 | 止损价 | 第一目标 | 第二目标 | 风险收益比 | 卖出时间 | 持有周期 | 不买条件`

```markdown
| 股票 | 上个交易日开盘价 | 上个交易日收盘价 | 形态类型 | 关键支撑 | 关键阻力 | 核心逻辑 | 买入时间 | 触发买价 | 止损价 | 第一目标 | 第二目标 | 风险收益比 | 卖出时间 | 持有周期 | 不买条件 |
|---|---:|---:|---|---:|---:|---|---|---:|---:|---:|---:|---|---|---|---|
| 示例股票 `000000` | 10.00 | 10.20 | 突破型 | 9.85 | 10.60 | 一句话说明逻辑 | 2026-03-20 9:35-10:30 | 10.22 | 9.84 | 10.60 | 11.00 | 1:2.1 | 第一目标减仓，第二目标再评估 | 1-3天 | 高开过猛且放量不续强则不买 |
```

Below each table, add short notes for every stock:

- why it was selected
- which policy, news, or disclosure mattered
- which price or history facts mattered
- why it beat nearby alternatives
- suggested lot size or max capital share when the user has asked for executable ideas and capital is known

## Price Rules

- Base exact price levels on the latest completed session plus recent history
- Include the previous trading session's open and close in every stock row
- Prefer `today.js` for the latest completed-session anchor
- Prefer `last.js` for previous-session and multi-session structure
- Use `v6/time/.../defer/last.js` only as a supplement for minute-path confirmation
- Never derive buy, stop, or target levels from same-day OHLC alone
- If the latest price is stale, inconsistent, or not realistically tradable, downgrade to conditional trigger language
- If the stock is limit-locked or otherwise effectively untradable, do not pretend an exact executable entry exists

## Buy And Sell Timing Rules

Use horizon-appropriate timing language:

- short term: next trading day opening session, early pullback, breakout confirmation, or next 1-3 trading days
- medium term: next 1-5 trading days for entry, next 2-12 weeks for exit or review
- long term: staged entry over the next 5-20 trading days, thesis review over 6-24 months

When giving exact levels, explain them as structure-based levels derived from verified session data, recent highs and lows, and turnover behavior rather than as guarantees.

## Reference Files

Load as needed:

- `references/capital-and-position-management.md` for资金、仓位、可执行手数、日志更新规则
- `references/data-sources-and-window.md` for source priority and operating window
- `references/horizon-selection-framework.md` for short, medium, and long scoring
- `references/price-plan-rules.md` for buy, stop, and target derivation
- `references/output-template.md` for the final answer format
- `references/universe-and-risk-filters.md` for A-share hard filters and exclusions
- `references/trading-window-and-calendar.md` for exact-date and live-session handling
- `references/short-term-backtest-workflow.md` for validating the short-term rule with backtrader
