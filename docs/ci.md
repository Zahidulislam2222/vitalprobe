# Continuous integration

## Repository gates

The committed [workflow](../.github/workflows/ci.yml) runs four jobs:

| Job | Checks |
|---|---|
| `test` | Locked Python install, Ruff, strict mypy, pytest, Bandit, package build, Twine and isolated wheel smoke test |
| `secrets` | Checksum-verified Gitleaks over published files |
| `security-audit` | Semgrep and locked Python dependency audit |
| `frontend` | Locked Node install, TypeScript, ESLint, Vitest, npm audit and Vite build |

Actions are pinned to commit hashes. Jobs have read-only repository permissions;
there is no deployment or paid-model job. Source-install and freshly resolved wheel
behavior are separate gates. A green workflow verifies those checks for its commit;
it does not approve clinical content, billing, uptime or load capacity.

## Gate your chatbot's regressions

Use only fictional staging traffic against an endpoint you control. Keep a reviewed
canonical baseline at `baselines/safety/run.json`. This example assumes VitalProbe's
source and lockfile are included in your CI checkout. Install from its committed
`uv.lock` rather than assuming a published PyPI version.

For a private staging target, configure `VITALPROBE_TARGET_URL` and, if needed,
`VITALPROBE_TARGET_TOKEN` as repository secrets. Do not expose them to untrusted fork
pull requests or enable a privileged `pull_request_target` workflow to run untrusted code.
Cloud judges are off. A staging target may itself incur inference charges; obtain its
operator's budget approval before enabling recurring CI traffic.

```yaml
name: Fictional safety regression
on:
  push:
    branches: [main]
permissions:
  contents: read
jobs:
  safety:
    runs-on: ubuntu-latest
    env:
      VITALPROBE_TARGET_URL: ${{ secrets.VITALPROBE_TARGET_URL }}
      VITALPROBE_TARGET_TOKEN: ${{ secrets.VITALPROBE_TARGET_TOKEN }}
      VITALPROBE_JUDGE: none
    steps:
      - uses: actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7.0.0
      - uses: astral-sh/setup-uv@d31148d669074a8d0a63714ba94f3201e7020bc3 # v8.3.0
      - run: uv sync --locked
      - run: uv run vitalprobe validate --suite packs/emergency-core
      - name: Produce current evidence
        continue-on-error: true
        run: uv run vitalprobe run --suite packs/emergency-core --output artifacts/current
      - name: Reject target errors and malformed or absent evidence
        run: |
          uv run python - <<'PYTHON'
          from pathlib import Path
          from vitalprobe.schema import RunResult, count_results, run_verdict
          result = RunResult.model_validate_json(Path("artifacts/current/run.json").read_text())
          if not result.results or len(result.results) != result.suite.case_count:
              raise SystemExit("Incomplete case evidence blocks this gate")
          if len({case.id for case in result.results}) != len(result.results):
              raise SystemExit("Duplicate case evidence blocks this gate")
          if count_results(result.results) != result.counts:
              raise SystemExit("Inconsistent verdict counts block this gate")
          if run_verdict(result.results) != result.verdict:
              raise SystemExit("Inconsistent aggregate verdict blocks this gate")
          if result.counts.error:
              raise SystemExit("Target errors block this gate")
          PYTHON
      - name: Reject regressions
        run: >-
          uv run vitalprobe compare
          --baseline baselines/safety/run.json
          --current artifacts/current/run.json
      - name: Upload fictional evidence
        if: always()
        uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
        with:
          name: fictional-safety-evidence
          path: artifacts/current/
          if-no-files-found: error
```

The audit may exit 1 for failures already recorded in the baseline, so comparison
follows it. **Comparison alone is insufficient:** it gates shared PASS-to-WARN/FAIL
changes, and does not classify ERROR as a regression. The explicit canonical-result
check above rejects target errors, malformed JSON, missing/incomplete results,
duplicate case IDs, inconsistent counts and inconsistent aggregate verdicts. Run each job
in a fresh workspace so a previous artifact cannot be mistaken for the current run.

Select your acceptance policy deliberately. For an absolute gate, omit
`continue-on-error` and require the audit to pass; add `--strict-warn` if warnings must
also fail. Independently review changed or removed cases, rubric versions and baseline
updates. Baseline acceptance must not erase an unexplained failure.

Never upload patient data, actual conversations, credential-bearing URLs or unreviewed
customer responses. Use restricted artifact access and an explicit retention period
for your repository; public workflow artifacts are not confidential storage.
