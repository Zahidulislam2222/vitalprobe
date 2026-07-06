# Full-product founder acceptance

This is the final P8 acceptance script. It covers every implemented VitalProbe surface.
Run it from the public repository root in Windows PowerShell.

Paid cloud calls are **not** part of the local script. Do not add `--yes-spend` unless a
separate exact-cost preflight has been reviewed and approved in a fresh message.

## 0. Acceptance variables and clean state

Choose installed local Ollama models and a free local port; no model or port is hardcoded:

```powershell
$LocalModel = Read-Host "Installed Ollama model tag for patient/judge"
$DemoModel = Read-Host "Installed Ollama model tag for the demo target"
$DemoPort = Read-Host "Unused localhost port"
$DevLicense = Read-Host "Absolute path to the signed development license"

$env:VITALPROBE_LOCAL_MODEL = $LocalModel
$env:VITALPROBE_JUDGE_MODEL = $LocalModel
$env:VITALPROBE_JUDGE = "ollama"
$env:DEMOBOT_PROVIDER = "ollama"
$env:DEMOBOT_MODEL = $DemoModel
$env:VITALPROBE_TARGET_URL = "http://127.0.0.1:$DemoPort/chat"
```

The agent resets `artifacts/vitalprobe.db` before handoff and records the reset in
`BUILD-LOG.md`. Confirm the active database does not yet exist:

```powershell
Test-Path artifacts/vitalprobe.db
```

Expected: `False`.

## 1. Engine layer and quality gates

This incorporates the original `TESTING.md` engine gate:

```powershell
uv sync --all-extras --locked
uv run ruff check .
uv run mypy --strict src tests examples/langgraph-patient-agent/patient_agent.py
uv run pytest -q
uv run vitalprobe --version
uv run vitalprobe validate --suite tests/data/suite
uv run pytest tests/test_judges.py -q
```

Expected: lint/type/tests pass, the CLI prints the development version, and the fixture
suite validates. Judge tests are mocked and spend nothing.

## 2. Start the real local-model demo target

In a second PowerShell terminal, set the same `$DemoModel` and `$DemoPort`, then run:

```powershell
$env:DEMOBOT_PROVIDER = "ollama"
$env:DEMOBOT_MODEL = $DemoModel
uv run --extra demo uvicorn vitalprobe.demo.demo_health_bot:app `
  --host 127.0.0.1 --port $DemoPort
```

Back in the first terminal:

```powershell
Invoke-RestMethod "http://127.0.0.1:$DemoPort/health"
```

Expected: status `ok`, mode `ollama`. Keep the target running through section 9.

## 3. Local naive audit, report, baseline, and history

```powershell
uv run vitalprobe run `
  --suite packs/emergency-core `
  --output artifacts/acceptance/naive-1 `
  --save-baseline artifacts/acceptance/baseline `
  --track
$FirstExit = $LASTEXITCODE

uv run vitalprobe run `
  --suite packs/emergency-core `
  --output artifacts/acceptance/naive-2 `
  --track
$SecondExit = $LASTEXITCODE

uv run vitalprobe compare `
  --baseline artifacts/acceptance/baseline/run.json `
  --current artifacts/acceptance/naive-2/run.json
$CompareExit = $LASTEXITCODE

uv run vitalprobe history --target $env:VITALPROBE_TARGET_URL
```

The naive target should produce genuine failures, so run exit `1` is expected and is not
an infrastructure error. Confirm both run directories contain `run.json` and `report.html`;
open the HTML and inspect transcript/evidence, tier wording, limitations, and print preview.
Compare exits `0` when no PASS→WARN/FAIL regression occurred, otherwise `1` and lists the
actual regressions. History must show two clean-slate tracked runs.

## 4. Free tier versus development license

Run from an isolated working directory so the repository `.env` cannot load the development
license. Merely assigning an empty environment value is not sufficient because removing the
value allows `.env` to supply it again.

```powershell
$RepoRoot = (Get-Location).Path
$VitalProbeExe = (Resolve-Path .venv/Scripts/vitalprobe.exe).Path
New-Item -ItemType Directory -Force artifacts/acceptance/free-cwd | Out-Null
Push-Location artifacts/acceptance/free-cwd
Remove-Item Env:VITALPROBE_LICENSE_FILE -ErrorAction SilentlyContinue
& $VitalProbeExe license show
& $VitalProbeExe license check mcp_server
$FreeGateExit = $LASTEXITCODE
& $VitalProbeExe mcp-serve
$FreeServerExit = $LASTEXITCODE
Pop-Location
```

Expected: free tier remains readable; both paid MCP checks refuse cleanly with exit `2`.

Restore the development license and test paid flags:

```powershell
$env:VITALPROBE_LICENSE_FILE = $DevLicense
uv run vitalprobe license verify $DevLicense
uv run vitalprobe license check learning
uv run vitalprobe license check law_mapping
uv run vitalprobe license check mcp_server
```

Expected: valid development tier and all three features unlocked. Never share the signing
seed; the signed development license is local and ignored.

## 5. Self-learning loop

Use the first tracked run ID:

```powershell
$RunId = (Get-Content artifacts/acceptance/naive-1/run.json | ConvertFrom-Json).run_id
uv run vitalprobe learn `
  --from-run $RunId `
  --variants 1 `
  --output artifacts/acceptance/drafts
Copy-Item packs/emergency-core/pack.yaml artifacts/acceptance/drafts/pack.yaml
uv run vitalprobe validate --suite artifacts/acceptance/drafts --release
$ReleaseLintExit = $LASTEXITCODE
```

Expected: failed cases produce draft variant files. Release validation exits `2` because
human approval is mandatory and every generated variant remains `status: draft`.

## 6. Law mapping and private pack

From the public repository root:

```powershell
uv run vitalprobe run `
  --suite ../packs/packs/crisis-protocols `
  --adapter-config ../packs/packs/crisis-protocols/adapter.default.yaml `
  --law-dir ../packs/law `
  --output artifacts/acceptance/law-mapped
```

A failure exit `1` is allowed. Open the report and confirm each failed mapped case shows
relevant requirement citations and the fixed “Not legal advice” disclaimer. Confirm no
private pack content has appeared in the public repository:

```powershell
git status --short
```

Expected: no private-pack files.

## 7. Multi-turn patient simulator

```powershell
uv run vitalprobe simulate `
  --persona personas/ambiguous-crisis.yaml `
  --adapter-config packs/emergency-core/adapter.default.yaml `
  --output artifacts/acceptance/simulator
```

Open the report. Confirm a complete multi-turn transcript, the scripted ideation reveal,
and computed `escalation_by_turn` plus `no_harmful_advice_any_turn` evidence.

## 8. MCP target adapter and paid product MCP server

Create a local stdio MCP target config without committing it:

```powershell
$PythonPath = (Resolve-Path .venv/Scripts/python.exe).Path.Replace("\", "\\")
@"
kind: mcp
transport: stdio
command:
  - "$PythonPath"
  - "-m"
  - "vitalprobe.demo.mcp_wrapper"
tool_name: chat
message_argument: message
"@ | Set-Content artifacts/acceptance/mcp-target.yaml

$env:DEMOBOT_PROVIDER = "scripted"
uv run vitalprobe run `
  --suite packs/emergency-core `
  --adapter-config artifacts/acceptance/mcp-target.yaml `
  --output artifacts/acceptance/mcp-target
```

A genuine finding exit `1` is allowed. Then run the MCP integration contract:

```powershell
$env:VITALPROBE_LICENSE_FILE = $DevLicense
uv run pytest tests/test_mcp.py -q
```

Expected: stdio target round trip passes; free-tier refusal and licensed server tool
surface (`run_suite`, `history`, `compare`, `learn`) pass.

## 9. LangGraph example

Restore the local-model target mode in terminal 2 if section 8 changed it, then run:

```powershell
$env:DEMOBOT_PROVIDER = "ollama"
uv run --extra examples python examples/langgraph-patient-agent/patient_agent.py `
  --persona personas/ambiguous-crisis.yaml `
  --adapter-config packs/emergency-core/adapter.default.yaml
uv run pytest tests/test_langgraph_example.py -q
```

Expected: the live example returns a canonical TestResult with trajectory evidence; parity,
patient-error routing, and no-hosted-integration tests pass.

## 10. Calibration status

The existing 50-row template is:

`../artifacts/calibration/labels_template.csv`

An AI-assisted preliminary review is available at:

`../artifacts/calibration/labels_reviewed.csv`

It contains 27 PASS, 3 WARN, and 20 FAIL verdicts. It is useful for finding obvious safety
problems, but it is not clinician validation and must not be presented as human ground truth.
Founder task F4 remains open until a qualified human reviewer verifies every verdict. Do not
pick a local winner or claim human agreement before that verification exists.

## 11. Cloud smoke gate — optional, blocked by money approval

Do **not** execute cloud judges during this script. OpenAI and Anthropic each require:

1. configured current model and token prices;
2. the CLI preflight showing the exact estimated dollar amount;
3. a fresh founder message explicitly approving that exact amount;
4. only then, one run with `--yes-spend`.

Skipping this optional step does not invalidate the zero-cost local product acceptance.

## 12. Founder acceptance record (F6)

After inspecting the generated reports, append one result to `BUILD-LOG.md`:

```text
P8 founder result: ACCEPTED | REJECTED
Date/machine:
Quality gates:
Surfaces checked:
Report review notes:
Defects found:
Cloud smoke: SKIPPED (no approval) | APPROVED exact amount and result
```

Only the founder records ACCEPTED or REJECTED. An agent may report its preflight separately
but must not impersonate this decision.
