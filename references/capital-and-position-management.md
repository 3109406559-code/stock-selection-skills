# Capital And Position Management

Use this file whenever the user mentions cash, holdings, position size, add-position, reduce-position, or asks whether a trade is executable.

## Persistent State

Default state path:

- `股票日志/portfolio_state.json`

Default helper:

```powershell
& ".\.venv\Scripts\python.exe" ".codex\skills\a-share-stock-picker\scripts\portfolio_state.py" show
```

Use the helper to:

- initialize starting cash
- record estimated or exact buys
- record estimated or exact sells
- show current available cash and market value

## Known Vs Estimated

If exact fill data is missing:

- estimate board-lot shares conservatively
- label the transaction as estimated
- state the assumption in the answer and the log

Do not present estimated cash or cost as confirmed facts.

## Small-Account Rules

### Under 5,000 CNY

- default to at most 1 active short-term position
- do not recommend a name if one board lot obviously does not fit the user's deployable cash
- prefer names where one board lot uses 40% to 85% of deployable cash
- if the user already has a position above roughly 70% of total equity, new ideas should default to watchlist-only unless the existing position is being reduced or closed

### 5,000 to 20,000 CNY

- default to at most 2 active short-term positions
- single-idea size usually 30% to 60% depending on conviction and correlation

### Above 20,000 CNY

- still avoid concentrated same-theme duplication unless explicitly requested

## Board-Lot Feasibility

For mainland A-shares, default board lot:

- buy: 100 shares minimum and in multiples of 100

Before saying a stock is "适合买", check:

1. one-lot cost at the planned trigger price
2. current deployable cash
3. whether the user already holds a highly correlated name

If the trade is not executable:

- say it is watchlist-only
- do not fake an exact executable entry plan

## Allocation Guidance In Answers

When capital is known, every executable short-term idea should include:

- recommended lot count or max affordable lot count
- rough cash usage
- whether it is first-priority, backup, or watchlist-only

Keep this concise. One line per stock in the notes is enough.

## Logging Rules

When the user asks to write the stock log, or clearly states a new trade:

- update `股票日志/portfolio_state.json`
- write or append a dated Markdown log under `股票日志/`
- mention whether the state change was exact or estimated

## Post-Trade Management

When the user already holds a stock and asks about tomorrow:

- manage the existing position first
- only discuss new buys after checking whether the current position is likely to be reduced
- if not reducing, new names should usually be marked as observation candidates only
