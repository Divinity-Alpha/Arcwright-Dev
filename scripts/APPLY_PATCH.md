# Intent Server Patch — Apply Instructions
**Target:** `scripts/intent_server.py`  
**Goal:** 85.4% → ~92-96% on the 48-test user simulation suite  
**Fixes:** 4 changes, all self-contained, no architectural changes

---

## Before You Start

```bash
# Backup current intent server
cp scripts/intent_server.py scripts/intent_server_backup_20260312.py

# Confirm intent server is not currently running
# (kill it if so — it will be restarted after patch)
```

---

## Step 1 — Add COMMAND_WHITELIST, COMMAND_REQUIRED_PARAMS, validate_plan()

**Where:** Near the top of `intent_server.py`, after imports, before prompt constants.

**What to add:** Copy the entire block from `intent_server_patch.py`:
- `COMMAND_WHITELIST` set
- `COMMAND_REQUIRED_PARAMS` dict  
- `validate_plan()` function

**Then add the call site** in both `handle_classify()` and `handle_refine()`,
immediately after `plan = json.loads(raw)` (or wherever you parse the LLM JSON output):

```python
plan = validate_plan(plan)
if plan.get("validation_warnings"):
    for w in plan["validation_warnings"]:
        log("WARN", w)
```

---

## Step 2 — Replace CLASSIFY_PROMPT

Find the existing `CLASSIFY_PROMPT = """..."""` constant and replace it entirely
with the `CLASSIFY_PROMPT` from `intent_server_patch.py`.

Key changes:
- Explicit CREATE vs MULTI rule with 8 concrete examples
- "Complex single Blueprint = CREATE" stated multiple ways
- Asset name guessing warning

---

## Step 3 — Replace REFINE_PROMPT

Find the existing `REFINE_PROMPT = """..."""` constant and replace it entirely
with the `REFINE_PROMPT` from `intent_server_patch.py`.

Key changes:
- `operations[]` wrapper rule shown in every example
- "NEVER return flat params" stated twice
- Full command reference with correct signatures
- `rename_asset` shown with both `old_name` and `new_name`
- `batch_delete_actors` shown with `labels` as a list

---

## Step 4 — Replace Stage 2 Discovery Condition

Find in `handle_classify()` (or wherever Stage 2 runs):

```python
# CURRENT — replace this:
if mode in ("MODIFY", "MULTI"):
    discovery = run_stage2_discovery(targets, mode)
```

```python
# REPLACE WITH:
if should_run_discovery(mode, summary, targets):
    discovery = run_stage2_discovery(targets, mode)
```

Add the `should_run_discovery()` function from `intent_server_patch.py` 
near the other helper functions.

---

## Step 5 — Verify and Test

```bash
# Start intent server
python scripts/intent_server.py &

# Quick sanity check — send a test request
python -c "
import socket, json
s = socket.socket()
s.connect(('localhost', 13380))
req = json.dumps({'command': 'classify', 'text': 'Create a torch with a point light at 5000 intensity'})
s.send((req + '\n').encode())
resp = json.loads(s.recv(4096))
print(json.dumps(resp, indent=2))
s.close()
"
# Expected: mode=CREATE (not MULTI)

# Run full 48-test suite
python tests/run_user_sim.py

# Target: >= 177/192 (92%)
```

---

## Expected Test Impact by Category

| Category | Before | Expected After | Why |
|---|---|---|---|
| Setup | 25/32 (78%) | 27/32 (84%) | S.04 whitelist fix, S.07 discovery fix |
| Create | 31/40 (78%) | 38/40 (95%) | CREATE/MULTI prompt fix (+7 intent points) |
| Modify | 51/60 (85%) | 55/60 (92%) | operations[] format fix (+4 points) |
| Query | 20/20 (100%) | 20/20 (100%) | No change |
| Multi-Step | 18/20 (90%) | 19/20 (95%) | operations[] spillover |
| Conversational | 19/20 (95%) | 20/20 (100%) | prompt clarity |
| **Total** | **164/192 (85.4%)** | **~179/192 (93%)** | |

---

## If Score Does Not Improve as Expected

Check these in order:

1. **validate_plan() not being called** — add print statement to confirm it fires
2. **CLASSIFY_PROMPT not fully replaced** — diff against patch file
3. **LLM still returning MULTI for single assets** — add 2-3 more examples to CLASSIFY_PROMPT 
   specifically for the failing test cases
4. **operations[] still flat** — check if your JSON parsing strips the wrapper before validate_plan runs

The patch file has detailed comments on each fix. Reference `intent_server_backup_20260312.py` 
to compare before/after if needed.
