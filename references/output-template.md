# Output Template

Use this file when writing the final stock recommendations.

## Required Shape

If the user explicitly asks for only one horizon, output only that horizon.

Otherwise provide three sections:

1. Short-term picks
2. Medium-term picks
3. Long-term picks

If capital or holdings context exists, add a short `资金与仓位前提` block before the first section.

Each section must start with a table in this exact column order:

`股票 | 上个交易日开盘价 | 上个交易日收盘价 | 形态类型 | 关键支撑 | 关键阻力 | 核心逻辑 | 买入时间 | 触发买价 | 止损价 | 第一目标 | 第二目标 | 风险收益比 | 卖出时间 | 持有周期 | 不买条件`

Use this Markdown table skeleton:

```markdown
| 股票 | 上个交易日开盘价 | 上个交易日收盘价 | 形态类型 | 关键支撑 | 关键阻力 | 核心逻辑 | 买入时间 | 触发买价 | 止损价 | 第一目标 | 第二目标 | 风险收益比 | 卖出时间 | 持有周期 | 不买条件 |
|---|---:|---:|---|---:|---:|---|---|---:|---:|---:|---:|---|---|---|---|
| 示例股票 `000000` | 10.00 | 10.20 | 突破型 | 9.85 | 10.60 | 一句话说明逻辑 | 2026-03-20 9:35-10:30 | 10.22 | 9.84 | 10.60 | 11.00 | 1:2.1 | 第一目标减仓，第二目标再评估 | 1-3天 | 高开过猛且放量不续强则不买 |
```

## Column Guidance

- `股票`: ticker plus name
- `上个交易日开盘价`: the verified open of the latest completed session
- `上个交易日收盘价`: the verified close of the latest completed session
- `形态类型`: one of `突破型` `回踩型` `趋势型` `震荡低吸型`
- `关键支撑`: the main support level derived from the relevant historical window
- `关键阻力`: the nearest important resistance level derived from the relevant historical window
- `核心逻辑`: one short sentence
- `买入时间`: when the entry should be attempted
- `触发买价`: exact price or a clearly phrased conditional trigger
- `止损价`: exact stop for short/medium term, thesis-break condition or wider risk line for long term
- `第一目标`: realistic first target
- `第二目标`: stretch target
- `风险收益比`: a compact risk/reward summary such as `1:2.1`
- `卖出时间`: when profit-taking or review should happen
- `持有周期`: expected holding window
- `不买条件`: one short sentence explaining when to skip the trade

When exact levels are given, make sure they were derived from:

- Tonghuashun `today.js` for the latest completed-session anchor
- Tonghuashun `last.js` for previous-session and recent structure
- Tonghuashun `v6/time/.../defer/last.js` when short-term timing depends on intraday path

## Evidence Notes

After each table, add short notes for each stock:

- Policy/news/disclosure evidence
- Price/history evidence
- Why it beat other candidates
- Suggested lot count or max capital usage when the user has asked for executable ideas and capital is known

## Writing Rules

- Use exact dates whenever discussing the latest completed session or upcoming catalyst dates
- Keep the tables compact
- Keep evidence notes short but concrete
- Do not pad with weak names just to fill space
