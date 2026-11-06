# Lesson 4 practical application: Sales Report Tutor

Build the same small reporting workflow with **Agents API**, **Agents SDK**, and **Responses API**. The application reads fictional sales figures, calculates verified totals, and explains gross margin. Its purpose is to make runtime ownership and state visible while keeping the business task constant.

Start with the offline comparison. It runs with Python's standard library, requires no account, and makes no API calls. Optional live mode calls the actual OpenAI services. Offline answers are fixed teaching responses, clearly marked as simulations; they do not demonstrate actual model reasoning or remote persistence.

## What students learn

| Lesson | Where it appears in the application |
|---|---|
| 4 / 4A: choose where the loop runs | Each run prints its loop, state, and tool boundaries. |
| 4B: managed sessions | `managed_turn()` creates a remote session and saves its `managed_session_id`; another run with the same label submits a follow-up. |
| 4C: orchestration in your application | `sdk_turn()` uses an SDK Runner, a local function tool, and SQLite history. The model is still remote. |
| 4D: direct integration | `direct_response()` sends a model request and explicitly chains later requests. |
| 4E: different state mechanisms | Runtime and mode have separate storage folders and distinct identifiers. |
| 4F: prototype and measure | `compare` runs the same task across all three approaches and writes a scorecard. |

This example intentionally chooses one state strategy for each runtime. SDK applications can use other storage or server-managed continuation; Responses applications can use manual history or Conversations. The choices here are teaching examples, not restrictions.

## Requirements and quick start

Use Python 3.11 or later. Open a terminal in this new subfolder:

```powershell
cd "Practical Application Example"
python app.py compare
```

If your terminal already points to this subfolder, omit `cd`. macOS/Linux users can substitute `python3` for `python`.

The comparison prints three labeled reports and writes a fresh scorecard under `storage/`. Expected sample totals are:

```text
Revenue: EUR 20000.00
Cost: EUR 11200.00
Gross profit: EUR 8800.00
Gross margin: 44.00%
```

The sample dataset is fictional. The formula is `(20000 - 11200) / 20000 * 100 = 44%`. Margin divides by revenue; markup divides by cost. Calculations use `Decimal` to avoid binary floating-point arithmetic in these totals. Zero revenue produces an undefined margin rather than dividing by zero.

## Configure live mode

Create an isolated environment and install the optional live dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Use `.venv/bin/python` for the equivalent commands on macOS/Linux. Activation is optional; using the environment's Python directly also avoids PowerShell activation-policy problems.

Configure your own OpenAI API key in the terminal session:

```powershell
$env:OPENAI_API_KEY = "your_openai_api_key"
$env:OPENAI_MODEL = "gpt-6-astra"
```

On macOS/Linux:

```bash
export OPENAI_API_KEY="your_openai_api_key"
export OPENAI_MODEL="gpt-6-astra"
```

`.env.example` documents the variables; the application does **not** automatically load `.env` files. Use `--model` to override `OPENAI_MODEL`. The lesson's model is the default; your account must have access to it. Agents API beta also needs project access and appropriate session/model permissions. See the [official Agents API quickstart](https://developers.openai.com/api/docs/guides/agents-api/quickstart). Live requests use your API billing.

No key is included in the application, and it does not read the lesson's narration credentials. The SDK path disables tracing for this classroom example. Managed mode uses `environment={"type": "none"}` and sends text only; it creates no hosted sandbox and cannot run the local Python function tool.

## Run the application

### 1. Explore offline state

```powershell
python app.py run --runtime sdk --session student1
python app.py run --runtime sdk --session student1 --question "Explain the margin again."
python app.py state --runtime sdk --session student1
```

The second run reports turn 2. Offline mode saves facts and turns in JSON. It simulates the intended boundaries without instantiating `SQLiteSession`, creating an API session, or generating a real response ID. Offline text stays fixed even if you ask another question.

Try `managed` and `responses` with the same session label and inspect their separate files. Try a new label to start a fresh conversation.

### 2. Use Responses API directly

```powershell
.\.venv\Scripts\python.exe app.py run --mode live --runtime responses --session responses1
.\.venv\Scripts\python.exe app.py run --mode live --runtime responses --session responses1 --question "How is that different from markup?"
```

The application saves `previous_response_id`. The first request includes the data; the second uses the saved response chain. Instructions are sent on each request. This lab sets `store=True` to support continuation. A stored response identifier represents a response chain, not a running managed agent session. See [conversation state](https://developers.openai.com/api/docs/guides/conversation-state).

### 3. Run the SDK in your application

```powershell
.\.venv\Scripts\python.exe app.py run --mode live --runtime sdk --session sdk1
.\.venv\Scripts\python.exe app.py run --mode live --runtime sdk --session sdk1 --question "What was our gross profit?"
```

The runner can call `get_sales_facts` locally. Its trace lists actual tool invocations; it does not pretend a tool was called when it was not. History lives in `storage/live/sdk/sdk_history.sqlite`, partitioned by each conversation's storage key. The JSON file is a readable application ledger, while SQLite is the history loaded by the SDK. See [running agents and session memory](https://developers.openai.com/api/docs/guides/agents/running-agents).

### 4. Delegate the loop to a managed session

```powershell
.\.venv\Scripts\python.exe app.py run --mode live --runtime managed --session managed1
.\.venv\Scripts\python.exe app.py run --mode live --runtime managed --session managed1 --question "Explain our gross margin to a beginner."
```

The first request creates a remote session. The second opens its event stream, submits input to the saved session ID, waits for the root turn's outcome, and retrieves saved items. The app prints event types and stores retrieved items in the state JSON. It distinguishes successful completion from idle, cancellation, failure, or a disconnected stream. See [run and continue sessions](https://developers.openai.com/api/docs/guides/agents-api/sessions) and [event handling](https://developers.openai.com/api/docs/guides/agents-api/sessions/events).

### 5. Compare a prototype

```powershell
python app.py compare
.\.venv\Scripts\python.exe app.py compare --mode live
```

Each comparison creates fresh conversations, uses the same initial request and sample dataset, and writes `storage/comparison_<id>_scorecard.json`. An unavailable runtime is recorded as an error without preventing the others from running; the command returns a nonzero exit code if any runtime fails.

Elapsed time is measured wall time, including network and processing in live mode. Offline timings measure simulation overhead and are **not model benchmarks**. `quality_score` and `cost_usd` stay `null` until students supply evaluated results and actual billing information. A single run is not a meaningful performance ranking.

## Files and persisted state

```text
Practical Application Example/
  app.py              CLI commands, runtime selection, timing, scorecards
  core.py             Verified totals, prompts, state paths, atomic JSON saves
  runtimes.py         Offline simulation and the three live implementations
  data/sales.json     Fictional input data
  test_app.py         Offline and fake-client contract tests
  requirements.txt    Optional live packages
  .env.example        Configuration template; contains no credentials
  storage/            Created when you run the application; ignored by Git
    offline/<runtime>/<label>.json
    live/managed/<label>.json
    live/responses/<label>.json
    live/sdk/<label>.json
    live/sdk/sdk_history.sqlite
```

Use `--storage PATH` to choose another local destination, `--data PATH` for another dataset with the same schema, and `--question TEXT` to change the request. Run `python app.py --help` for all options. Labels accept letters, digits, `_`, and `-` only. Run one process per session label; concurrent writes to the same classroom session are outside this example's scope.

Data and tool definitions are fixed for an ongoing exercise. After changing the dataset, use a **new session label**: the Responses and managed paths retain the first turn's facts, while the SDK tool reads the file on each invocation. Offline mode retains its initial facts too. Changing models also requires a new session label.

## How the application was built

### Step 1: separate business logic from the runtime

`core.sales_facts()` loads the sample input and computes the totals before asking a model to explain them:

```python
profit = revenue - cost
margin = profit / revenue * 100 if revenue else None
```

The implementation uses `Decimal`, validates nonnegative finite inputs, and formats values for the model. The same verified facts drive all three approaches, so runtime differences are easier to see. The prompt asks the tutor to explain the figures without inventing their causes.

### Step 2: make the direct request explicit

The central pattern in `direct_response()` is:

```python
params = dict(model=model, instructions=INSTRUCTIONS, store=True)
params["input"] = question if previous else initial_input(question, facts)
if previous:
    params["previous_response_id"] = previous
result = client.responses.create(**params)
```

Python decides when to make another request. It stores the new identifier only after a completed text response. No function tool is configured on this path: the application supplies facts as context.

### Step 3: move orchestration to an SDK runner

The SDK path wraps the local data reader as a callable tool and attaches persistent history:

```python
@function_tool
def get_sales_facts() -> str:
    return json.dumps(sales_facts(facts_path))

session = SQLiteSession(storage_key, str(database))
result = await Runner.run(agent, question, session=session, max_turns=6)
```

The agent is configured with this tool and instructions. The SDK handles model/tool steps inside this process. `max_turns` bounds the runner loop. The application owns the Python runtime, tool implementation, database, and deployment. The model itself runs remotely. Specialist handoffs can be added later; this initial example uses one agent to keep the runtime comparison clear.

### Step 4: move the harness to the managed service

The managed path creates a text-only session:

```python
sessions.create(
    agent={"model": model, "instructions": INSTRUCTIONS},
    environment={"type": "none"},
    input=initial_input(question, facts),
    stream=True,
)
```

The implementation collects the result and saves the session identifier. For later turns it subscribes before sending input, and saves a per-message idempotency key before submission. `consume_managed()` only accepts a completed root turn as success. Remote saved items provide the durable transcript; the local JSON maps a student label to that remote resource.

### Step 5: keep state and output artifacts distinct

`state_path()` places mode and runtime in separate folders. Offline handles cannot be accidentally reused as remote IDs. `save_json()` writes a temporary file then replaces the destination, reducing the chance of a partially written state file. JSON transcripts are application artifacts; they are not interchangeable with the SDK history database or remote API resources.

## Tests and classroom exercises

Run the tests without installing live dependencies:

```powershell
python -m unittest -v
```

Tests check the real margin calculation, zero revenue, invalid numbers, session isolation, persistence across reloads, response chaining, and managed failure/completion handling. Fake API clients never contact OpenAI. They test application behavior, not account access or the service itself. With live packages installed, an additional integration test exercises the real SDK function tool and SQLite persistence using a fake runner, without a model request. It is skipped in the dependency-free environment.

Suggested exercises:

1. Run two turns with each runtime and identify the state mechanism used to answer the follow-up.
2. Add a product to `data/sales.json`, choose new session labels, and verify the recalculated totals.
3. Evaluate the same five questions per runtime. Score factual accuracy against the verified totals, clarity, and whether margin is confused with markup.
4. Repeat live runs, measure median wall time, and use actual usage information to calculate costs. Record recovery and operational effort separately.
5. Extend the SDK with a specialist agent and handoff. Observe that orchestration still lives in your application.

## Troubleshooting, recovery, and cleanup

| Symptom | Next step |
|---|---|
| No `OPENAI_API_KEY` | Set it in the same terminal, or use offline mode. |
| Missing module | Use the virtual environment's Python and install `requirements.txt`. |
| `beta.agents` missing | Upgrade `openai`; this path requires the SDK's Agents API beta support. |
| Authentication, access, or model error | Check your key, project permissions, billing, API availability, and model access. Use a fresh session label after changing the model. |
| Network error or timeout | Inspect saved state before retrying; a remote request may have completed even if the response was lost. |
| Invalid state JSON | Keep the file for inspection and start with a new label. |
| Pending managed submission | Follow the recovery steps below; the app refuses an automatic duplicate submission. |

For a managed interruption, inspect the remote session with your saved ID before retrying:

```python
from openai import OpenAI
client = OpenAI()
session = client.beta.agents.sessions.retrieve("your_saved_session_id")
items = client.beta.agents.sessions.items.list("your_saved_session_id", order="asc")
print(session.to_json())
for item in items:
    print(item.to_json())
```

If a pending message was accepted, reconcile the local transcript with the saved items and remove `pending_submission` from its JSON only after resolving the outcome. If it was not accepted, reuse the saved idempotency key and the exact same text when resubmitting through `sessions.events.create`; do not create a new key for an uncertain submission. This classroom app deliberately leaves uncertain outcomes for inspection instead of blindly retrying them. It sets SDK HTTP retries to zero on its direct client. SDK Runner requests follow that SDK's own retry behavior.

Use new labels for a fresh local exercise. To remove old local artifacts, delete only the session JSON files you no longer need; SDK history also exists in its SQLite database. Deleting local files does not delete remote sessions or stored responses. After saving any desired results, remote resources can be deleted explicitly:

```python
client.beta.agents.sessions.delete("your_saved_session_id")
client.responses.delete("your_saved_response_id")
```

Delete each stored response you intend to remove; deleting the last response does not mean the full chain was deleted. This example is a single-user teaching app. A deployed service must derive session access from authenticated users; a student-provided label is not authorization.

## Verification scope

The offline comparison and automated fake-client tests can be run without API credentials. Live adapters follow the official documentation linked above, checked on November 6, 2026. Their imports and method signatures were checked with `openai==3.46.0` and `openai-agents==0.24.0`, pinned in `requirements.txt`. Live service behavior, account permissions, and model availability require a configured account and are not established by offline tests. Capture `python -m pip freeze` after validating a live classroom environment if a full dependency snapshot is needed.
