# Deployment and release procedure

The supported public deployment is the static website in `web/dist`. The Python engine,
dashboard, reports/history and Stripe test lane run in an operator-controlled environment.
This guide does not authorize public hosting of the local dashboard or payment endpoints.

## Build and validate

From the repository root, run the backend and package gates:

```sh
uv sync --locked --all-extras
uv run ruff check .
uv run mypy
uv run pytest
uvx --from bandit==1.9.4 bandit -q -ll -r src
uv build
uvx --from twine twine check dist/*
```

For the website, from `web/`:

```sh
npm ci --ignore-scripts --no-fund
npm run typecheck
npm run lint
npm test
npm audit --audit-level=low
npm run build
```

Run secret scanning and the project's installed edit-time hook without disabling
either. CI also runs Semgrep and locked Python dependency auditing; see [CI](ci.md).
Review public configuration before building: every `VITE_` value can be exposed to
visitors. Provider keys and private content must never enter the frontend bundle.

## Local-first deployment sequence

1. Fetch upstream and reconcile source changes. Inventory the actual hosting platform.
2. Snapshot live artifacts and compare them with the last verified release manifest.
   Reconcile any newer live change into local before editing or overwriting it.
3. Build from the reviewed local source; record commit, toolchain, artifact hashes and
   test results. Inspect the public artifact allowlist and secret scan.
4. Package a new uniquely named immutable release and retain an independent archive.
5. Upload only public build files and necessary serving configuration. Validate the
   server configuration before switching active routing.
6. Smoke-check origin and public HTTPS, direct routes, assets and expected isolation.
7. Compare every deployed file's SHA-256 to the local manifest. Record source/artifact
   provenance separately; documentation-only commits need not rebuild a live website.
8. Exercise the real browser journey and retain the last verified release for rollback.

Do not edit production as the source of a fix. Keep credentials, host identities,
private directories and privileged server commands in the operator's private runbook.

## Static hosting contract

Serve `/`, `/product/`, `/explore/`, `/pricing/`, `/docs/` and `/trust/` as actual HTML
entries. Preserve `/evidence/`, `/evidence/run.json` and `/run.json`. Unknown/API/private
file paths should return 404, and unsupported write methods must be rejected. Keep MIME
types correct for scripts, fonts and media. Test nested-route refresh and no-JavaScript
fallback behavior.

Use TLS and suitable security headers, including a restrictive CSP. The current site
requires self-hosted scripts/media/fonts and inline style support for motion. Its browser
runtime needs no remote API connection. Avoid broadening policy to silence a browser
test failure; investigate the actual cause. Configure HTML revalidation and immutable
hashed-asset caching separately, following the selected host/CDN's documented behavior.

## Rollback and recovery

Switch back to the last verified immutable artifact using the platform's native release
mechanism. Check public/origin responses and every-file hashes again. Preserve the
failed release, logs and incident details for investigation; do not overwrite evidence.

Test an archive restore into a separate destination. Validate its hashes, configuration
and actual runtime, then return routing to the intended current release and verify parity.
A backup archive existing on disk does not establish that restoration works.

## Python distribution

Install from source or a verified locally built wheel; public package-index publication
remains deferred. Wheel/sdist checks must confirm required templates, rubrics, prompts
and public verification material are included, while secrets and unrelated dependency
trees are excluded. Test a fresh wheel in an isolated environment rather than relying
only on an editable development install.

The [reliability objectives](reliability.md) define proposed recovery targets. New paid
infrastructure, public identity/storage/billing or scope changes require their own approvals.
