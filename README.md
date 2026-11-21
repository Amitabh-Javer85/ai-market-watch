# AI Market Watch
[Open AI Market Watch](https://amitabh-javer85.github.io/ai-market-watch/)

A public dashboard for NVIDIA, AMD, Broadcom, Microsoft, Alphabet, Amazon, IBM, and Palantir. Select a company to explore its price history, filter peers by industry, or refresh quotes without signing in.

## How to read the numbers
- TradingView supplies quotes, changes, chart ranges and trading status inside its attributed embeds. Each instrument follows its provider venue and timing.
- Median move, breadth, and daily movers use matched sessions from GetMarketHistory. The public snapshot contains derived percentages only. Its session date and extended-hours basis appear on screen. Prices are unadjusted; a split can affect comparisons. Source history may lag by roughly two days.
- Refresh reloads the market panels and checks the published comparison snapshot. An independent GitHub Actions job checks for new comparisons twice daily. An unavailable feed has a source link, and a failed comparison update preserves the last validated snapshot.

## Development
The public app is the contents of `public/`. From this directory, run `python -m http.server 8000 --directory public` and open http://localhost:8000/. Node, provider keys, and a database are unnecessary.

Run `python -m unittest discover -s tests`, then install the pinned browser-test requirements with `python -m pip install -r tests/requirements.txt` and `python -m playwright install chromium`. Run `python tests/verify.py` for deterministic interaction tests and add `--live` to check the actual provider frames. CI serves the site under its project URL prefix.

## Releases
GitHub Pages serves the site independently of a developer machine. Only `public/` and a generated release identifier are deployed. The original Python prototype at the repository root is archived at `local-v1`. See [operations](OPERATIONS.md) for rollout, verification, free service limits, data timing and rollback, and the [release checklist](RELEASE-PLAN.md) for the v10 scope.
