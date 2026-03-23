# Price Plan Rules

Use this file when the user wants exact buy prices, stop-loss levels, target prices, or explicit buy and sell timing.

## Core Principle

Derive every price plan from verified Tonghuashun session data, not from guesswork.

Do not use the latest completed session in isolation. First read the relevant historical window, then interpret the latest session inside that larger structure.

Minimum inputs before giving exact numbers:

- latest completed-session open, high, low, and close from `today.js` or the local helper script
- previous trading session open, high, low, and close from `last.js`
- recent structure from `last.js`
- intraday path from `v6/time/.../defer/last.js` when short-term execution quality matters

If any of these are missing or inconsistent, downgrade to conditional trigger language instead of fake precision.

## Fixed Calculation Sequence

Always follow this order before writing `触发买价`, `止损价`, `第一目标`, or `第二目标`:

1. determine the horizon
2. pull the required historical window
3. identify the setup type
4. mark key structure levels from the historical window
5. use the latest completed session only as the anchor day
6. derive buy, stop, targets, and risk/reward
7. reject the setup if the structure is poor

Never skip from the latest completed session directly to exact price levels.

## Structure Checklist

Before setting levels, identify:

- latest completed-session close
- latest completed-session high and low
- previous trading session close
- recent 5-day high and low
- recent 20-day high and low for medium term
- recent 60-day or 6-12 month structure for long term
- whether the stock closed near the high, near the low, or in the middle of the range
- whether turnover and amount were expanding, stable, or fading

Required structure windows by horizon:

- short term: recent 5 sessions minimum, recent 10 preferred
- medium term: recent 20 sessions minimum, recent 60 preferred
- long term: recent 6 months minimum, recent 12 months preferred

## China A-Share Board Rules

Remember the board context before setting targets:

- main board names usually face a 10% daily price limit
- ChiNext and STAR names often face a 20% daily price limit
- `ST` or `*ST` names often face tighter limits and should normally be excluded by hard filters

Do not set targets that casually assume tradability beyond realistic board constraints.

If a stock was effectively locked at limit-up or limit-down, do not pretend that a normal exact entry or exit is executable.

## Short-Term Rules

Use for next trading day to roughly 5 trading days.

Preferred setup types:

1. breakout continuation
2. early pullback after a strong close
3. reclaim of a key level after an intraday washout

### Short-Term Buy Price

- `突破型`: price is near the recent 5-10 day high and turnover is expanding
- `回踩型`: price pulled back into a recent support area but the broader 5-10 day trend is still intact
- `趋势型`: price is above key short-term averages or close clusters and still respecting support

If the stock closed strong and near the high:

- set `触发买价` slightly above the latest completed-session close or high
- use a modest breakout buffer, usually about 0.2% to 1.0%

If the stock faded late but the broader trend is still intact:

- set `触发买价` as a reclaim zone above the latest completed-session close

If the stock is only suitable on pullback:

- set `触发买价` near the latest completed-session close to low support band
- mention a concrete time window such as `9:35-10:30`

### Short-Term Stop

Anchor `止损价` to the nearest invalidation level:

- usually the latest completed-session low
- or the lowest low in the recent 3-5 session support band

Do not set a stop so wide that the short-term setup accidentally becomes a medium-term trade.

### Short-Term Targets

Set `第一目标` to the nearest realistic resistance:

- recent 3-5 day swing high
- recent unfilled gap
- failed breakout area

Set `第二目标` to the next resistance step above `第一目标`.

### Short-Term Sell Timing

Use practical language such as:

- `次日冲高减仓`
- `达到第一目标先卖一半`
- `回封失败或跌破分时承接位离场`

## Medium-Term Rules

Use for roughly 2 to 12 weeks.

### Medium-Term Buy Price

Anchor `触发买价` to the latest completed-session close and the recent 20-60 session structure:

- prefer an accumulation or pullback zone near the latest close
- if the stock just broke out, use a retest zone rather than a far-above-market chase price
- a range is usually better than a single price

### Medium-Term Stop

Anchor `止损价` below:

- the recent 20-day swing low
- or the obvious base support zone

### Medium-Term Targets

Set `第一目标` to:

- the recent 20-60 day swing high
- or the first major resistance above the breakout area

Set `第二目标` to:

- a higher structural resistance level
- or a measured breakout extension if the trend is clean

### Medium-Term Sell Timing

Use review-based timing such as:

- `未来2-8周内到目标位分批兑现`
- `下一次财报前后复核`
- `若行业景气转弱则提前减仓`

## Long-Term Rules

Use for roughly 6 to 24 months.

### Long-Term Buy Price

Do not pretend a long-term trade has a tight single-tick entry.

Use:

- a staged entry zone around the latest completed-session close
- or a valuation-aware buy band built from the recent 6-12 month structure

### Long-Term Stop

Use a wider `止损价` or a thesis-break line tied to:

- major structural support
- or a clearly stated business-thesis failure condition

### Long-Term Targets

Set `第一目标` to a realistic re-rating level and `第二目标` to a stronger upside scenario.

Good anchors:

- prior yearly high
- valuation re-rating band
- earnings growth path over the next 6-24 months

### Long-Term Sell Timing

Use review windows rather than tight trading language:

- `半年报或年报后复核`
- `分红预案兑现后复核`
- `产业逻辑变化时复核`

## When To Downgrade

Do not output exact buy, stop, or target numbers when:

- the latest completed-session data cannot be verified
- Tonghuashun endpoints conflict materially and cannot be reconciled
- the stock was effectively untradable
- recent price structure is too chaotic to support a clean invalidation line
- the broader historical window conflicts with the apparent strength of the latest completed session

In these cases, switch to:

- conditional trigger language
- wider entry zones
- clear statements of what would invalidate the idea

## Output Style

When giving exact levels:

- tie the numbers to the latest completed-session date
- mention whether the entry is breakout-based, pullback-based, or staged
- explicitly output `形态类型`, `关键支撑`, and `关键阻力`
- compute `风险收益比` from `触发买价`, `止损价`, and `第一目标`
- make sure the proposed reward is meaningfully larger than the risk unless you explicitly note a lower-quality setup
