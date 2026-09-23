# Release validation

Checked on 2026-09-23 with Node.js 24 and Python 3.12 locally / Python 3.13
in GitHub Actions. No paid feed, mailbox credential or personal portfolio was used.

## Executed checks

`npm test` runs the static build and 86 automated tests. The browser suite adds
10 desktop/mobile scenarios, for **96 passing tests** in the release pipeline.

| Area | Tests | Evidence covered |
| --- | ---: | --- |
| Scrapers, HTTP, SQLite | 27 | All 11 captured sources; French number parsing; correct buy/sell direction; quantity minimums; explicit Joubert stock transitions; markup drift; inversion/jump quarantine; retry bounds; robots; atomic/idempotent history; Paris midnight and DST boundaries; retained failure state; no future spot pairing |
| Mathematical model | 23 | Robust median/MAD; independent Paris days; fees, budget and minimums; source freshness; historical sample gates; exclusion of future data; synchronized dealer comparisons; chronological next-day fills |
| Portfolio | 14 | FIFO, partial-lot cent conservation, fees, overselling, backdated entries, separate products, invalid/duplicate transactions, persistence, corrupt storage, quota failures and backup conflicts |
| Actual dashboard DOM | 5 | Loaded app modules, metal controls, form handlers, purchase/reload/oversell, escaped notes, corrupt storage lock, saved model settings and insufficient-history output |
| Notifications | 15 | Enabled/disabled and dry-run paths, missing configuration, stale signals, deduplication, cooldowns, TLS before login, header validation, uncertain delivery, durable intent before SMTP and checkpoint failure |
| Durable Git history | 2 | Temporary bare remote; dedicated branch restore; explicit public-file allowlist; source branch preservation; retry after a rejected push with already committed data |
| Desktop/mobile Chromium | 10 | Actual rendering, no horizontal overflow, purchase/reload, oversell rejection, saved settings, cold-start output, corrupt storage preservation and backup file import/export |

The notification suite injects a fake SMTP transport. It verifies message creation,
delivery-state behavior and TLS call order; it does **not** establish provider or
mailbox delivery. The disabled production CLI path was also run successfully.

## Live collection

The initial 2026-09-22 live run succeeded on all 11 endpoints, returning 69
source/product quote records across Change Vivienne, Maison Joubert and
Or & Change. Its snapshot contained 138 daily records and 197 intraday records.
Those counts describe the initial snapshot, not the continuously growing archive.
A quote record can contain one or both price sides; it is not a count of distinct
products. The catalog has 19 separate product identities.

Each source result retains its URL, collection timestamp, count and response hash
in `data/market.json`. Fixtures retain only actual price rows, with provenance in
`tests/fixtures/manifest.json`. Synthetic histories appear only in tests.

Real collection began on 2026-09-21. Historical premium signals require 30 prior
distinct Paris days by default; the release still has insufficient real history
to evaluate simulated profitability. Synthetic histories appear only in tests.

## Production verification

[Release pipeline](https://github.com/HakimTaoufik/vivienne-metals/actions/runs/35829008150)
validated source commit `7876c3d`, ran all 96 tests, collected live dealer pages,
persisted the archive and deployed GitHub Pages. All 11 endpoints succeeded with
69 source/product records. The
[live dashboard](https://hakimtaoufik.github.io/vivienne-metals/) was also inspected
in a browser: it showed 11/11 healthy sources, three Paris dates, working gold and
silver controls, and the expected 2/30 prior-day model warmup. The earlier successful code run was
[35764756460](https://github.com/HakimTaoufik/vivienne-metals/actions/runs/35764756460),
with 92 tests before the four additional production regressions.

Hourly execution and deployment were observed in successful scheduled runs
[35778702902](https://github.com/HakimTaoufik/vivienne-metals/actions/runs/35778702902),
[35795063037](https://github.com/HakimTaoufik/vivienne-metals/actions/runs/35795063037)
and [35806588230](https://github.com/HakimTaoufik/vivienne-metals/actions/runs/35806588230).
Schedules can be delayed; a successful workflow does not promise every dealer
will always be available. Source health is shown separately on the dashboard.

Production checks found and fixed three issues before the v0.6.1 tag:

* An accessible-name mismatch in the operation selector, caught by the first real browser run.
* Joubert stock labels replacing quantity inputs; unavailable asks are suppressed and missing inputs without a stock label still fail closed.
* UTC daily aggregation disagreeing with the Paris calendar. Re-exporting the preserved SQLite archive restored 21, 22 and 23 September without inventing observations.

Real SMTP provider/mailbox delivery remains unverified. Alerts are disabled until
the owner supplies the SMTP secrets and recipient and enables the configuration.
No real notification has been sent.

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
