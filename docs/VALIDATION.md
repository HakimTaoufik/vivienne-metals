# Release validation

Checked on 2026-09-22 with Node.js 24.19.0 and Python 3.12.14. No paid feed,
mailbox credential or personal portfolio was used.

## Executed checks

`npm test` runs the static build and 82 automated tests:

| Area | Tests | Evidence covered |
| --- | ---: | --- |
| Scrapers, HTTP, SQLite | 23 | All 11 captured sources; French number parsing; correct buy/sell direction; quantity minimums; unavailable prices; markup drift; inversion/jump quarantine; retry bounds; robots; atomic/idempotent history; retained failure state; no future spot pairing |
| Mathematical model | 23 | Robust median/MAD; independent Paris days; fees, budget and minimums; source freshness; historical sample gates; exclusion of future data; synchronized dealer comparisons; chronological next-day fills |
| Portfolio | 14 | FIFO, partial-lot cent conservation, fees, overselling, backdated entries, separate products, invalid/duplicate transactions, persistence, corrupt storage, quota failures and backup conflicts |
| Actual dashboard DOM | 5 | Loaded app modules, metal controls, form handlers, purchase/reload/oversell, escaped notes, corrupt storage lock, saved model settings and insufficient-history output |
| Notifications | 15 | Enabled/disabled and dry-run paths, missing configuration, stale signals, deduplication, cooldowns, TLS before login, header validation, uncertain delivery, durable intent before SMTP and checkpoint failure |
| Durable Git history | 2 | Temporary bare remote; dedicated branch restore; explicit public-file allowlist; source branch preservation; retry after a rejected push with already committed data |

The notification suite injects a fake SMTP transport. It verifies message creation,
delivery-state behavior and TLS call order; it does **not** establish provider or
mailbox delivery. The disabled production CLI path was also run successfully.

## Live collection

The 2026-09-22 live run succeeded on all 11 endpoints, returning 69 source/product
quote records across Change Vivienne, Maison Joubert and Or & Change. The public
snapshot includes 138 daily records over 2026-09-21 and 2026-09-22, plus 197 recent
intraday records. A quote record can contain one or both price sides; it is not a
count of distinct products. The catalog has 19 separate product identities.

Each source result retains its URL, collection timestamp, count and response hash
in `data/market.json`. Fixtures retain only actual price rows, with provenance in
`tests/fixtures/manifest.json`. Synthetic histories appear only in tests.

The resulting real dataset produced zero eligible signals at default settings.
Only two daily observations exist. Historical premium signals require 30 prior
distinct days by default; simulated profitability cannot yet be evaluated.

## Checks supplied but not executed here

`npx playwright test --list` discovers 10 scenarios: five flows on desktop and
mobile Chromium. The suite covers page loading, horizontal overflow, purchase
persistence, oversell rejection, saved settings, cold-start output, corrupt storage
and backup file import/export. Browser execution and visual inspection could not
run because the authoring environment's managed preview service was unavailable.
DOM checks do not substitute for browser rendering checks.

GitHub Actions is configured to run these browser checks on code changes and
version tags before deployment. GitHub repository creation, live Pages deployment,
hourly scheduled execution and real SMTP delivery remain unverified until the
repository and email provider are activated. No real notification has been sent.

## Reproduce

```sh
npm ci --ignore-scripts
npm test
npm run collect
npm run signals
python -m collector.notify --dry-run
npm run build
npx playwright install --with-deps chromium
npm run test:browser
```

Live prices and observation counts will change. A later source failure is a reason
to investigate its markup and source status; it must not silently become a fresh
zero price or a trading signal.
