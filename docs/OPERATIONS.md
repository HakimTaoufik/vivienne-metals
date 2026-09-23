# Run and publish

## Quick local start

Install Node.js 24 and Python 3.11 or later. The application and collector have
no runtime package dependencies. The npm lockfile pins development-only DOM and
browser-test tools.

```sh
npm ci --ignore-scripts
npm test
npm run collect
npm run signals
python -m collector.notify --dry-run
npm run build
npm run dev
```

For a normal local checkout the dev server listens on port 4173. It serves the
`dist` folder; run the build again after source edits. The website is pure static
HTML, CSS and ES modules and works under a GitHub project subpath.

## Repository and GitHub Pages

The [repository](https://github.com/HakimTaoufik/vivienne-metals) and
[GitHub Pages dashboard](https://hakimtaoufik.github.io/vivienne-metals/) are active.
Clone the current code and its version history with:

```sh
git clone https://github.com/HakimTaoufik/vivienne-metals.git
cd vivienne-metals
git fetch origin --tags
```

The bundled initial archive is retained for provenance; the repository has newer
fixes. If copying the source folder, preserve its `.git` directory.
Do not publish your portfolio export or an `.env` file. A public repository keeps
this setup compatible with free GitHub Pages; a private repository requires an
eligible GitHub plan. Pages itself is a public dashboard in this architecture.

For a new fork, enable **Settings → Pages → Source → GitHub Actions** and Actions for the
repository if necessary. The workflow has the minimum job-level content/Pages
permissions it needs. Run **Collect, alert and publish** once under Actions. The
deployment URL appears in the successful deployment job.

Optional CLI activation after creating the repository:

```sh
gh api --method POST repos/OWNER/vivienne-metals/pages -f build_type=workflow
gh workflow run market.yml --repo OWNER/vivienne-metals
```

If Pages already exists, use the repository settings instead of repeating POST.

## Durable public history

The pipeline serializes runs in one concurrency group. It restores a dedicated
`market-data` branch into a worktree containing only an allowlist of public data
files. The first run seeds the archive from the supplied real snapshot, then adds
new observations. SQLite transactions and unique observation keys make identical
imports idempotent. Historical data is not a disposable Actions cache/artifact.

Every run commits the SQLite archive, JSON publication, delivery status and hashed
cooldowns to `market-data` without force-pushing. Only `main` and the schedule
trigger production, so data commits do not recursively launch collection.
Source failures still publish health state. Deployment failures do not erase the
data already saved on the durable branch.

Keep a periodic backup of `market-data`, and monitor database/repository size as
history grows. A multi-year high-frequency archive may merit external object
storage rather than an ever-growing Git repository.

## Enable email

1. Open the site's Parameters tab and set quantities, costs, thresholds and cooldown.
2. Check **Activer les alertes dans la configuration exportée** and export settings.
3. Replace `config/settings.json` in `main` with the exported file and commit it.
4. Under **Settings → Secrets and variables → Actions**, create these repository
   secrets using your SMTP provider's instructions:

| Secret | Value |
| --- | --- |
| `SMTP_HOST` | Provider SMTP hostname |
| `SMTP_PORT` | `587` for STARTTLS or `465` for implicit TLS |
| `SMTP_USER` | Provider username |
| `SMTP_PASSWORD` | Provider app password / SMTP secret |
| `SMTP_FROM` | One authorized plain sender address |
| `ALERT_TO` | Your single recipient address |

The dashboard never stores these secrets. Live delivery remains inactive until
you supply them and enable alerts. No recipient has been preselected.

The runner sends one text digest of eligible market signals. It persists a hashed
delivery intent remotely **before** SMTP. A connection failure or uncertain SMTP
result suppresses that signal for the cooldown rather than risking repeated mail.
This favors avoiding duplicates over guaranteed delivery. It is not an exactly-once
mail service: mailbox delivery still depends on the provider and spam handling.

For inspection without sending, `python -m collector.notify --dry-run` writes a
private `.preview.eml` only when an eligible signal exists. It never consumes the
cooldown. The tests inject explicit synthetic signals for this path. Do not lower
production safeguards just to manufacture a test opportunity.

## Schedule and health

Collection is requested at minute 17 of each hour. GitHub schedules can be delayed
or dropped; they are not a real-time service. Scheduled runs in inactive public
repositories can be disabled by GitHub. Check Actions if observations stop and
re-enable scheduled workflows when needed. The dashboard excludes quotes older
than the configured age (six hours by default).

If a parser fails, inspect the dealer page and the source-health panel. Update its
adapter and actual fixture together; do not relax validation just to restore a
green status. If a >25% jump is legitimate, review the exact changed quote before
repairing the affected baseline in a backed-up archive.

## Tests and versioning

```sh
npm test                          # collector, model, storage, SMTP, DOM, Git persistence
npx playwright install chromium # on your local machine or CI
npm run test:browser              # desktop and mobile Chromium flows
```

The browser suite runs on code pushes, pull requests and version tags; it avoids
reinstalling a browser on every hourly data run. Runtime schedules still run fast
regression tests. Browser tests require a working browser runtime.

The v0.6.1 release passed 86 core/DOM tests and all ten real browser scenarios in
GitHub Actions, then deployed successfully to GitHub Pages. Live browser inspection
and scheduled collections were also completed. See `docs/VALIDATION.md` for the
run links, production regressions and remaining limits. Actual SMTP provider and
mailbox delivery still require the owner's email configuration.

Make focused commits; use annotated `v0.x.y` tags for tested milestones. Treat an
adapter fix as a patch release and a product/schema change as a minor release.
Never rewrite a released tag or force-push the durable market-data branch.

Primary platform references: [GitHub Pages configuration](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site),
[scheduled workflow behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule),
[Playwright web servers](https://playwright.dev/docs/test-webserver).
