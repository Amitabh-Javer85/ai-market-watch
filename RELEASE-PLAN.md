# v10.0 release plan
Research complete before implementation. The dedicated public GitHub repository and GitHub Pages provide always-on static hosting without a local server, a billing credential, or a second hosting account. Use standard public GitHub Actions runners. Hosting is subject to GitHub limits; no perpetual availability guarantee. TradingView provides free branded public display. Real-time status and venue vary. Do not extract quotes from widgets or redistribute the former Yahoo cache. IEX HIST permits redistribution with terms, but direct downloads are currently unavailable. Retain the original local implementation at tag local-v1.

## Implementation and release checklist
- [x] Archive only the original reproducible application source and tag the rollback point. Create a dedicated release branch.
- [ ] Build a responsive glass dashboard with eight exchange-qualified symbols, industry grouping, company selection, chart history, provider-displayed quotes and daily movement, source details, keyboard controls, refresh and provider-failure recovery. Preserve choices. Research a permitted source for derived indicators; record actual parity.
- [ ] Use isolated local assets, deterministic routing, no private snapshot, secrets, login, metered functions or owner-operated machine. Publish only the static site directory.
- [ ] Cover company and exchange correctness, responsive breakpoints, search, selection, refresh, disabled storage, blocked provider, keyboard, empty states, recovery and deployment under a subpath.
- [ ] Run CI on PR and main. Gate Pages deployment on green checks, publish production identity, verify anonymous HTTPS and public widget content. Document rollback and forward recovery, runbook and limits.
- [ ] Inspect desktop and phone renders, independently verify every company's prices/chart and the deployed revision, and fix and commit any failures.
- [ ] Tag verified production release and record evidence. Each task or feature is a separate reversible commit.

Sources: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits ; https://docs.github.com/en/billing/concepts/product-billing/github-actions ; https://www.tradingview.com/widget/ ; https://www.tradingview.com/widget-docs/faq/data/ ; https://www.iex.io/legal/hist-data-terms ; https://iextrading.com/trading/market-data/
