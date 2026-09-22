# Vivienne · or & argent

A small, dependency-free price and portfolio dashboard for rue Vivienne, Paris.
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

Deployment and SMTP activation are pending. The authoring environment's browser
preview was unavailable; DOM integration tests ran, and desktop/mobile browser
tests are supplied for GitHub Actions. See `docs/VALIDATION.md` for the exact
checks performed and the checks still requiring activation.
