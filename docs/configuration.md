# Configuration reference

Configuration has one owner per concern. Python settings are validated by
`src/vitalprobe/config.py`; `.env.example` is the safe environment inventory. REST
and MCP request details belong to adapter YAML. Frontend public build settings
belong to `web/src/config.ts` and `web/.env.example`; product copy belongs to
`web/src/data/`. Provider prompts and rubrics are maintained package data.

Copy `.env.example` to `.env` locally. Keep `.env`, signing material and licensed
content out of Git, artifacts, browser bundles and reports. Environment variables
can override settings; use explicit values in CI rather than relying on a developer's
shell. Frontend `VITE_*` values are public after compilation and must never hold secrets.

## Python environment inventory

The safe examples below are transcribed from `.env.example`, not from a private
configuration file. Blank secret fields mean unset; they are not working credentials.
Price estimates of zero are placeholders and do not establish that a provider is free.
The legacy fixture identifiers are retained exactly for command compatibility.

| Variable | Safe example | Purpose / group |
|---|---|---|
| `VITALPROBE_TARGET_URL` | `` | chatbot endpoint under test |
| `VITALPROBE_TARGET_TOKEN` | `` | optional bearer token (staging only, revocable) |
| `VITALPROBE_DB_PATH` | `artifacts/vitalprobe.db` | local SQLite run history (gitignored) |
| `VITALPROBE_LICENSE_FILE` | `` | optional path to an offline signed license |
| `VITALPROBE_JUDGE` | `none` | none / openai / anthropic / ollama |
| `VITALPROBE_JUDGE_MODEL` | `` | provider model ID; never hardcoded |
| `OPENAI_API_KEY` | `` | semantic judges (live calls require --yes-spend) |
| `ANTHROPIC_API_KEY` | `` | semantic judges (live calls require --yes-spend) |
| `VITALPROBE_OPENAI_BASE_URL` | `https://api.openai.com/v1` | semantic judges (live calls require --yes-spend) |
| `VITALPROBE_ANTHROPIC_BASE_URL` | `https://api.anthropic.com/v1` | semantic judges (live calls require --yes-spend) |
| `OLLAMA_HOST` | `http://localhost:11434` | semantic judges (live calls require --yes-spend) |
| `VITALPROBE_OPENAI_RESPONSES_PATH` | `/responses` | semantic judges (live calls require --yes-spend) |
| `VITALPROBE_ANTHROPIC_MESSAGES_PATH` | `/messages` | semantic judges (live calls require --yes-spend) |
| `VITALPROBE_ANTHROPIC_API_VERSION` | `2023-06-01` | semantic judges (live calls require --yes-spend) |
| `VITALPROBE_OLLAMA_CHAT_PATH` | `/api/chat` | semantic judges (live calls require --yes-spend) |
| `VITALPROBE_JUDGE_TIMEOUT_S` | `60` | semantic judges (live calls require --yes-spend) |
| `VITALPROBE_JUDGE_ESTIMATED_TOKENS_PER_CASE` | `1500` | semantic judges (live calls require --yes-spend) |
| `VITALPROBE_ANTHROPIC_MAX_TOKENS` | `500` | semantic judges (live calls require --yes-spend) |
| `VITALPROBE_LOCAL_MODEL` | `` | semantic judges (live calls require --yes-spend) |
| `VITALPROBE_LOCAL_JUDGE_MAX_ATTEMPTS` | `3` | initial attempt + two invalid-JSON reprompts |
| `VITALPROBE_JUDGE_OLLAMA_THINK` | `false` | keep reasoning off so local judges return pure JSON |
| `VITALPROBE_GENERATOR_TEMPERATURE` | `1.0` | draft-variant generator creativity (learning loop) |
| `VITALPROBE_GENERATOR_MAX_TOKENS` | `400` | output cap per draft-variant generation call |
| `VITALPROBE_SIMULATOR_TEMPERATURE` | `0.8` | synthetic-patient next-turn creativity |
| `VITALPROBE_SIMULATOR_MAX_TOKENS` | `200` | output cap per synthetic-patient turn |
| `VITALPROBE_JUDGE_INPUT_PRICE_PER_MILLION` | `0` | semantic judges (live calls require --yes-spend) |
| `VITALPROBE_JUDGE_OUTPUT_PRICE_PER_MILLION` | `0` | semantic judges (live calls require --yes-spend) |
| `VITALPROBE_DEMO_RESPONSES_FILE` | `` | optional YAML override for scripted target responses |
| `DEMOBOT_PROVIDER` | `scripted` | scripted / ollama |
| `DEMOBOT_MODEL` | `` | required for ollama; use a locally installed model tag |
| `VITALPROBE_DEMO_SYSTEM_PROMPT_FILE` | `` | optional text-file override |
| `VITALPROBE_DEMO_TEMPERATURE` | `0.2` | scripted health target |
| `VITALPROBE_DEMO_MAX_TOKENS` | `180` | scripted health target |
| `VITALPROBE_DEMO_TIMEOUT_S` | `120` | scripted health target |
| `VITALPROBE_DEMO_OLLAMA_THINK` | `false` | scripted health target |
| `VITALPROBE_RUNNER_CONCURRENCY` | `4` | runner |
| `VITALPROBE_DASHBOARD_HOST` | `127.0.0.1` | Local dashboard |
| `VITALPROBE_DASHBOARD_PORT` | `8800` | Local dashboard |
| `VITALPROBE_DASHBOARD_RUNS_DIR` | `artifacts/dashboard-runs` | output dirs for dashboard-triggered runs |
| `VITALPROBE_DASHBOARD_RUN_TIMEOUT_S` | `600` | kill a dashboard-triggered run after this many seconds |
| `VITALPROBE_DASHBOARD_OUTPUT_TAIL_CHARS` | `8000` | CLI output tail shown on the trigger result page |
| `VITALPROBE_DRAFTS_DIR` | `artifacts/drafts` | where `vitalprobe learn` drafts are read from |
| `VITALPROBE_LAW_DIR` | `` | law schema YAML dir from your paid pack bundle |
| `VITALPROBE_BILLING_SANDBOX_ENABLED` | `false` | Stripe sandbox technical validation ($0; never use live keys here) |
| `STRIPE_SECRET_KEY` | `` | Stripe sandbox technical validation ($0; never use live keys here) |
| `STRIPE_WEBHOOK_SECRET` | `` | Stripe sandbox technical validation ($0; never use live keys here) |
| `VITALPROBE_STRIPE_API_BASE_URL` | `https://api.stripe.com/v1` | Stripe sandbox technical validation ($0; never use live keys here) |
| `VITALPROBE_STRIPE_TIMEOUT_S` | `30` | Stripe sandbox technical validation ($0; never use live keys here) |
| `VITALPROBE_STRIPE_RECURRING_INTERVAL` | `month` | Stripe sandbox technical validation ($0; never use live keys here) |
| `VITALPROBE_STRIPE_RECURRING_INTERVAL_COUNT` | `1` | Stripe sandbox technical validation ($0; never use live keys here) |
| `VITALPROBE_STRIPE_PROCESSING_LEASE_S` | `60` | Stripe sandbox technical validation ($0; never use live keys here) |
| `VITALPROBE_STRIPE_AUTOMATED_PRICE_ID` | `` | Stripe sandbox technical validation ($0; never use live keys here) |
| `VITALPROBE_STRIPE_CLINICIAN_PRICE_ID` | `` | Stripe sandbox technical validation ($0; never use live keys here) |
| `VITALPROBE_STRIPE_AUTOMATED_UNIT_AMOUNT` | `5000` | Stripe sandbox technical validation ($0; never use live keys here) |
| `VITALPROBE_STRIPE_CLINICIAN_UNIT_AMOUNT` | `7000` | Stripe sandbox technical validation ($0; never use live keys here) |
| `VITALPROBE_STRIPE_CURRENCY` | `usd` | Stripe sandbox technical validation ($0; never use live keys here) |
| `VITALPROBE_STRIPE_WEBHOOK_TOLERANCE_S` | `300` | Stripe sandbox technical validation ($0; never use live keys here) |
| `VITALPROBE_BILLING_DB_PATH` | `artifacts/billing-sandbox.db` | Stripe sandbox technical validation ($0; never use live keys here) |
| `VITALPROBE_BILLING_LICENSE_DIR` | `artifacts/billing-sandbox/licenses` | Stripe sandbox technical validation ($0; never use live keys here) |
| `VITALPROBE_BILLING_SANDBOX_SIGNING_SEED_FILE` | `artifacts/billing-sandbox/sandbox-signing-seed.hex` | Stripe sandbox technical validation ($0; never use live keys here) |
| `VITALPROBE_BILLING_AUTOMATED_FEATURES` | `private_packs,law_mapping,learning` | Stripe sandbox technical validation ($0; never use live keys here) |
| `VITALPROBE_BILLING_CLINICIAN_FEATURES` | `private_packs,law_mapping,learning,rebranding,mcp_server` | Stripe sandbox technical validation ($0; never use live keys here) |

## Frontend environment inventory

| Variable | Safe example | Owner / purpose |
|---|---|---|
| `VITE_REPOSITORY_URL` | `https://github.com/Zahidulislam2222/vitalprobe` | Validated public site / development configuration |
| `VITE_REPORT_URL` | `/evidence/` | Validated public site / development configuration |
| `VITE_EVIDENCE_URL` | `/evidence/run.json` | Validated public site / development configuration |
| `SITE_DEV_HOST` | `127.0.0.1` | Validated public site / development configuration |
| `SITE_DEV_PORT` | `18831` | Validated public site / development configuration |

## Adapter and maintained-data configuration

REST adapters own `method`, `url` or `url_env`, `headers`, `request_template`,
`response_path`, `timeout_s` and retry fields. MCP adapters own transport, command
or URL, tool name, message argument and timeout. See the executable examples in
[backend interfaces](backend.md). A missing environment-backed header is omitted;
verify required authentication in your target before an audit. Never commit a real
header token into YAML. Secrets remain in the environment.

Change provider base URL, model, API version, token limits or prices through settings;
change request shape through adapter YAML; change judge rubrics/prompts through
maintained package data. Model IDs are deliberately not assigned a default.
`VITALPROBE_LOCAL_MODEL` selects the locally installed simulator/generator model;
`DEMOBOT_MODEL` selects the optional local target model.

The website's proposed pricing is maintained in `web/src/data/pages.json`. Stripe
sandbox amount/Price settings are separate validated payment expectations, expressed
in minor currency units. Update both deliberately when changing the product offer;
website text neither provisions a Price nor enables checkout.

## Operational checks

1. Start with `VITALPROBE_JUDGE=none` and the scripted target for a local-only run.
2. Verify target address and authentication before sending fictional cases.
3. Keep the dashboard bound to loopback. It has no public account or authorization layer.
4. Keep `VITALPROBE_BILLING_SANDBOX_ENABLED=false` except during the authorized,
   local, synthetic, test-key procedure in [Stripe validation](stripe-sandbox-e2e.md).
5. Before cloud judging, set the model, token estimates and current input/output prices;
   approve the provider cost independently of the CLI's `--yes-spend` flag.
6. Run the configuration hygiene and compliance tests after changing settings or data.

Do not record current secret values in public documentation or CI logs. Missing test
credentials and human approvals are release blockers, not configuration defaults.
