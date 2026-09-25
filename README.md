# Vivienne · or & argent

A small, dependency-free price and portfolio dashboard for rue Vivienne and the wider Paris area.
[Open the live dashboard](https://hakimtaoufik.github.io/vivienne-metals/).

GitHub Pages serves static files. GitHub Actions collects dealer quotes and sends
configured email alerts. Python 3.11+ and Node.js 22+ are required for development.

## Development

```sh
npm ci --ignore-scripts
npm test
npm run collect
npm run signals
npm run build
npm run dev
```

The public dataset contains market observations only. Holdings and transactions
stay in your browser. Export a backup after changes. Browser storage is not a
cloud account and can be cleared; device-to-device transfer uses backup import.

Prices are indicative website observations. Availability, condition, quantity,
fees and applicable taxes can change the executable price. Signals are transparent
screening rules, not a promise of return. Dealer history starts at collection;
synthetic observations are never added to the market dataset.

See `docs/OPERATIONS.md`, `docs/METHODOLOGY.md` and `docs/SOURCES.md` for setup,
limitations, quote semantics, and validation evidence.

Version 0.7.0 tracks **12 Paris dealers (8 on rue Vivienne), 62 product identities
and 32 public price endpoints**. The website is in French. There are no frontend
runtime dependencies. Development-only tools are pinned in `package-lock.json`.

Collections are scheduled every 15 minutes; GitHub may delay runs. The page reloads
the latest published file, not the dealer websites. Dealer timestamps, when available,
are preserved separately from collection time. Prices older than one hour are
excluded by default. Unknown quantities, unavailable items and suspended quotes
cannot become the best comparable price or an excellent signal.

`npm run build` also creates `dist/demo.html`: a self-contained offline replay of
the real stored snapshot. Its calculation time is explicitly frozen, and its demo
ledger is isolated from the live portfolio. Open it locally, or use
[the hosted replay](https://hakimtaoufik.github.io/vivienne-metals/demo.html).

The release gate contains 122 core/DOM checks plus 14 desktop/mobile browser
scenarios. See the [build status](https://github.com/HakimTaoufik/vivienne-metals/actions/workflows/market.yml).

Email is disabled until you configure SMTP secrets, choose your recipient and
enable alerts in `config/settings.json`; see `docs/OPERATIONS.md`. The mathematical
model waits for sufficient real daily history. It does not invent prior prices
or promise profitable trades. `docs/VALIDATION.md` records the validation evidence.
