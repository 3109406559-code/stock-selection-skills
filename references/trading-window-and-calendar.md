# Trading Window And Calendar

Use this file to decide which session should be treated as the anchor and how to phrase timing.

## Default Time Zone

Use China Standard Time and write exact dates.

## Session Handling

### After the cash close and before the next open

This is the preferred window for the skill.

- use the latest completed session as the anchor day
- add overnight policy, company, and macro updates
- write the intended buy window for the next trading day explicitly

### During live trading hours

Say that the framework is optimized for the post-close to pre-open window and that the answer is provisional.

During live hours:

- do not present the current session as final
- separate completed-session facts from intraday observations
- avoid overconfident exact levels if the live tape is still evolving

### Weekend or exchange holiday

Use the most recent completed trading session as the anchor day and say so explicitly.

If the next session date is uncertain because of a holiday stretch, avoid casual relative phrasing and use conditional wording such as:

- `下一个交易日开盘后`
- `待交易所恢复交易后的首个交易日`

## Exact-Date Rule

Whenever the user could be confused by relative dates, include the exact date in the answer:

- anchor session date
- catalyst dates
- intended buy window
- review or sell window

## Trading-Hours Language

Use horizon-appropriate timing language:

- short term: `次日开盘后`, `9:35-10:30`, `突破确认后`
- medium term: `未来1-5个交易日分批介入`
- long term: `未来5-20个交易日分批布局`

Do not mix long-term thesis language with tight intraday execution language unless you clearly explain the change in horizon.
