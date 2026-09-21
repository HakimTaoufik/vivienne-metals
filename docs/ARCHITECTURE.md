# Architecture

* `collector/`: Python standard-library HTTP collection, strict HTML adapters,
  SQLite archival and JSON export. Per-source failures never become zero quotes.
* `shared/`: browser/Node shared calculation modules, so email signals and on-screen
  signals use the same model and defaults.
* `web/`: static, French-language dashboard. Portfolio ledger is device-local.
* `data/`: public quote history and collector health; no holdings, email addresses,
  passwords or SMTP credentials.
* `.github/workflows/`: test, collect, notify and deploy. Durable runtime data lives
  on the `market-data` branch, separate from small versioned source commits.

All prices are EUR. Quote amounts are integer cents. `ask` means you pay the dealer;
`bid` means the dealer pays you. Melt value is fine-metal grams × EUR/gram spot.
Missing sides remain null. Specific coin variants and bullion sizes have distinct
identities; matching never uses fuzzy product names.

The static website cannot securely run a scraper, hold an SMTP password, or send
mail when closed. Actions supplies this server-side execution. Local UI settings
must be exported to repository configuration to govern unattended email alerts.
Holdings-aware suggestions are local; emails are market-only by default.
