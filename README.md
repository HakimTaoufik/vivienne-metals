# Vivienne · or & argent

A small, dependency-free price and portfolio dashboard for rue Vivienne, Paris.
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

The initial implementation contains 19 product identities (gold coins/bars and
silver coins/Fiji bars), three dealers, 11 public price endpoints, and separate
commit/tag milestones. The website is in French; developer documentation is in
English. There are no frontend/runtime npm dependencies. Development-only tools
are pinned in `package-lock.json`.

The GitHub repository and hourly collection are active. GitHub Pages deployment
requires all 86 core/DOM tests and all 10 desktop/mobile browser scenarios to pass
on code changes. See the [current build and deployment status](https://github.com/HakimTaoufik/vivienne-metals/actions/workflows/market.yml).

Email is disabled until you configure SMTP secrets, choose your recipient and
enable alerts in `config/settings.json`; see `docs/OPERATIONS.md`. The mathematical
model waits for sufficient real daily history. It does not invent prior prices
or promise profitable trades. `docs/VALIDATION.md` records the validation evidence.
