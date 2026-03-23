# Universe And Risk Filters

Use this file before scoring candidates.

## Default Universe

By default, cover only mainland Shanghai and Shenzhen common A-shares.

Exclude unless the user explicitly asks:

- Hong Kong stocks
- US stocks
- B-shares
- ETFs, LOFs, REITs, and funds
- bonds and convertible bonds

## Hard Exclusions

Normally exclude these names from final recommendations:

- `ST` or `*ST`
- suspended names
- delisting-risk situations
- names with unresolved accounting, fraud, or material governance alarms
- names with insufficient price history for the target horizon
- one-word limit-up names that are not realistically tradable for the intended plan

## Listing-History Rules

Use these minimum structure rules:

- short term: at least 20 complete daily rows preferred; below that, downgrade confidence sharply
- medium term: at least 60 complete daily rows preferred
- long term: at least 120 complete daily rows preferred, and ideally 1 full year of context

If the history window is too short, say so explicitly instead of pretending the structure is reliable.

## Liquidity And Execution Rules

Downgrade exact-price plans when:

- the latest session amount is too small for believable execution
- turnover is erratic and gaps dominate the tape
- the stock often opens with extreme slippage relative to the planned trigger

As a practical default, treat very low-amount names with caution when planning exact short-term entries.

## Concentration Rules

Avoid ending up with a final list that is overly concentrated in:

- one concept theme
- one policy rumor cluster
- one industry chain

If multiple names are similar, keep the strongest expression and cut weaker copies.

## Disclosure Rules

Before finalizing a pick, check for:

- latest earnings or earnings-preannouncement language
- major shareholder reduction plans
- regulatory investigations or exchange inquiry letters
- material litigation, guarantee, or balance-sheet pressure

If a negative official disclosure materially weakens the thesis, remove the stock even if price action looks strong.
