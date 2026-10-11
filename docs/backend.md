# Backend and integration interfaces

The Python backend is a local execution library with CLI, loopback dashboard and MCP
interfaces. It is not a hosted audit API. Start with [quickstart](quickstart.md) and
use `uv run vitalprobe COMMAND --help` for exact options in your checkout.

## CLI reference

| Command | Purpose | Important inputs and limits |
|---|---|---|
| `validate` | Validate suite schema and duplicate IDs | `--suite`; `--release` additionally rejects draft cases |
| `run` | Execute cases, write canonical JSON and optional HTML | `--suite`, `--output`, optional `--adapter-config`, `--track`, `--strict-warn`, `--save-baseline`, `--format` |
| `compare` | Compare shared case IDs between canonical runs | `--baseline`, `--current`; new/removed cases are reported separately |
| `history` | Inspect locally tracked target runs | `--target` as shown in tracked output |
| `license show` | Inspect current local entitlement status | Configured license file; never prints a private signing seed |
| `license verify` | Verify a supplied license | Use command help for the file argument |
| `license check` | Check one feature entitlement | For example `mcp_server`; unavailable features exit 2 |
| `simulate` | Run a fictional multi-turn persona workflow | `--persona`, `--output`, optional `--adapter-config`, `--format`; configured local model |
| `calibrate` | Compare judges and supplied human labels | `--suite`, repeatable `--responses`/`--judges`, `--output`, optional `--labels` |
| `learn` | Generate draft variants from tracked failures | `--from-run`, `--variants`, `--output`; learning entitlement and configured local model |
| `dashboard` | Serve the local HTML interface | Configured loopback host/port; install dashboard extra |
| `mcp-serve` | Expose product tools over stdio | `mcp_server` entitlement required |

Cloud judging for `run` and `calibrate` requires explicit `--yes-spend` as well as provider
settings. Set accurate current token prices and inspect the estimate; zero configured
prices do not imply a free provider. No live call is needed for the deterministic path.

| Exit code | Meaning |
|---|---|
|0| Successful command; a run may contain warnings unless strict warnings are enabled |
|1| Failed run or regression according to the command's policy |
|2| Invalid configuration/input, unavailable entitlement or refused prerequisite |

Individual target errors remain `ERROR` records; inspect counts and error details as well
as the process exit status. Comparison's regression policy is narrower than all verdict
changes; see [test authoring](writing-tests.md).

## REST target contract

An adapter maps a fictional transcript to an authorized target. For the bundled fixture,
`POST /chat` accepts `{"message":"fictional scenario"}` and returns `{"reply":"response"}`.
Configure another target through YAML rather than changing runner source:

```yaml
method: POST
url_env: VITALPROBE_TARGET_URL
headers:
  Authorization: "Bearer ${VITALPROBE_TARGET_TOKEN}"
request_template:
  message: "{{last_user_message}}"
response_path: reply
timeout_s: 30
retry_attempts: 3
retry_wait_multiplier_s: 0.2
retry_wait_max_s: 2
```

`{{turns_json}}` as a whole template value becomes a structured list; inside longer text
it becomes serialized JSON. Dot paths select nested values, including numeric list
indexes. Unset header variables cause that header to be dropped, so confirm target
authentication before execution. Retries apply to network/server errors, not arbitrary
application responses. Operator-controlled URLs are not safe to expose as unrestricted
hosted input.

## MCP target versus product server

The target adapter invokes a configured MCP tool. An HTTP example is:

```yaml
kind: mcp
transport: http
url: http://127.0.0.1:8902/mcp
tool_name: chat
message_argument: message
timeout_s: 60
```

The URL is an example for an MCP server you must start separately. For stdio, configure
`transport: stdio` and an explicit trusted `command` list instead. Do not put secrets
in process arguments. The product-side `mcp-serve` interface is separate and license
gated; inspect its definitions in `src/vitalprobe/mcp/server.py`.

## Local dashboard routes

| Method and path | Purpose |
|---|---|
| `GET /` | Stored runs |
| `GET /runs/{run_id}` | Run details |
| `GET /history` | Target history |
| `GET /compare` | Baseline comparison |
| `GET /license` | Entitlement status |
| `GET /calibration` | Calibration artifacts |
| `GET /learning`, `GET /law` | Entitlement-gated draft/mapping views |
| `GET/POST /trigger-run` | Trigger the existing CLI and inspect its result |
| `GET /billing`, `POST /billing/checkout`, `POST /billing/portal`, `POST /billing/webhook` | Disabled-by-default localhost Stripe test lane only |

These are local HTML/application routes, not a public versioned SaaS API. API-documentation
endpoints are disabled for the dashboard. It has no general account or tenant authorization.
Do not expose it by changing the bind address. Triggered runs use fixed list arguments,
not a shell command assembled from input.

## Result and artifact contract

`RunResult` contains version/run ID/timestamps, redacted target metadata, suite metadata,
run verdict, counts and per-case results. A `TestResult` records ID/title/category/severity,
input turns, response, verdict, checks, optional judge evidence, law references and errors.
The serialized count key is `pass`, alongside `warn`, `fail` and `error`.

Consumers should validate against the public models in `src/vitalprobe/schema.py` and
handle optional fields. Keep raw artifacts intact; do not replace them with a dashboard
summary. Treat schema/version changes as compatibility changes with migration notes.
