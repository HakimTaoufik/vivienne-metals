# Version history

## v0.6.1 — 2026-09-23

* Give the purchase/sale selector an explicit accessible name.
* Fix the label mismatch found by the first real desktop/mobile browser run.
* Preserve all existing model, storage and notification regression checks.
* Recognize Joubert's explicit out-of-stock rows without a quantity input; suppress their ask prices while retaining source coverage.
* Aggregate quote and spot history at Paris midnight, including daylight saving changes; rebuild daily history from the preserved observations.
* Add four regression tests for stock transitions, missing quantity safeguards and Paris day boundaries.
* Activate the public repository, hourly collection and GitHub Pages dashboard.

## v0.6.0 — 2026-09-22

* Hourly GitHub Actions collection and GitHub Pages deployment configuration.
* Dedicated durable data branch, initial real-history seed and failed-push retry.
* Remote delivery intent saved before SMTP, with cooldowns after uncertain results.
* Deployment, methodology, sources and validation documentation.
* 82 automated tests passed; ten additional browser scenarios supplied for CI.
* GitHub activation and real SMTP delivery remain pending; no fabricated backtest.

## v0.5.0 — 2026-09-22

* French static dashboard: comparison, SVG history, metal/product buttons and filters.
* Private browser journal, FIFO valuation, backup import/export and simple parameters.
* Two days of actual price observations; 69 latest source/product records.
* Five DOM integration tests and desktop/mobile browser scenarios.

## v0.4.1 — 2026-09-22

* Separate Maison Joubert resale page and verified resale quantity requirements.
* Captured fixtures required for all eleven endpoints; no silently skipped sources.

## v0.4.0 — 2026-09-21

* FIFO portfolio ledger, partial-sale cost allocation and backup validation.

## v0.3.0 — 2026-09-21

* Robust premium anomaly screening, net dealer spread and chronological backtests.
* SMTP digests with dry runs, freshness checks and duplicate suppression.

## v0.2.0 — 2026-09-21

* Three dealer adapters, exact product mapping, validated cents and SQLite history.

## v0.1.0 — 2026-09-21

* GitHub Pages architecture, price conventions and dependency-free runtime scaffold.
