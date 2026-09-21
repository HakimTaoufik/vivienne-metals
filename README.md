# Vivienne · or & argent

A small, dependency-free price and portfolio dashboard for rue Vivienne, Paris.
GitHub Pages serves static files. GitHub Actions collects dealer quotes and sends
configured email alerts. Python 3.11+ and Node.js 22+ are required for development.

## Development

```sh
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
