# Prices, signals and portfolio calculations

## Units and identities

All trade prices are integer EUR cents per physical unit. `ask` is what the user
pays; `bid` is what the dealer pays the user. Missing/zero prices become null.
Never interpret a dealer's French "achat" label without its page context.

Melt value = fine grams × observed EUR/gram × 100, rounded to cents. Spot is the
indicative quotation displayed by Change Vivienne, not an independent licensed
exchange feed. A product observation is paired with a spot observed at or before
it, no more than six hours earlier. The paired value and provenance are retained.
Collection time is not a dealer-guaranteed last-price-update time.

Coq/Marianne and general Napoléon/Génie coins remain separate. Combibar products
are not silently mapped to ordinary bars. Bar prices may still depend on maker,
condition, certificate and year; comparison does not establish interchangeability.
Fine-weight assumptions are explicit in `config/products.json`.

## Opportunity rules (robust-premium-v1)

The model is an interpretable screening rule, not a fitted return predictor.
For each product/dealer/side, take the last observation on each **previous Paris
calendar day**, within the configured lookback. Exclude today's data and future
observations. The default minimum is 30 distinct days, not 30 scrapes.

Let `p = 100 × (price / melt − 1)`, `m = median(historical p)` and
`scale = max(0.25, 1.4826 × median(abs(p − m)))`. The robust score is
`z = (current p − m) / scale`. It is **not** a confidence level or probability.
The 0.25 percentage-point floor prevents near-constant series from creating an
effectively infinite score. No parameter optimization is run on the test period.

An excellent buy requires all of:

* Fresh, successful source and contemporaneous spot; known minimum quantities.
* At least the minimum number of historical ask and bid days for that dealer.
* `z <= -zThreshold`; premium no greater than `maxPremiumPct`.
* Current round-trip net spread no greater than `maxSpreadPct`.
* Quantity and net purchase cost within your configured limits.
* The historical median bid premium, applied to today's melt value, yields at
  least `minEdgePct` after purchase fees, selling fees, tax provision and fixed fees.

That last requirement is a **mean-reversion scenario**, not a forecast that the
median will recur. It intentionally produces few alerts when transaction costs
make an apparent bargain uneconomic.

An excellent sell requires a sufficiently high current dealer bid premium
(`z >= zThreshold`), adequate history, fresh data, verified quantity and a net
advantage over that dealer's historical median bid. Market-only emails cannot
know whether you hold that product. On-screen suggestions can additionally
compare net proceeds with your remaining FIFO cost basis.

The independent cross-dealer rule compares the lowest eligible ask to the highest
eligible bid after all configured costs. Observations must be within 15 minutes,
both minima must be known and satisfied, and the purchase must fit the budget.
An apparent positive spread is not guaranteed executable arbitrage.

## Backtest

The backtest walks forward one observed day at a time. Each signal is calculated
using strictly earlier days. A pending order fills at the next observed day's
eligible quote, with 0.25% adverse slippage on each side plus configured costs.
It holds at most one position of the configured quantity, starts with the stated
budget and cannot borrow. It exits on a qualifying sell signal or after 30
observed days, at the following observation. Open positions are marked at an
eligible bid; missing valuations are omitted, not invented.

The output includes finished trades, open-position status, simulated return and
maximum observed drawdown. Zero trades or a short sample cannot establish model
quality. Public history starts on 2026-09-21; no dealer history was fabricated or
backfilled from the synthetic unit-test fixtures. There is currently insufficient
real history to evaluate profitability.

## Portfolio

Each purchase creates a FIFO lot containing unit price plus allocated acquisition
fees. Partial sales consume the oldest lots; remaining cents stay on the residual
lot, ensuring exact conservation when the lot is exhausted. Realized result is
actual sale proceeds less recorded sale fees and consumed cost basis. The ledger
does not calculate the user's personal statutory tax liability.

The dashboard's net liquidation estimate applies the configured selling fee,
fixed fee and tax provision to fresh published bids. Quotes with unknown minimums
are marked for confirmation; those with a known unmet minimum are excluded.
Products with no usable quote are excluded from the total and the total is labeled
partial. Export backups: local browser storage can be cleared and does not sync.

## Known limits

* Sources can change HTML, prices can be indicative, and category pages can omit
  minimum quantities. Unknown minima prohibit automatic excellent signals.
* The site has no trade-execution function. Stock/grade checks remain with dealers.
* Gold and silver use a single indicative spot provider; no automatic fallback to
  an unrelated or unverified spot feed is attempted.
* Dealer-specific inventory, liquidity, tax treatment and execution slippage can
  dominate a statistical anomaly. The model does not ingest news or macro forecasts.
* Browser settings affect the local dashboard. Scheduled emails use the committed
  repository settings; exporting a file alone does not change the runner.
