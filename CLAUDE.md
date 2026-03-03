# BlueprintLLM — Claude Code Project Context

> **Doc Version:** 2.3
> **Last Updated:** 2026-03-02
> **Owner:** Divinity Alpha
> **Repo:** github.com/Divinity-Alpha/BlueprintLLM

### CLAUDE.md Changelog
| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-02-26 | Initial creation — hardware, pipeline, training config, backup system |
| 1.1 | 2026-03-01 | Added UE 5.7 Plugin section, DSL parser, node mapping table |
| 1.2 | 2026-03-01 | Plugin pin resolution, test results, macro node support |
| 1.3 | 2026-03-02 | Updated roadmap to 8 phases, added compliance checker architecture |
| 1.4 | 2026-03-02 | Epochs changed from 2→3, Strategic Rules section added (16 rules) |
| 1.5 | 2026-03-02 | Added CLAUDE.md Update Policy |
| 1.6 | 2026-03-02 | Added GA=4 rule (5b), Golden Config block, pre-flight verification (13b) |
| 1.7 | 2026-03-02 | Added changelog and versioning system. Rule 10 strengthened (CLAUDE.md is source of truth) |
| 1.8 | 2026-03-02 | Added Plugin Testing Log with per-test tracking. Expanded test results table with node/connection counts. |
| 1.9 | 2026-03-02 | TCP Command Server added (port 13377). Python client library + test runner. Strategic Rule 17. Roadmap Phase 2 updated. |
| 2.0 | 2026-03-02 | Training timeout 28800→43200 (12h). Strategic Rule 18 (size timeout for cold-cache pace). Golden Config updated. |
| 2.1 | 2026-03-02 | Command Server OPERATIONAL (8/8 tests pass). data_literal pin defaults implemented. L12_20 IR fixed. Plugin Testing Log updated. |
| 2.2 | 2026-03-02 | Training uses heartbeat-based stall detection (1800s), no fixed duration timeout. Removed training_timeout from config. Rule 18 replaced. |
| 2.3 | 2026-03-02 | Added parallel development roadmap (Track A: LLM, Track B: Command Server). Replaced fixed training timeout with heartbeat-based stall detection. Added Strategic Rule 18. |

**Claude Code: When you update this file, increment the version number and add a changelog entry. Always print the current doc version when starting a session.**

---

## What This Project Is

BlueprintLLM is a self-improving AI system that trains LLMs to generate **validated, structurally correct** Unreal Engine 5 Blueprint DSL from natural language descriptions. The core innovation is the **teaching loop** — a closed-loop cycle of train → examine → grade → create lesson → retrain that targets specific weaknesses each iteration.

The long-term vision is a platform that trains validated AI models for ANY structured language (not just Blueprints). Blueprints are the proof-of-concept. The teaching loop infrastructure is language-agnostic.

---

## Hardware Configuration (Current — February 2026)

| Component | Details |
|---|---|
| **GPU 0 (PyTorch cuda:0)** | NVIDIA RTX PRO 6000 Blackwell Max-Q Workstation Edition, 96GB VRAM |
| **GPU 1 (PyTorch cuda:1)** | NVIDIA GeForce RTX 5070 Ti, 16GB VRAM |
| **System RAM** | 64GB DDR5 @ 4000 MT/s |
| **nvidia-smi ordering** | GPU 0 = 5070 Ti, GPU 1 = PRO 6000 (reversed from PyTorch) |
| **CUDA Version** | 13.1 |
| **Driver** | 591.74 |
| **Compute Capability** | PRO 6000 = sm_120 (Blackwell), 5070 Ti = sm_100 |

### CRITICAL Hardware Notes

- **Monitors are connected to the 5070 Ti, NOT the PRO 6000.** Display rendering must stay off the training card.
- **PyTorch and nvidia-smi order GPUs differently.** PyTorch cuda:0 = PRO 6000. nvidia-smi GPU 0 = 5070 Ti. Always use PyTorch ordering in scripts.
- **CUDA_VISIBLE_DEVICES=0 targets the PRO 6000** in our scripts (PyTorch ordering).
- **Blackwell (sm_120) has compatibility issues** with bitsandbytes 4-bit NF4 quantization. 4-bit does NOT work. Use 8-bit quantization.

### GPU Role Assignment

| GPU | Role | What Runs Here |
|---|---|---|
| **PRO 6000 (cuda:0)** | ML Training & Inference | 70B model training, exams, inference, all heavy ML work |
| **5070 Ti (cuda:1)** | Display + Light Tasks | Monitor rendering, UE5 editor, dashboard, 8B quick testing, general computing |

### Quantization — What Works and What Doesn't

| Method | Status | Notes |
|---|---|---|
| bitsandbytes 4-bit NF4 | ❌ FAILS | Segfaults or extreme slowdown on Blackwell sm_120 |
| bitsandbytes 8-bit | ✅ WORKS | 67.7GB VRAM, loads in ~125s, 3.4 tok/s inference |
| GPTQ (gptqmodel) | ❌ FAILS | Version incompatibility with transformers 5.x |
| AWQ (autoawq) | ❌ FAILS | Pins old torch version, won't build |
| bfloat16 (no quant) | ✅ WORKS | For small models (3B, 8B) that fit in VRAM |

**ALWAYS use `load_in_8bit=True` for the 70B model. Never attempt 4-bit on this hardware.**

---

## Software Environment

| Package | Version | Notes |
|---|---|---|
| Python | 3.11.9 | Installed to C:\Program Files\Python311 |
| PyTorch | 2.10.0+cu130 | CUDA-enabled build |
| transformers | 4.57.6 | Downgraded from 5.x for gptqmodel compat |
| bitsandbytes | 0.49.2 | 8-bit works, 4-bit does not on Blackwell |
| peft | Installed | QLoRA adapter management |
| trl | Installed | Training with SFTTrainer |
| accelerate | Installed | Multi-device management |
| CUDA Toolkit | 13.1 | Matches driver |
| Git | 2.53.0 | |
| Node.js | 24.14.0 | For Claude Code |
| Visual Studio 2022 | Community | C++ build tools for CUDA compilation |

### Virtual Environment
- Location: `C:\BlueprintLLM\venv\`
- Always activate before running: `.\venv\Scripts\activate`
- Python on PATH requires disabling Windows app execution aliases

---

## Project Structure

```
C:\BlueprintLLM\
├── scripts/                    # All pipeline scripts (numbered 01-20+)
│   ├── utils/                  # Shared utilities
│   ├── 01_analyze_blueprint_clipboard.py
│   ├── 02_dsl_to_training_entry.py
│   ├── 03_generate_synthetic_data.py
│   ├── 04_train_blueprint_lora.py      # Main training script
│   ├── 05_auto_translate_export.py
│   ├── 06_validate_dsl.py              # DSL parser/validator
│   ├── 07_inference.py                 # Interactive inference
│   ├── 08_generate_system_prompt.py
│   ├── 09_evaluate_model.py
│   ├── 10_training_dashboard.py
│   ├── 11_pipeline_orchestrator.py     # Autonomous pipeline
│   ├── 12_run_exam.py                  # Exam runner
│   ├── 13_lesson_to_training.py        # Lesson integration
│   ├── 14_update_dashboard.py          # Dashboard generator
│   ├── 15_stop_signal.py               # Graceful shutdown
│   ├── 16_backup.py                    # Backup utility
│   ├── 17_scheduled_backup.py          # Watchdog backup
│   ├── 18_restore_backup.py            # Restore from backup
│   ├── 19_training_health_monitor.py   # Automated health checks
│   ├── 20_deduplicate_dataset.py
│   ├── error_handler.py                # Retry logic, timeout handling
│   ├── pipeline_logger.py              # Step-numbered logging
│   ├── backup_utils.py
│   └── system_prompt.txt               # Training system prompt
├── datasets/
│   ├── train.jsonl                     # Main training data (~728KB, 1400+ examples)
│   ├── validation.jsonl                # Eval set (~21KB)
│   ├── auto_translated.jsonl           # Auto-translated examples
│   ├── synthetic_train.jsonl           # Synthetic training data
│   └── lesson_02_data.jsonl            # Lesson 2 additions
├── lessons/
│   ├── lesson_01.json                  # First teaching lesson (20 prompts)
│   └── lesson_02.json                  # Second teaching lesson
├── models/                             # Created by training (adapter weights)
├── exams/                              # Exam results
├── logs/                               # Training logs, pipeline logs
│   ├── pipeline_live_state.json        # Live dashboard state file
│   ├── pipeline_heartbeat              # Heartbeat for stall detection
│   └── step_timing_history.json        # Historical step timings for ETA
├── dashboard/
│   ├── index.html                      # Main training observatory
│   └── live.html                       # Live pipeline monitor
├── backups/                            # Local backups (primary)
├── offload/                            # Disk offload folder for model loading
├── pipeline_config.json                # Pipeline configuration
└── .claude/
    └── CLAUDE.md                       # THIS FILE
```

---

## Pipeline Step Numbering System

ALL pipeline output, logs, dashboard, and communication uses this canonical numbering:

| Step | Name | Duration | Auto? |
|---|---|---|---|
| **1** | **Data Foundation** | | |
| 1.1 | Export UE5 Blueprints | Manual | ❌ |
| 1.2 | Convert to DSL format | ~2 min | ✅ |
| 1.3 | Validate with parser | ~1 min | ✅ |
| 1.4 | Format as training JSONL | ~1 min | ✅ |
| 1.5 | Split train/validation sets | ~30 sec | ✅ |
| **2** | **Pre-Flight Checks** | | |
| 2.1 | Check STOP_SIGNAL | ~1 sec | ✅ |
| 2.2 | Verify GPU availability | ~5 sec | ✅ |
| 2.3 | Verify dataset integrity | ~10 sec | ✅ |
| 2.4 | Pre-training backup | ~2 min | ✅ |
| **3** | **Model Loading** | | |
| 3.1 | Load base model from cache | ~2 min (125s for 70B 8-bit) | ✅ |
| 3.2 | Apply quantization (8-bit) | Included in 3.1 | ✅ |
| 3.3 | Apply QLoRA adapters | ~30 sec | ✅ |
| 3.4 | Load tokenizer | ~10 sec | ✅ |
| 3.5 | Load training dataset | ~15 sec | ✅ |
| 3.6 | Configure trainer | ~5 sec | ✅ |
| **4** | **Training** | | |
| 4.1 | Training epoch 1 begin | ~1 sec | ✅ |
| 4.2 | Training epoch 1 steps | ~1-2 hrs | ✅ |
| 4.3 | Epoch 1 eval checkpoint | ~2-5 min | ✅ |
| 4.4 | Training epoch 2 begin | ~1 sec | ✅ |
| 4.5 | Training epoch 2 steps | ~1-2 hrs | ✅ |
| 4.6 | Epoch 2 eval checkpoint | ~2-5 min | ✅ |
| 4.7 | Final eval | ~2-5 min | ✅ |
| **5** | **Post-Training** | | |
| 5.1 | Verify loss health | ~10 sec | ✅ |
| 5.2 | Save LoRA adapter | ~1-2 min | ✅ |
| 5.3 | Save training config | ~2 sec | ✅ |
| 5.4 | Save training log | ~2 sec | ✅ |
| 5.5 | Post-training backup | ~2 min | ✅ |
| 5.6 | Run health monitor | ~10 sec | ✅ |
| **6** | **Examination** | | |
| 6.1 | Load exam prompts | ~5 sec | ✅ |
| 6.2 | Load trained model for inference | ~2-3 min | ✅ |
| 6.3 | Generate DSL prompt N/N | ~15-30 sec each | ✅ |
| 6.N+3 | Compare all outputs vs expected | ~5 sec | ✅ |
| 6.N+4 | Score node mastery | ~5 sec | ✅ |
| 6.N+5 | Categorize errors | ~5 sec | ✅ |
| 6.N+6 | Save exam results | ~2 sec | ✅ |
| **7** | **Claude Grading** | | |
| 7.1 | Upload exam results | Manual | ❌ |
| 7.2 | Analyze error patterns | ~5 min | ❌ Claude |
| 7.3 | Identify weak nodes | ~2 min | ❌ Claude |
| 7.4 | Write corrections | ~10 min | ❌ Claude |
| 7.5 | Create next lesson file | ~10 min | ❌ Claude |
| **8** | **Lesson Integration** | | |
| 8.1 | Load new lesson | ~2 sec | ✅ |
| 8.2 | Generate prompt variations | ~1 min | ✅ |
| 8.3 | Validate all DSL | ~30 sec | ✅ |
| 8.4 | Merge into training set | ~5 sec | ✅ |
| 8.5 | Update dataset stats | ~2 sec | ✅ |
| **9** | **Dashboard & Finalize** | | |
| 9.1 | Update main dashboard | ~5 sec | ✅ |
| 9.2 | Milestone backup | ~2 min | ✅ |
| 9.3 | Log to pipeline history | ~2 sec | ✅ |
| 9.4 | Update step timing history | ~2 sec | ✅ |
| 9.5 | Cycle complete | ~1 sec | ✅ |

**ALWAYS use this numbering in console output, log files, and dashboard displays.**
Format: `[STEP X.Y] STARTING/COMPLETE/PROGRESS: Description`

---

## Training Configuration (70B on PRO 6000)

```json
{
  "gpu": 0,
  "base_model": "meta-llama/Meta-Llama-3.1-70B",
  "epochs": 3,
  "learning_rate": 0.00005,
  "lora_rank": 64,
  "lora_alpha": 128,
  "batch_size": 1,
  "gradient_accumulation_steps": 4,
  "max_seq_length": 2048,
  "quantization": "8bit",
  "use_4bit": false,
  "use_8bit": true,
  "auto_backup": true,
  "max_scheduled_backups": 5,
  "stop_on_error": true,
  "stall_kill_seconds": 1800,
  "prompt_timeout_seconds": 120,
  "heartbeat_interval_seconds": 60
}
```

### Key Training Decisions
- **Learning rate 0.00005** (halved from 8B's 0.0001) — larger models need smaller LR
- **3 epochs** — proven in v6. 2 epochs caused shallow learning and regressions in v5. 3 gives 50% more repetition, critical for replay buffer data to stick.
- **LoRA rank 64** — good balance of quality vs training speed
- **Gradient accumulation 4** — effective batch size of 4. v7 accidentally used 8 and regressed. Do not change.
- **8-bit quantization** — only method that works on Blackwell hardware
- **Stall detection: heartbeat-based** — kill if no new training log output for 1800s (30 min). No fixed total duration timeout. Training time grows with dataset size; fixed timeouts cause false kills.

### ⚠️ GOLDEN CONFIG (v6 proven — do not deviate without owner approval)
These exact values produced 95.5% syntax / 90% similarity. Any deviation requires explicit justification:
```
epochs: 3
learning_rate: 0.00005
batch_size: 1
gradient_accumulation_steps: 4
lora_rank: 64
lora_alpha: 128
max_seq_length: 2048
quantization: 8bit (load_in_8bit=True)
training_timeout: heartbeat (kill if no log output for 1800s, no fixed duration limit)
```
**If pipeline_config.json contains different values, update it to match this block before training.**

---

## Strategic Rules (MANDATORY — Read Before Any Action)

These rules were learned through hard experience. **Any Claude session (claude.ai or Claude Code) must follow these rules. Do not override without explicit owner approval.**

### Training Rules
1. **ALWAYS use 3 epochs.** 2 epochs causes shallow learning and regressions (proven v5→v6). This is non-negotiable.
2. **ALWAYS include replay buffer data** when adding new lessons. Double L01-L02 examples in the dataset to prevent catastrophic forgetting of fundamentals.
3. **ALWAYS run full L01-L12+ exam suite** after any training run, not just the new lesson. Regressions hide in lessons you didn't test.
4. **NEVER skip the correction lesson pattern.** New training = new exam = grade = targeted corrections. No shortcuts.
5. **8-bit quantization only.** 4-bit does not work on Blackwell. Don't try it.
5b. **gradient_accumulation_steps=4, NOT 8.** v6 achieved 95.5% with GA=4. v7 regressed to 92.8% when GA was changed to 8. Do not change this without explicit owner approval.

### Plugin / API Rules
6. **Pin name mismatches go in the plugin, not the model.** The LLM's job is understanding logic. The plugin's job is UE internal naming.
7. **Float→Double remapping stays in the plugin.** This is an engine version detail, not a model concern.
8. **Delete existing Blueprint assets before re-import.** Overwriting causes crashes.

### Process Rules
9. **Update CLAUDE.md immediately** when a strategic decision is made. If it's not in CLAUDE.md, it doesn't exist for future sessions.
10. **Update pipeline_config.json to match CLAUDE.md** whenever config changes. The config file and CLAUDE.md must always agree. **If they disagree, CLAUDE.md is the source of truth — update pipeline_config.json to match.**
11. **When giving instructions to Claude Code**, always say "Reference CLAUDE.md for all configuration details and strategic rules" — this forces the other session to read the rules.
12. **Every version gets a grading report** saved to `/mnt/user-data/outputs/` and committed to git. This is the historical record.
13. **When in doubt, search CLAUDE.md first.** The answer is probably already documented.
13b. **Before every training run, verify the actual config.** Claude Code must print the effective training config (epochs, gradient_accumulation_steps, learning_rate, batch_size, quantization) and confirm it matches CLAUDE.md BEFORE training starts. If any value differs, stop and fix it. Do not proceed with mismatched config.

### Architecture Rules
14. **The LLM generates DSL. The parser validates. The plugin translates.** Keep these concerns separated. Don't bleed UE implementation details into training data.
15. **The compliance checker validates against the DSL spec, not against UE internals.** Third-party tools shouldn't need to know UE pin names.
16. **New node types discovered during plugin testing** get added to node_map.py first, then to the training curriculum if the model doesn't already handle them.
17. **The Command Server reuses existing import logic.** `import_from_ir` must call the same `FDSLImporter::ParseIR` + `FBlueprintBuilder::CreateBlueprint` as the Tools menu. One code path, two entry points. Never duplicate Blueprint creation logic in the server.
18. **Training uses heartbeat-based stall detection, not fixed timeouts.** Never set a fixed training duration timeout. Monitor training logs for activity — if no new output for 30 minutes, the process is stalled. If logs are still being written, let training continue regardless of total elapsed time.

### CLAUDE.md Update Policy

**Update immediately when:**
- A training config changes (epochs, learning rate, dataset composition, anything in the JSON block)
- Something breaks or doesn't work (add to "Things That Have Broken Before")
- A new strategic rule emerges from a mistake
- The plugin gains a new capability or node type support
- Any decision is made that would change what Claude Code does next

**Update after each training cycle:**
- Add a row to the version/training history table
- Document any new correction patterns or techniques
- Update accuracy numbers and status fields

**Update at phase transitions:**
- When a phase moves from "in progress" to "complete"
- When the roadmap timeline shifts based on reality
- When a major architectural decision changes

**Don't update for:**
- Mid-conversation brainstorming that hasn't led to a decision
- One-off debugging details
- Information already captured in grading reports

**Simple rule: If it would change what Claude Code does, update now. If it's historical record, update at the next training cycle. If it's a strategic shift, update at the phase boundary.**

---

### Overfitting Warning Signs (from v1 experience)
- Train loss < 0.05 = almost certainly memorizing
- Train loss << eval loss (gap > 50%) = memorizing
- Loss 0.013 with regurgitated format rules = classic overfit (v1 failure mode)
- v2 at 2 epochs: loss 0.260, eval accuracy 95.6% > train accuracy 93.5% = healthy generalization

---

## Backup System

### Three-Tier Architecture

**Tier 1: Local Backups (C:\BlueprintLLM\backups\)**
- Milestone backups after training/exam completion (NEVER auto-deleted)
- Pre-training safety backups (keep last 3)
- Scheduled watchdog backups every 6 hours (keep last 5)

**Tier 2: Secondary SSD Backup (D:\BlueprintLLMBackup\)**
- **Mirror of ALL local backups** — automatic duplicate
- Protects against primary drive failure
- MUST be updated every time a local backup runs
- Captures everything NOT in Git:
  - `models/` — trained LoRA adapter weights (the most critical files)
  - `datasets/` — curated training data (train.jsonl, validation.jsonl, etc.)
  - `lessons/` — teaching loop lesson files
  - `exams/` — exam results and history
  - `logs/` — training logs, pipeline history, timing data
  - `backups/backup_manifest.json` — integrity checksums
  - `pipeline_config.json` — current configuration
  - `dashboard/` — generated dashboard HTML

**Tier 3: Git (github.com/Divinity-Alpha/BlueprintLLM)**
- All scripts (scripts/*.py)
- Documentation
- System prompts
- NOT model weights, datasets, or logs (too large / contains training data)

### Backup Implementation

Every backup script MUST:
1. Save to `C:\BlueprintLLM\backups\` (primary)
2. Mirror to `D:\BlueprintLLMBackup\` (secondary SSD)
3. Include SHA256 checksums in backup_manifest.json
4. Log the backup to `logs/backup_log.txt`

```python
# Standard backup paths
PRIMARY_BACKUP = r"C:\BlueprintLLM\backups"
SECONDARY_BACKUP = r"D:\BlueprintLLMBackup"

# After any backup to PRIMARY_BACKUP:
import shutil
shutil.copytree(backup_path, os.path.join(SECONDARY_BACKUP, backup_name), dirs_exist_ok=True)
```

### What Gets Backed Up (per backup)
- `adapter_model.safetensors` (~500-800MB for 70B 8-bit LoRA)
- `adapter_config.json`
- `training_config.json`
- `datasets/train.jsonl` + `validation.jsonl`
- `lessons/lesson_*.json`
- `exams/exam_*.jsonl`
- `logs/*.log`
- `pipeline_config.json`
- `requirements.txt` snapshot

### What Does NOT Need Backup
- Base LLaMA model (re-downloads from HuggingFace, ~130GB cache)
- Python packages (reinstalls from requirements.txt)
- Scripts (in Git)
- venv/ folder (recreate with `python -m venv venv`)

---

## GPU Offloading Strategy

### Tasks for PRO 6000 (cuda:0) ONLY
- All 70B model operations (training, inference, exams)
- Any operation involving the trained LoRA adapter
- Heavy ML compute

### Tasks for 5070 Ti (cuda:1) — Offload These
- Dashboard generation and serving (no GPU needed, CPU task)
- DSL validation/parsing (CPU task)
- Dataset processing and deduplication (CPU task)
- File I/O operations (backups, log writing)
- 8B model quick testing (if needed for comparison)
- UE5 Editor (when user is working in Unreal)
- Display rendering (monitors connected here)

### Implementation
```python
# For training/inference scripts:
os.environ["CUDA_VISIBLE_DEVICES"] = "0"  # PRO 6000 only

# For quick 8B testing on secondary GPU:
os.environ["CUDA_VISIBLE_DEVICES"] = "1"  # 5070 Ti only

# For non-GPU tasks (dashboard, parsing, backups):
# Don't set CUDA_VISIBLE_DEVICES — these don't use GPU
```

### IMPORTANT: Never run on both GPUs simultaneously for training
Multi-GPU training requires matched VRAM. 96GB + 16GB = broken. Always single-GPU training on the PRO 6000.

---

## Error Handling Philosophy

### Retry Logic
- Default 3 retries with exponential backoff (30s, 60s, 120s)
- Timeout: model load = 600s, training steps = no hard timeout, inference = 120s per prompt
- CUDA OOM: clear cache, reduce batch size, retry
- Single exam prompt timeout: skip and continue (don't fail entire exam)
- Network timeout: retry with backoff

### Stall Detection
- Heartbeat file updated every 60 seconds during training
- Stall threshold: 1800s (30 min) for training steps
- Training has legitimate pauses during eval checkpoints (5-10 min)
- HeartbeatCallback in training fires on: on_log, on_evaluate, on_save

### Graceful Shutdown
- STOP_SIGNAL file approach: `python scripts/15_stop_signal.py stop`
- Pipeline checks between major steps (not mid-training batch)
- Current operation completes, checkpoint saves, then exits
- Resume with: `python scripts/11_pipeline_orchestrator.py --resume`

### Resume Capability
- On fatal error: saves state to `logs/pipeline_resume_state.json`
- `--resume` flag picks up from failed step
- Always creates safety backup before resuming

---

## Teaching Loop — How It Works

The teaching loop is the core methodology. Each cycle targets specific weaknesses found in the previous exam.

### The Loop
1. Train model on dataset (Steps 2-5)
2. Exam: test model against lesson prompts (Step 6)
3. Grade: analyze errors, identify weak nodes (Step 7 — requires Claude)
4. Create lesson: write targeted examples for weak areas (Step 7)
5. Integrate: add lesson data to training set (Step 8)
6. Repeat from step 1

### Error Taxonomy
- **Missing nodes** — model didn't generate a required node type
- **Missing EXEC** — execution flow connections missing
- **Missing DATA** — data pin connections missing
- **Format errors** — DSL syntax violations
- **Extra lines** — model generated unnecessary content

### Node Mastery Tracking
- 42+ target node types tracked individually
- Per-node accuracy from exam scores
- ≥85% = mastered (minimum threshold, not ship quality)
- ≥95% per-node with validation retry = good product quality
- ≥97% per-node = production quality

### Health Monitor Alerts
- Dataset > 2500 examples: suggest reducing to 1 epoch
- Train loss < eval loss × 0.5: overfitting detected
- Node stuck 3+ cycles: change teaching approach
- Node regresses after mastery: catastrophic forgetting
- Lesson data > 40% of total: risk of teaching to the test

---

## Training History

| Version | Date | Model | Hardware | Loss | Accuracy | Notes |
|---|---|---|---|---|---|---|
| v1 | 2026-02-22 | 8B | RTX 4070 12GB | 0.013 | N/A | OVERFIT — too many epochs, regurgitated format rules |
| v2 | 2026-02-23 | 8B | RTX 4070 12GB | 0.260 | 93.5% train / 95.6% eval | Healthy — 2 epochs, good generalization |
| v3 | 2026-02-25 | 3B | RTX 4070 12GB | 1.07 | N/A | FAILED — only 10 steps before graceful stop, model too small |
| v4 | 2026-02-26 | 70B | PRO 6000 96GB | TBD | TBD | FIRST 70B RUN — currently in progress |

---

## Console Output Standards

### Verbose Step Logging
```
[14:30:05] [STEP 2.1] STARTING: Pre-training backup
[14:30:07] [STEP 2.1] COMPLETE: Pre-training backup (2.1s)
           Saved to backups/pre_train_v4_20260226/
[14:30:07] [STEP 3.1] STARTING: Load base model | ETA: 2m 5s
           Model: meta-llama/Meta-Llama-3.1-70B (8-bit)
[14:32:12] [STEP 3.1] COMPLETE: Load base model (2m 5s)
           VRAM: 67.7 GB allocated on cuda:0
```

### Progress Updates During Training
```
[14:45:08] [STEP 4.2] PROGRESS: 7.2% (100/1393) | Elapsed: 10m | Remaining: 2h 5m | loss: 0.8432
```

### Error Format
```
[14:50:00] [STEP 6.3] ERROR: Prompt 7/20 timed out after 120s — skipping
[14:50:00] [STEP 6.3] RETRY 1/3: Attempting with reduced max_tokens
```

---

## Product Roadmap (Summary)

| Phase | Timeline | Goal |
|---|---|---|
| **1: Blueprint Mastery** | Now → Month 3 | 95%+ mastery on all node types ✅ (achieved v6) |
| **2: UE5 Plugin** | Months 1-3 | End-to-end DSL → Blueprint in UE Editor ✅ OPERATIONAL — TCP Command Server 8/8 tests pass |
| **3: Direct Claude Integration** | Months 3-6 | Claude.ai generates Blueprints with minimal human interaction |
| **4: DSL Open Standard & Compliance Checker** | Months 4-8 | Publish spec, build validator API, enable community tools |
| **5: Community Ecosystem** | Months 6-12 | Third-party tools, marketplace, certification tiers |
| **6: Multi-System** | Months 8-14 | Behavior Trees, Materials, Animation, Niagara, Sequences |
| **7: Platform** | Months 14-20 | Teaching loop as a service for other structured languages |
| **8: Scale** | Months 20-30 | Multi-industry, $3-10M ARR |

---

## Grand Vision

### The Origin Story
This project exists because Claude.ai helped design an exciting game, but building the Blueprints to its instructions was so tedious that there had to be a better way. The gap between "AI can describe game logic" and "AI can build game logic" is exactly what BlueprintLLM fills.

### Phase 3: Direct Claude Integration
Once the UE plugin is proven end-to-end, the workflow becomes:
1. User describes gameplay in natural language to Claude
2. Claude generates DSL (already 95.5% accurate with fine-tuned model)
3. Parser converts DSL to IR automatically
4. Plugin creates real Blueprints in UE Editor
5. User goes from game design doc to functional prototype in hours, not weeks

Longer term, Claude could output `.blueprint.json` IR files directly — no fine-tuned model needed, just the parser and plugin on the user's end.

### Phase 4: DSL Open Standard & Compliance Checker
What we've actually built is three things:
1. **A DSL specification** for describing Blueprint logic in text
2. **A validation pipeline** that can check compliance
3. **A proven training methodology** showing LLMs can learn the format

The plan:
- Formalize the DSL spec as a versioned document (v1.0) after end-to-end is proven
- Build a **Compliance Checker** — a web API or CLI tool that accepts DSL and returns pass/fail with specific violations
- The checker validates: syntax validity, node type mapping, connection integrity, pin name resolution, variable declarations, event presence
- Scoring mirrors our exam grading: syntax %, similarity %, node mapping rate
- Compliance checker can also validate third-party tool output (see Phase 5)

### Phase 5: Community Ecosystem & Marketplace
Publish the DSL spec as an open standard so other developers can build compliant tools:
- Visual editors, node-based web tools, other AI integrations
- Tools for other engines that compile the same DSL to their native format
- The DSL becomes the lingua franca for text-based Blueprint description

**Certification Tiers:**
| Tier | Requirement | Description |
|---|---|---|
| **Basic** | Pass L01-L06 node types | Core events, flow control, variables |
| **Advanced** | Pass full node set | All 179+ node types mapped correctly |
| **Certified** | Pass all eval tests | All 11 eval tests at 90%+ accuracy |

**Marketplace Model:**
- Developers submit their tool
- Tool generates DSL for a standard test suite (like our eval tests)
- Compliance checker scores it automatically
- Tools that pass get listed with their tier badge
- Automated re-testing on spec version updates

**Compliance Checker Architecture:**
```
Third-party tool output (DSL text)
    ↓
Compliance API / CLI
    ├── Syntax validation (regex + grammar check)
    ├── Node type mapping (against NODE_MAP)
    ├── Connection integrity (reference validation)
    ├── Pin name resolution (known aliases + UE pin names)
    ├── Variable declaration check
    └── Event presence check
    ↓
Score Report
    ├── Syntax validity %
    ├── Node mapping rate %
    ├── Connection integrity %
    ├── Overall compliance tier (Basic/Advanced/Certified)
    └── Specific violations with line numbers
```

This is buildable on top of the existing parser — it already validates syntax, checks node types, verifies connections, and flags unmapped types. Wrapping it into an API with tiered scoring is straightforward.

---

## Things That Have Broken Before (Lessons Learned)

1. **Overfitting at low epoch counts looks like success** — v1 had loss 0.013 which seemed great but was memorization. Watch for train loss << eval loss.
2. **Windows PowerShell needs execution policy change** — `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
3. **New PATH entries require new terminal session** — close and reopen PowerShell after installing anything.
4. **Windows app execution aliases intercept `python` command** — disable in Settings → Apps → Advanced app settings → App execution aliases.
5. **bitsandbytes 4-bit does NOT work on Blackwell** — always use 8-bit.
6. **PyTorch and nvidia-smi order GPUs differently** — always verify with `torch.cuda.get_device_name(0)`.
7. **Stall detection too aggressive** — training has legit long pauses. Use 1800s threshold, not 600s.
8. **3B model cannot generate valid Blueprint DSL** — too small for structured output. Minimum 8B, ideally 70B.
9. **transformers 5.x breaks gptqmodel** — if needed, stay on transformers 4.57.x.
10. **HuggingFace login doesn't persist across sessions sometimes** — use `login(add_to_git_credential=False)` and re-login if downloads fail.
11. **Fixed training timeouts don't scale.** 28800s (8h) was too short for cold CUDA cache; 43200s (12h) was a guess that would break for larger datasets. Replaced with heartbeat-based stall detection: if no heartbeat for 1800s, kill. Training runs as long as needed. Config: `stall_kill_seconds_training` in `pipeline_config.json`.

---

## UE 5.7 Plugin (Phase 2) — WORKING as of 2026-03-02

### Architecture
The pipeline is: **Natural Language → Fine-tuned LLM → DSL Text → Python Parser → JSON IR → C++ UE Plugin → Real Blueprint Asset**

### Components

| Component | Location | Status |
|---|---|---|
| DSL Parser (Python) | `scripts/dsl_parser/` | ✅ 99.9% map rate, 179 node types |
| Node Map | `scripts/dsl_parser/node_map.py` | ✅ 179 NODE_MAP + 24 ALIASES |
| UE 5.7 C++ Plugin | `ue_plugin/BlueprintLLM/` | ✅ Full node/connection support + TCP Command Server |
| Test IR Files | `test_ir/*.blueprint.json` | 8 files, 8/8 passing |

### Plugin Files
```
ue_plugin/BlueprintLLM/
├── BlueprintLLM.uplugin
├── Source/BlueprintLLM/
│   ├── BlueprintLLM.Build.cs          (+ Networking, Sockets modules)
│   ├── Public/
│   │   ├── BlueprintLLMModule.h       (Tools menu + server lifecycle)
│   │   ├── DSLImporter.h              (JSON IR → structs)
│   │   ├── BlueprintBuilder.h         (structs → UBlueprint)
│   │   └── CommandServer.h            (TCP server, LogBlueprintLLM category)
│   └── Private/
│       ├── BlueprintLLMModule.cpp     (auto-starts server on plugin load)
│       ├── DSLImporter.cpp
│       ├── BlueprintBuilder.cpp
│       └── CommandServer.cpp          (5 commands, game thread dispatch)
└── Content/

scripts/mcp_client/
├── __init__.py
├── blueprint_client.py                (TCP client library)
├── verify.py                          (5-step connectivity test)
└── test_runner.py                     (batch IR import + report)
```

### How to Build
```powershell
# Copy plugin into UE project
xcopy /E /I C:\BlueprintLLM\ue_plugin\BlueprintLLM "C:\Junk\BlueprintLLMTest\Plugins\BlueprintLLM"

# Build editor target
& "C:\Program Files\Epic Games\UE_5.7\Engine\Build\BatchFiles\Build.bat" BlueprintLLMTestEditor Win64 Development "C:\Junk\BlueprintLLMTest\BlueprintLLMTest.uproject"

# Open editor, Tools → BlueprintLLM → Import DSL Blueprint
# IMPORTANT: Delete existing generated blueprints before re-import
```

### Supported Node Types

| Category | UE Class | Creation Method | Notes |
|---|---|---|---|
| Events | UK2Node_Event | Native | BeginPlay, ActorBeginOverlap, AnyDamage, Tick |
| InputAction | UK2Node_InputAction | Native | Requires Input Action configured in project |
| CustomEvent | UK2Node_CustomEvent | Native | |
| CallFunction | UK2Node_CallFunction | SetFromFunction() | PrintString, math, gameplay statics, etc. |
| Branch | UK2Node_IfThenElse | Native | |
| Sequence | UK2Node_ExecutionSequence | Native + AddInputPin() | Dynamic output count from connections |
| MultiGate | UK2Node_MultiGate | Native + AddInputPin() | Dynamic output count from connections |
| FlipFlop | UK2Node_MacroInstance | Macro (StandardMacros) | Loaded from EditorBlueprintResources |
| DoOnce | UK2Node_MacroInstance | Macro (StandardMacros) | Loaded from EditorBlueprintResources |
| Gate | UK2Node_MacroInstance | Macro (StandardMacros) | Loaded from EditorBlueprintResources |
| ForLoop | UK2Node_MacroInstance | Macro (StandardMacros) | Loaded from EditorBlueprintResources |
| WhileLoop | UK2Node_MacroInstance | Macro (StandardMacros) | Loaded from EditorBlueprintResources |
| ForEachLoop | UK2Node_MacroInstance | Macro (StandardMacros) | Loaded from EditorBlueprintResources |
| Cast | UK2Node_DynamicCast | Native | Object pin set to AActor type |
| VariableGet | UK2Node_VariableGet | Native | Property created on BP class |
| VariableSet | UK2Node_VariableSet | Native | Property created on BP class |

### Pin Name Resolution (FindPinByDSLName — 11 strategies)

The DSL uses short/generic pin names that don't match UE's internal names. The resolver tries these in order:

1. **Exact match** — FindPin(DSLName, Direction)
2. **Exact match (any direction)** — FindPin(DSLName) without direction filter
3. **Known aliases** — TMap with 15+ mappings (e.g. "I" → "InString", "C" → "Condition")
4. **VariableGet "Value"** — First non-exec, non-self, non-WorldContextObject pin
5. **Sequence A-F** — "then 0" through "then 5" + Nth exec output fallback
6. **Out_N pattern** — "Out_0", "Out_1" etc. for MultiGate + Nth exec output fallback
7. **Branch "C"** — Maps to "Condition" / "bCondition"
8. **Exec input "Execute"** — PN_Execute, then "In", "Input", then first exec input pin
9. **Exec output "Then"** — PN_Then, then "Out", "Output", then first exec output pin
10. **"Pressed"/"Released"** — Nth exec output on InputAction nodes
11. **Case-insensitive search** — Last resort before substring match

**WorldContextObject is excluded from all fallback matching** — it exists on every CallFunction node and causes false matches.

### Connection Wiring

- Uses `Schema->TryCreateConnection()` instead of `MakeLinkTo()` — auto-inserts conversion nodes (Float→String, Int→Float, etc.)
- All nodes get `CreateNewGuid()` after creation — required for editor interactivity
- `Graph->NotifyGraphChanged()` called after wiring — proper editor state

### UE5 Compatibility Fixes

- **Float→Double function rename** — Auto-remaps `Add_FloatFloat` → `Add_DoubleDouble` etc.
- **KismetMathLibrary class resolution** — Falls back to `UKismetMathLibrary::StaticClass()` if path lookup fails
- **Re-import safety** — Deletes existing assets before recreation (prevents crash)
- **Unused default events** — Removes auto-created Event ActorBeginOverlap/Tick if not used

### UE5 Pin Name Cheat Sheet (discovered through testing)

| Node Type | Pin Name (UE Internal) | DSL Name | Notes |
|---|---|---|---|
| FlipFlop exec input | `None` | Execute | Yes, literally "None" |
| FlipFlop exec outputs | `A`, `B` | A, B | |
| FlipFlop data output | `IsA` | IsA | Boolean |
| Sequence exec outputs | `then 0`, `then 1`... | A, B, C... | Space in name |
| MultiGate exec outputs | `Out 0`, `Out 1`... | Out_0, Out_1... | TBD - need log confirmation |
| Branch condition | `Condition` | C | |
| Branch exec outputs | standard PN_Then/PN_Else | True, False | |
| PrintString input | `InString` | I | |
| Cast object input | `Object` | Object | Must set PinType to AActor |
| Math inputs | `A`, `B` | A, B | Direct match |
| Math output | `ReturnValue` | ReturnValue | |

### Test Results (as of 2026-03-02) — 8/8 PASS

| Test | Description | Nodes | Conns | Plugin Import | Nodes Created | Connections Wired | Notes |
|---|---|---|---|---|---|---|---|
| T1_01 | Hello World | 2 | 1 | ✅ | ✅ 2/2 | ✅ 1/1 | First successful import |
| L05_01 | IsValid + Branch | 6 | 5 | ✅ | ✅ 6/6 | ✅ 5/5 | Variables, data flow working |
| L05_02 | CastToCharacter | 4 | 1 | ✅ | ✅ 4/4 | ✅ 1/1 | Model only generated 1/4 connections |
| L12_02 | Sequence + 4 prints | 6 | 5 | ✅ | ✅ 6/6 | ✅ 5/5 | Sequence fan-out working |
| L12_08 | FlipFlop toggle | 6 | 5 | ✅ | ✅ 6/6 | ✅ 5/5 | FlipFlop macro + InputAction working |
| L12_14 | MultiGate 3 outputs | 5 | 4 | ✅ | ✅ 5/5 | ✅ 4/4 | |
| L12_19 | Math (12 nodes) | 12 | 17 | ✅ | ✅ 16/16 | ✅ 21/21 | Float→Double remap, extra nodes auto-generated |
| L12_20 | Health system (13 nodes) | 13 | 14 | ✅ | ✅ 13/13 | ✅ 14/14 | 3 events, damage/heal, data_literal support |

### Plugin Testing Log

| Date | Test | Action | Result | Issue Found | Fix Applied |
|---|---|---|---|---|---|
| 2026-03-01 | T1_01 | First import attempt | ✅ Perfect | — | — |
| 2026-03-01 | L05_01 | Import with variables | ✅ Perfect | — | — |
| 2026-03-01 | L05_02 | Cast node test | ✅ Plugin OK | Model IR only has 1/4 connections | Model issue, not plugin |
| 2026-03-01 | L12_02 | Sequence fan-out | ✅ Perfect | — | — |
| 2026-03-01 | L12_08 | FlipFlop macro | ⚠️ Partial | FlipFlop was placeholder, not macro | Switched to UK2Node_MacroInstance |
| 2026-03-02 | L12_08 | FlipFlop retry | ⚠️ Partial | Macro loads but InputAction→FlipFlop exec pin mismatch | Added Pressed/Released aliases, Nth exec fallback |
| 2026-03-02 | L12_14 | MultiGate | ✅ Perfect | — | — |
| 2026-03-02 | ALL 8 | **Automated test via TCP Command Server** | ✅ **8/8 PASS** | L12_20 had IR authoring bugs (wrong pin names, orphaned LessThan node, invalid "Damage" literal) | Fixed IR: pin names (I→InString, V→Health), routed through LessThan, Damage→data wire from Event_AnyDamage. Added data_literal support to BlueprintBuilder (sets pin DefaultValue). |

All 8 IR files imported and verified via Command Server `test_runner.py` with zero manual steps. Blueprints created and visible in UE Editor.

### TCP Command Server — OPERATIONAL (8/8 tests pass)

**Status:** Fully operational. All 5 commands tested and working. 8/8 IR files imported, verified, and created as real Blueprint assets in UE Editor via automated test runner.

A TCP server embedded in the plugin allows external tools (Python scripts, future MCP bridge) to create and verify Blueprints remotely without manual file dialogs.

**Architecture:**
- Listens on `localhost:13377` using `FTcpListener`
- Newline-delimited JSON protocol (one JSON object per line, newline-terminated)
- Socket I/O on background thread, all UObject work dispatched to game thread via `AsyncTask(ENamedThreads::GameThread, ...)`
- Auto-starts on plugin load; toggleable via Tools menu
- Proper log category: `LogBlueprintLLM`

**Commands:**

| Command | Description | Critical Rule |
|---|---|---|
| `health_check` | Returns server name, version, engine version | — |
| `import_from_ir` | Imports a `.blueprint.json` file — calls same `ParseIR` + `CreateBlueprint` as Tools menu | Rule 17: one code path |
| `get_blueprint_info` | Queries existing Blueprint: nodes, pins, connections, variables, compile status | — |
| `compile_blueprint` | Recompiles a Blueprint | — |
| `delete_blueprint` | Deletes a Blueprint asset (via `ObjectTools::ForceDeleteObjects`) | Rule 8: delete before re-import |

**Protocol:**
```json
// Request (client → server)
{"command": "health_check", "params": {}}

// Response (server → client)
{"status": "ok", "data": {"server": "BlueprintLLM", "version": "1.0"}}

// Error response
{"status": "error", "message": "File not found: C:/bad/path.json"}
```

**Python Client:**
```python
from scripts.mcp_client.blueprint_client import BlueprintLLMClient

with BlueprintLLMClient() as client:
    client.health_check()
    client.import_from_ir("C:/BlueprintLLM/test_ir/T1_01_HelloWorld.blueprint.json")
    client.get_blueprint_info("BP_HelloWorld")
    client.delete_blueprint("BP_HelloWorld")
```

**Test commands:**
```bash
# Quick connectivity test
python scripts/mcp_client/verify.py

# Full test suite against all IR files
python scripts/mcp_client/test_runner.py

# Outputs report to results/plugin_test_<timestamp>.json
```

**Build verified:** 2026-03-02, UE 5.7, VS 2026 14.50.35725, Win64 Development. data_literal support added (sets pin DefaultValue). All 8 IR tests pass via automated test runner.

---

## Parallel Development Roadmap

Two tracks run simultaneously. Track A (LLM) runs when training finishes. Track B (Command Server) runs while training is in progress. They converge at integration points.

### Track A: LLM Training & Accuracy

| Step | Task | Status | Depends On |
|---|---|---|---|
| A1 | Grade v7b results — confirm GA=4 fixed regression | Not started | v7b training complete |
| A2 | Identify remaining weak categories from v7b | Not started | A1 |
| A3 | Write Lesson 14 corrections for weak categories | Not started | A2 |
| A4 | Train v8 (L14 + replay buffer, golden config) | Not started | A3 |
| A5 | Grade v8 with full L01-L14 exam suite | Not started | A4 |
| A6 | Generate fresh IR from v8 exam outputs via parser | Not started | A5 |
| A7 | Separate model-side vs plugin-side failures | Not started | A6 + B4 |
| A8 | Write corrections for remaining model failures | Not started | A7 |
| A9 | Train v9 — target 97%+ syntax all lessons | Not started | A8 |
| A10 | Final accuracy milestone — all failures are plugin-side only | Not started | A9 |

### Track B: Command Server & Automation

| Step | Task | Status | Depends On |
|---|---|---|---|
| B1 | TCP server + health_check | Complete | — |
| B2 | import_from_ir command | Complete | B1 |
| B3 | get_blueprint_info + compile_blueprint | Complete | B1 |
| B4 | Automated test runner (8/8 passing) | Complete | B2 + B3 |
| B5 | Individual node commands (add_node, remove_node, add/remove_connection) | Not started | B4 |
| B6 | set_node_param and set_variable commands | Not started | B5 |
| B7 | spawn_actor and get_actors commands (level placement) | Not started | B4 |
| B8 | DSL-to-UE single command (raw DSL text → verified Blueprint) | Not started | B4 |
| B9 | Claude Desktop integration via MCP | Not started | B8 |
| B10 | Widget Tree commands (create_widget, add_widget_child) | Not started | B5 |
| B11 | Level population commands (spawn_actor_at, set_actor_properties) | Not started | B7 |
| B12 | Material commands (create_material_instance, apply_material) | Not started | B7 |

### Integration Points

| Milestone | Tracks | What It Proves |
|---|---|---|
| First automated end-to-end test | A1 + B4 | v7b IR files verified through test runner automatically |
| Quantified pipeline accuracy | A6 + B4 | Exact count of Blueprints that work end-to-end from v8 |
| Single-command pipeline | A6 + B8 | Raw DSL → verified Blueprint, no intermediate files |
| Live natural language to Blueprint | A10 + B9 | Claude Desktop connected, fine-tuned model, real-time creation |
| First complete scene from description | A10 + B10 + B11 | Blueprints + UI + actors placed in level |

### What To Work On When

- **While training runs:** Work on Track B (next uncompleted step)
- **When training finishes:** Grade results (Track A), write corrections, start next training run, then resume Track B
- **At integration points:** Run convergence tests, document results

---

### Model Training Issues (see MODEL_TRAINING_ISSUES.md for details)

2 high-severity issues remaining in model IR output:
1. Incomplete Cast node connections (L05_02) — model generates 1/4 connections
2. Sequence node used linearly instead of fan-out (L12_19) — plugin creates extra nodes to compensate

3 issues FIXED in L12_20 IR (were IR authoring bugs, not model issues):
- ~~LessThan node orphaned~~ — routed SubtractFloat→LessThan→Branch
- ~~Event output pin as string literal~~ — changed to data wire from Event_AnyDamage.Damage
- ~~Wrong pin names (I, V)~~ — fixed to InString, Health

2 medium-severity (plugin has workarounds):
1. Float vs Double function names (auto-remapped)
2. Missing implicit conversion nodes (TryCreateConnection handles it)

### Plugin Includes Required

```cpp
#include "EdGraphSchema_K2.h"
#include "K2Node_CallFunction.h"
#include "K2Node_Event.h"
#include "K2Node_CustomEvent.h"
#include "K2Node_IfThenElse.h"
#include "K2Node_ExecutionSequence.h"
#include "K2Node_MultiGate.h"
#include "K2Node_DynamicCast.h"
#include "K2Node_InputAction.h"
#include "K2Node_VariableGet.h"
#include "K2Node_VariableSet.h"
#include "K2Node_MacroInstance.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Kismet/KismetMathLibrary.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/Character.h"
```

---

## Communication Protocol

- **Step numbering is the universal language.** Use it in all logs, dashboard, and communication.
- **Claude.ai (architect)** designs solutions and creates lessons. Share exam results there for grading.
- **Claude Code (builder)** implements solutions and runs the pipeline.
- **This file (CLAUDE.md)** is the shared context between both. Update it when architecture decisions change.
- **The user is the project director**, not a relay between AIs. Minimize copy-pasting between Claude.ai and Claude Code.
