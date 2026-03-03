# DnD Sim Project Execution Protocol

Purpose: Let Ridge run this project end-to-end with minimal nudging, high reliability, and Discord-visible progress.

---

## Core Rules

1. **Always work from TODO.md** (single source of truth).
2. **One chunk = one commit** (small, atomic, recoverable).
3. **No silent progress** — every chunk gets a Discord-visible launch + completion/failure update.
4. **Parallelize safely** — only non-overlapping file lanes run in parallel.
5. **If blocked, reroute** — do not stall the whole project.
6. **All coding in sub-agents** — never do implementation work in the main session. Main context is for conversation, planning, and orchestration only.

---

## Task States

Each TODO item should be treated as one of:
- `ready`
- `running`
- `blocked`
- `needs-review`
- `done`

Ridge loop:
1) pick highest-priority `ready`
2) spawn sub-agent with strict scope
3) validate + commit
4) update TODO state
5) repeat until no `ready` items remain

---

## Chunk Template (mandatory)

Every sub-agent task must specify:

- **Scope:** exact files/functions in/out of scope
- **Deliverable:** exact expected output
- **Validation commands:** show/list/fight/tests
- **Commit message:** predefined
- **TODO updates:** which checkboxes/progress note to modify
- **Deferred list:** explicit out-of-scope items

Max target runtime: **15–25 minutes** per chunk.

---

## Sub-Agent Model Lanes

### How to spawn sub-agents

**Codex** — use `exec` with `pty:false`, `background:true`, feeding prompt via stdin:
```bash
cat /tmp/prompt.txt | codex exec --full-auto - > /tmp/codex_chunk.log 2>&1 &
```
Monitor with `process action:poll` and `exec command:"tail -20 /tmp/codex_chunk.log"`.

**Opus (Claude sub-agent)** — use `sessions_spawn` with `runtime: "subagent"`, `mode: "run"`:
```
sessions_spawn(
  task: "...",
  runtime: "subagent",
  mode: "run",
  model: "anthropic/claude-opus-4-6"
)
```
Opus sub-agents run isolated from the main context window. Use for anything that would burn tokens in main session.

**Key rule: Never do implementation in the main session.** Write the prompt, spawn the agent, monitor from main.

---

### Codex lane (implementation)
Use for:
- mechanics code (`sim/*.py`)
- bug fixes
- tests
- refactors

### Opus lane (parallel support)
Use for:
- build YAML generation (no mechanics overlap)
- audit/planning docs
- findings writeups
- TODO reconciliation
- anything that needs reading + synthesizing lots of code/data

Never assign overlapping edit surfaces to both models at the same time.

---

## Concurrency Guardrails

Before launching parallel sub-agents, verify lane separation:

- If Codex edits `sim/*.py`, Opus must only edit `data/builds/*.yaml` or docs.
- If Codex edits loader + tests, Opus can do findings + TODO updates only.
- If overlap risk exists, serialize.

---

## Failure Handling

If a chunk fails:
1. Retry once with narrower scope.
2. If fail again, split into two smaller chunks.
3. Mark blocker in TODO (`blocked`) with exact reason.
4. Continue with other `ready` work.

Never let one blocker halt total progress.

---

## Discord Update Contract

For every chunk:

### Launch
- label
- model
- purpose
- expected finish window

### Completion
- commit hash
- files changed
- validations passed
- next chunk queued

### Failure
- exact failure mode
- what was preserved
- recovery plan + next run

Keep updates concise and frequent enough that Kirt never has to ask for status.

---

## Quality Gates (before closing any chunk)

- `./dnd-sim show <new/changed builds>` passes
- at least one smoke fight for mechanics changes
- targeted tests pass (or full suite when practical)
- no temp files accidentally committed
- TODO updated to reflect reality

---

## Endgame Definition (Level 5 project)

Project complete when:
1. All level-5 mechanics in TODO are done or explicitly deferred with reason
2. All planned level-5 builds exist and validate
3. `rank --tag level5` executed with stable output
4. FINDINGS.md updated with level-5 tier analysis
5. Projects folder synced
6. Git pushed

---

## Immediate Next-Step Queue (auto-run)

1. Finish any currently running chunks.
2. Reconcile TODO checkboxes against actual commits.
3. Execute remaining `ready` mechanics/build/ranking tasks in chunk order.
4. Update findings and publish final status summary.

---

Owner: Ridge
Mode: Autonomous with visible checkpoints
