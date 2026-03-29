# Nuclear Clean — Level Reset
# Run before any build

Reference CLAUDE.md Rule 20.

## STEP 1 — Find all actors
```json
{"command": "find_actors", "params": {"search": ""}}
```
Record count.

## STEP 2 — Delete all actors
```json
{"command": "batch_delete_actors", "params": {
  "labels": [list from find_actors]
}}
```

## STEP 3 — Verify clean
```json
{"command": "find_actors", "params": {"search": ""}}
```
Should return 0.

## STEP 4 — save_all
Persist the clean state. Do NOT call save_level
on untitled levels (F013).

## STEP 5 — Report
Deleted: [n] actors
Remaining: [n] actors
Level clean: yes/no
