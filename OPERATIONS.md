# AI Market Watch operations

[Open AI Market Watch](https://amitabh-javer85.github.io/ai-market-watch/) · [Release checks](https://github.com/Amitabh-Javer85/ai-market-watch/actions/workflows/pages.yml) · [Metric updates](https://github.com/Amitabh-Javer85/ai-market-watch/actions/workflows/metrics.yml)

## Hosting and ownership

GitHub Pages serves the files under `public/` from a dedicated public repository. A visitor needs a browser and the public URL. Once deployed, the dashboard continues to work with the developer's computer off. Releases use the repository's automatic token, GitHub's standard Ubuntu runners and the `github-pages` environment. No personal access token, paid runner or custom domain is needed. Keep **Settings → Pages → Build and deployment → Source** set to **GitHub Actions**. Keep Actions enabled and the `main` branch eligible to deploy to the environment.

The site is a free public information service. GitHub Pages' published limits include 1 GB/site and 100 GB/month of soft bandwidth. There is no purchased uptime guarantee. Monitor GitHub's service status during incidents. Standard runner compute is free for public repositories; the release artifact expires after one day. Keep the repository public and avoid paid runners, metered add-ons and commercial transaction features. [Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits) · [Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions) · [GitHub Status](https://www.githubstatus.com/)

## Release

1. Branch from current `main`, make focused commits, and open a pull request targeting `main`.
2. Wait for **Dashboard tests**. It discovers Python unit tests, installs Chromium, and runs `tests/verify.py` at a project subpath. Test locally with the commands below. The pull request workflow has read access and cannot publish.
3. Merge the reviewed change. The `main` workflow reruns tests, stages only `public/` and adds `version.json` to the staged artifact. **Publish main** checks that the tested revision still matches the head of `main` before requesting deployment.
4. Require **Check public release** to pass. It verifies public HTTPS, the revision, the metrics snapshot, and the live provider via Chromium. An unrelated green build or a successful upload alone does not verify the production URL.
5. For an intentional redeploy of the current revision, dispatch `gh workflow run pages.yml --ref main`. View runs with `gh run list --workflow pages.yml --limit 5` and `gh run view RUN_ID --log-failed`. Scheduled data commits explicitly dispatch this workflow because pushes using the automatic token generally do not start another push workflow.

```sh
python -m pip install -r tests/requirements.txt
python -m playwright install chromium
python -m unittest discover -s tests
python tests/verify.py
python tests/verify.py --url https://amitabh-javer85.github.io/ai-market-watch/ --live
```

On a fresh Linux runner use `python -m playwright install --with-deps chromium`. The local suite starts its own HTTP server. Keep development dependencies outside the published directory.

## Monitoring and recovery

- **Identify the active release.** Fetch [the version endpoint](https://amitabh-javer85.github.io/ai-market-watch/version.json) and compare `revision` to the expected `git rev-parse origin/main` after a fetch. On transient edge caching, retry the version URL with `?rev=<expected-sha>`. Version `10.0` identifies the release family; the full SHA identifies the exact deployment.
- **Data freshness.** Inspect the dated [metrics snapshot](https://amitabh-javer85.github.io/ai-market-watch/metrics.json) and the latest metric update workflow. A Saturday, Sunday or exchange holiday can legitimately show the prior session. If an expected completed session is missing, inspect provider availability, coverage and the update run before retrying the update workflow. Preserve the last valid data during an upstream outage. A browser refresh retrieves available data and does not grant public visitors GitHub write access.
- **Scheduled jobs.** GitHub can delay or drop scheduled events at peak times. They run on the default branch and may be disabled after 60 days without repository activity. Normal commits containing changed data provide activity. If prolonged provider failure or repository inactivity suspends updates, inspect the failed ingestion runs, re-enable the metrics workflow in Actions, then dispatch it on `main`. The static dashboard remains hosted independently of scheduler state. [Scheduled event behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- **Widget / chart outage.** Verify the upstream provider links directly and retry in an ordinary browser with third-party content enabled. The chart provider and the source of derived metrics are independent. Use the widget's fallback link and preserve its attribution and original embed origin. Check the exact failed test before rolling back a healthy shell.
- **Release failed before deployment.** The last successful Pages deployment continues to serve. Inspect **Dashboard tests**, current `main`, Pages source and deployment environment settings. A newer main revision intentionally prevents an older run from promoting. Run or wait for the workflow on current `main`.
- **Deployment succeeded but smoke failed.** Check `version.json`, the expected public URL including the project subpath, and the failing resource or provider. A failed smoke check does not automatically remove an already-published release. If the public site is serving a regression, roll it back.
- **Rollback a feature.** From the latest main, create a rollback branch, `git revert <feature-commit>`, run both test suites, then open and merge the rollback PR. Use `git revert -m 1 <merge-commit>` for a merge that must be reverted in full. Preserve unrelated good changes. The revert produces a new release revision; verify anonymous production checks on that revision.
- **Restore a complete static release.** Find a known good v10 commit in release history. In a branch based on current main run `git restore --source=<known-good-v10-sha> -- public/`, review the diff and commit it. If the old release also requires a prior ingestion or test contract, restore those specific compatible files and validate together. Use the normal PR and deployed-SHA checks. The `local-v1` tag preserves the previous local Python dashboard; it is not a Pages deployment artifact.

## Integrity checks

- Keep credentials, raw provider histories, developer folders and screenshots outside `public/`. Retain provider attribution and the source and trading date of derived metrics.
- Treat a provider response, a successful transfer, an accepted Pages deployment and a verified public release as separate checks. Never replace missing prices with zero or invent a newer session date.
- Review hosting/data terms and run the same acceptance suite when a provider or major workflow dependency changes. The release workflow pins direct Actions dependencies to full commit SHAs.
