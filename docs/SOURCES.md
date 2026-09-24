# Dealer adapters

The initial sources were inspected and downloaded on 2026-09-21. Raw response
hashes and capture times for sanitized regression fixtures are in
`tests/fixtures/manifest.json`. Fixtures retain only relevant price rows, not
session tokens, checkout forms or scripts. Tests never use these as live history.

| Dealer | Pages | Price semantics | Quantity policy |
| --- | --- | --- | --- |
| [Change Vivienne](https://changevivienne.com/), 48 rue Vivienne | Home, gold bars, silver bars | Home `data-action=buy` is the dealer buying, hence user bid; category `cv-price-sell` is also user bid. Direction verified against the Coq product page's “acheter” card. | Explicit `data-min-qty`; silver coin minimums can exceed one. Out-of-stock bars have no ask. |
| [Maison Joubert](https://maison-joubert.fr/), 38 bis rue Vivienne | Purchase and resale catalogs | `joubert-vend-net` is user ask; `joubert-achat-net` is user bid. London/base prices and tier quotes are excluded. | Purchase minimum from purchase page; resale minimum from resale page. Both retain independent observation times. Explicit out-of-stock purchase rows have no ask, even when a reference sale price remains displayed. |
| [Or & Change](https://www.oretchange.com/), 53 rue Vivienne | Gold coins, gold bars, French silver coins, each direction separately | Exact product name + `product-price`; configured page determines bid or ask. | Category pages do not establish quantity minima. Quotes remain visible but do not trigger automatic excellent signals. |

All configured endpoint URLs are in `config/sources.json`; actual product links
are retained in each observation. Coverage is deliberately limited to audited public prices, not every Paris shop. Online prices can differ from
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

## September 2026 expansion

The September 23–24 audit adds nine dealers, with public response timestamps and
SHA-256 hashes in `tests/fixtures/expansion-manifest.json`. All 32 endpoints collected
successfully on September 24, yielding 418 source/product quotes and 62 identities.
A quote with both directions counts once, not twice. Branches sharing one price
feed are not counted as independent competitors.

| Dealer | Paris shop | Audited representation | Comparison limits |
| --- | --- | --- | --- |
| Merson | 33 rue Vivienne | Four purchase/resale gold/silver catalogs; visible price cross-checked against `content` | Gold minimum 1 only where explicitly stated; silver and buyback minimums otherwise unknown. Buyback is gross before tax. |
| Godot & Fils | 26 rue Vivienne | Gold/silver tables; Napoléon product volume table | Actual ask/bid columns, never London/fixing. Old promotional price excluded. Napoléon bands 1–9, 10–49, 50–99, 100–499, 500+; order maximum 1000. Other table minimums remain unknown. |
| Vivienne Métaux Précieux | 43 rue Vivienne | Public `orpDataCarousel` JSON embedded on homepage | Dealer `achat_cours` = customer bid; `vente_cours` = ask. Paris-local `date_extraction` preserved. Minimums unknown. |
| Comptoir Vivienne de Bourse | 36 rue Vivienne | Official Cours Boutique iframe, public `ydp.io/plcjg/data.js` JSONP | Dedicated boutique feed only; general `/or` page excluded after conflicting prices. Provider publication timestamp retained. Minimums unknown. |
| Comptoir Argentor | 45 rue Vivienne | Official public `ydp.io/uhmzy/data.js` feed | Homepage warned prices were being updated; explicitly confirmation-required and excluded from rankings/signals pending re-audit. |
| Abacor | 13 rue de Rivoli | Three WooCommerce categories | Published EUR ask only; exact US thousands/decimal format. One-unit add-to-cart offer; out-of-stock excluded. Distinct Liberty/Indian Head identities. |
| Comptoir Change Opéra | 9 rue Scribe | Coin buy/sell, gold bars and French silver tables | Immediate net/gré-à-gré columns, not fixing, London, BTC or condition-specific US coin table. Explicit minima; “Pas de vente” clears ask. |
| GoldUnion | 77 rue de Rennes | Three exact product offers: Coq, Napoléon and Swiss 20 F | Duplicate Product JSON-LD must agree. Price applies only to audited 1–49 band; bulk discounts not extrapolated. Ask only. |
| Arcades Change | 59 rue de Ponthieu | Public `gold_table` | Dealer Achat = bid, Vente = ask. Minimums unknown. |

HTML pages request HTML; public `.js` feeds request JavaScript/JSON. A broad JSON
Accept header caused some PrestaShop websites to return a different representation;
a regression test protects this boundary. Public JSONP is parsed as JSON inside a
fixed callback envelope, never executed. Requests sharing a hostname are serialized.

Coin mappings are exact, with no fuzzy weight matching. Generic Napoléon, Coq,
generic sovereign, George, Elizabeth and half-sovereign remain separate. A 30 g
Panda is not a troy ounce. Gold Eagle and Krugerrand contain one fine troy ounce
despite their larger gross weight. Modern ounce content is 31.1034768 g; older
coin specifications and bar purity remain nominal (wear and assay are not inferred).
Reference specifications: [US Mint](https://www.usmint.gov/coins-precious-metal-coins/bullion-coin-programs/),
[Royal Canadian Mint](https://www.mint.ca/en/shop/coins/2026/2026-gml-1-oz-9999-pure-gold-coin-bullion),
and the linked dealer product descriptions. Melt value is indicative, never a dealer bid.
