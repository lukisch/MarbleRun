# llmauto -- LLM Automation Framework (Marble Runs)

Universal automation tool for LLM agents.
Chain execution, prompt management, autonomous work loops.

**Author:** Lukas Geiger | **License:** MIT | **Python:** 3.10+

---

## What is llmauto?

llmauto orchestrates autonomous LLM agent chains ("marble runs"). Multiple agents work in sequence -- workers execute tasks, reviewers check results, controllers coordinate -- passing context via handoff files.

Think of it as a marble run: the marble (context) rolls from link to link in a loop, with each link being an LLM agent with a specific role and prompt.

### Key Features

- **Chain Execution:** Define multi-agent chains in JSON, run them autonomously
- **Marble Run Pattern:** Sequential agent loops with handoff-based context passing
- **Multi-Model Support:** Mix Claude Opus, Sonnet, and Haiku in a single chain
- **Role System:** Workers, Reviewers, Controllers with skip-if-not-assigned patterns
- **State Management:** Persistent round counters, handoff files, stop/resume support
- **Pipe Mode:** Single LLM calls from the command line
- **Background Execution:** Start chains in separate terminal windows
- **Telegram Notifications:** Optional status updates via Telegram bot
- **Zero Dependencies:** Pure Python stdlib (subprocess, json, pathlib, sqlite3)

### Requirements

- Python 3.10+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (`claude` command available in PATH)

---

## Installation

```bash
git clone https://github.com/lukisch/llmauto.git
cd llmauto

# Run directly (no install needed)
python -m llmauto --help

# Or install as package
pip install -e .
llmauto --help
```

---

## Quick Start

### 1. Create a Chain Definition

Create a JSON file in `chains/` (e.g. `chains/my-chain.json`):

```json
{
  "description": "Simple worker-reviewer loop",
  "mode": "loop",
  "max_rounds": 5,
  "runtime_hours": 2,
  "links": [
    {
      "name": "worker",
      "role": "worker",
      "model": "claude-sonnet-4-5-20250929",
      "prompt": "worker_prompt.txt"
    },
    {
      "name": "reviewer",
      "role": "reviewer",
      "model": "claude-opus-4-6-20250918",
      "prompt": "reviewer_prompt.txt",
      "continue": true
    }
  ]
}
```

### 2. Create Prompt Templates

Place prompt files in `prompts/` (e.g. `prompts/worker_prompt.txt`):

```text
You are a software development worker. Read the handoff file at
state/my-chain/handoff.md for your current assignment.

Execute the assigned tasks, then write a handoff for the reviewer:
- What you completed
- What needs review
- Any blockers
```

### 3. Run the Chain

```bash
# Start in foreground
python -m llmauto chain start my-chain

# Start in background (opens new terminal window)
python -m llmauto chain start my-chain --bg

# Check status
python -m llmauto chain status my-chain

# Stop gracefully (after current link finishes)
python -m llmauto chain stop my-chain "Reason for stopping"

# View logs
python -m llmauto chain log my-chain 50

# Reset state (back to round 0)
python -m llmauto chain reset my-chain
```

### 4. Pipe Mode (Single Calls)

```bash
# Direct prompt
python -m llmauto pipe "Explain quantum computing in 3 sentences"

# From file
python -m llmauto pipe -f prompt.txt

# With model override
python -m llmauto pipe "Hello" --model claude-opus-4-6-20250918
```

---

## Chain Architecture

### How Marble Runs Work

```
Round N:
  [Link 1: Worker]  --executes tasks-->  writes handoff.md
                                              |
  [Link 2: Reviewer] --reads handoff-->  reviews + fixes --> writes handoff.md
                                              |
  [Link 3: Controller] --reads handoff-->  coordinates --> writes handoff.md
                                              |
                                        Round N+1 ...
```

### Shutdown Conditions

A chain stops when any of these conditions are met:

- `runtime_hours` exceeded
- `max_rounds` reached
- `status.txt` contains "STOPPED" or "ALL_DONE"
- `max_consecutive_blocks` consecutive BLOCK states
- Manual stop via `llmauto chain stop`

### State Files

Each chain maintains persistent state in `state/<chain-name>/`:

| File | Purpose |
|------|---------|
| `status.txt` | READY, RUNNING, STOPPED, ALL_DONE, BLOCKED |
| `round_counter.txt` | Current round number |
| `handoff.md` | Context handoff between links |
| `start_time.txt` | When the chain was started |

### Chain Configuration Schema

| Field | Type | Description |
|-------|------|-------------|
| `description` | string | Human-readable description |
| `mode` | string | `loop` (repeat), `once` (single pass), `deadend` (single pass) |
| `max_rounds` | int | Maximum number of complete cycles |
| `runtime_hours` | float | Maximum runtime in hours |
| `deadline` | string | Hard deadline (ISO date) |
| `links` | array | Ordered list of chain links |

### Link Configuration

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique link identifier |
| `role` | string | `worker`, `reviewer`, `controller` |
| `model` | string | Claude model ID |
| `prompt` | string | Prompt template filename or inline text |
| `continue` | bool | Use `--continue` flag (persistent session) |
| `fallback_model` | string | Fallback model if primary fails |
| `until_full` | bool | Add context-limit awareness suffix |
| `telegram_update` | bool | Send Telegram notification after this link |

---

## Advanced Patterns

### Skip-If-Not-Assigned

For chains where a controller assigns work to either an Opus or Sonnet worker:

```json
{
  "links": [
    {"name": "controller", "role": "controller", "model": "opus"},
    {"name": "opus-worker", "role": "worker", "model": "opus"},
    {"name": "sonnet-worker", "role": "worker", "model": "sonnet"}
  ]
}
```

The controller writes `ASSIGNED: opus` or `ASSIGNED: sonnet` in the handoff.
The non-assigned worker reads the handoff and skips immediately.

### Continue Mode

Links with `"continue": true` maintain a persistent Claude Code session
in a dedicated workspace directory. Each invocation continues the previous
conversation, preserving full context.

### Template Variables

Prompts support `{HOME}` (Windows path) and `{BASH_HOME}` (Unix path)
placeholders that are resolved at runtime.

---

## Project Structure

```
llmauto/
  llmauto.py              Main CLI entry point
  config.json             Global configuration
  core/
    runner.py             Claude CLI wrapper (subprocess, env, fallback)
    config.py             Config management (chains, global)
    state.py              State management (handoff, rounds, shutdown)
  modes/
    chain.py              Marble run engine
  chains/                 Chain definitions (JSON)
  prompts/                Prompt templates per chain
  state/                  Runtime state per chain (gitignored)
  logs/                   Runtime logs (gitignored)
  templates/              Chain pattern templates
  docs/                   Documentation
```

---

## Global Configuration (config.json)

| Setting | Default |
|---------|---------|
| `default_model` | `claude-sonnet-4-5-20250929` |
| `default_permission_mode` | `dontAsk` |
| `default_allowed_tools` | Read, Edit, Write, Bash, Glob, Grep |
| `default_timeout_seconds` | 7200 (2h) |
| `telegram.enabled` | false |

---

## Included Example Chains

llmauto ships with several production-tested chain configurations:

| Chain | Pattern | Description |
|-------|---------|-------------|
| `worker-reviewer-loop` | Template | Basic 2-link worker/reviewer pattern |

See `chains/` for the full set of included chain definitions.

---

## License

MIT License. See [LICENSE](LICENSE).

---

## Author

Lukas Geiger -- [github.com/lukisch](https://github.com/lukisch)
