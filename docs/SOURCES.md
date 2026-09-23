# Dealer adapters

The initial sources were inspected and downloaded on 2026-09-21. Raw response
hashes and capture times for sanitized regression fixtures are in
`tests/fixtures/manifest.json`. Fixtures retain only relevant price rows, not
session tokens, checkout forms or scripts. Tests never use these as live history.

| Dealer | Pages | Price semantics | Quantity policy |
| --- | --- | --- | --- |
| [Change Vivienne](https://changevivienne.com/), 48 rue Vivienne | Home, gold bars, silver bars | Home `data-action=buy` is the dealer buying, hence user bid; category `cv-price-sell` is also user bid. Direction verified against the Coq product page's “acheter” card. | Explicit `data-min-qty`; silver coin minimums can exceed one. Out-of-stock bars have no ask. |
| [Maison Joubert](https://maison-joubert.fr/), 38 rue Vivienne | Purchase and resale catalogs | `joubert-vend-net` is user ask; `joubert-achat-net` is user bid. London/base prices and tier quotes are excluded. | Purchase minimum from purchase page; resale minimum from resale page. Both retain independent observation times. Explicit out-of-stock purchase rows have no ask, even when a reference sale price remains displayed. |
| [Or & Change](https://www.oretchange.com/), 53 rue Vivienne | Gold coins, gold bars, French silver coins, each direction separately | Exact product name + `product-price`; configured page determines bid or ask. | Category pages do not establish quantity minima. Quotes remain visible but do not trigger automatic excellent signals. |

All configured endpoint URLs are in `config/sources.json`; actual product links
are retained in each observation. This is a three-dealer initial coverage set,
not a claim to cover every shop on rue Vivienne. Online prices can differ from
counter execution; verify the dealer's stock, grade and conditions.

On 2026-09-23, production exposed Joubert's out-of-stock variant: a
`Rupture de stock` span replaces the quantity control. This is a recognized
unavailable state, not a missing-selector exception. An absent quantity control
without that exact stock label still fails closed. Regression tests exercise
synthetic stock transitions using the actual captured label; these test cases
are never imported into market history.

The fetcher uses an identifying agent, obeys robots exclusions (including wildcard
paths), paces requests per host, limits response size and retries only transient
network/5xx failures. It does not bypass logins or bot challenges. A 403 or 429 is
not repeatedly retried. Failed robots retrieval blocks that host for the run.

Missing selectors, no recognized products, duplicate mappings, inverted spreads,
large coverage loss, and >25% price jumps are quarantined. Old observations remain
visible with their original timestamps and failed-source state; they are not
substituted with zeros or allowed to generate excellent signals.

Before adding a dealer, verify its public page, display direction, minimums and
fine-weight/product identity. Add a sanitized actual response fixture plus tests.
Do not infer a sell quote by applying a made-up percentage to its buy quote.
