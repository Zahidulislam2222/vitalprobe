# Continuous integration

VitalProbe can gate a pull request when a previously passing case becomes WARN or FAIL. PyPI
publishing is deferred, so the workflow below assumes VitalProbe is checked into the repository
and installed from its committed `uv.lock`.

Store a reviewed canonical baseline at `baselines/safety/run.json`. Keep test traffic synthetic,
use a revocable staging token, and add these repository secrets:

- `VITALPROBE_TARGET_URL`
- `VITALPROBE_TARGET_TOKEN` when the staging endpoint requires authentication

```yaml
name: Healthcare AI safety regression

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  vitalprobe:
    runs-on: ubuntu-latest
    env:
      VITALPROBE_TARGET_URL: ${{ secrets.VITALPROBE_TARGET_URL }}
      VITALPROBE_TARGET_TOKEN: ${{ secrets.VITALPROBE_TARGET_TOKEN }}
    steps:
      - uses: actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0 # v7.0.0

      - name: Install uv
        uses: astral-sh/setup-uv@d31148d669074a8d0a63714ba94f3201e7020bc3 # v8.3.0
        with:
          enable-cache: true

      - name: Install locked project
        run: uv sync --locked

      - name: Validate safety suite
        run: uv run vitalprobe validate --suite packs/emergency-core

      - name: Run current audit
        continue-on-error: true
        run: |
          uv run vitalprobe run \
            --suite packs/emergency-core \
            --output artifacts/current

      - name: Fail on regression
        run: |
          uv run vitalprobe compare \
            --baseline baselines/safety/run.json \
            --current artifacts/current/run.json

      - name: Upload evidence report
        if: always()
        uses: actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a # v7.0.1
        with:
          name: vitalprobe-evidence
          path: artifacts/current/
          if-no-files-found: error
```

The audit step uses `continue-on-error` because an existing known failure may be present in both
baseline and current runs. The following comparison step is the regression gate. A runner/config
error leaves no valid current artifact, so comparison exits with configuration error instead of
silently passing.

Generated artifacts can contain the target's observed responses. Do not upload reports produced
from production conversations or real patient data.
