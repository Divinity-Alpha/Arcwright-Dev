# Arcwright Mission Control — Integration Spec

## Overview

Wire the Mission Control dashboard (blueprint_mission_control.html) to the live training pipeline so it updates in real-time. The dashboard reads JSON files from disk on a 5-second polling interval. The pipeline writes these files at each state change.

## Architecture

```
Pipeline (Python scripts)
    │
    ├── writes → C:\BlueprintLLM\dashboard\state.json          (every state change)
    ├── writes → C:\BlueprintLLM\dashboard\exam_progress.json   (after each exam prompt)
    ├── writes → C:\BlueprintLLM\dashboard\version_history.json  (after each pipeline completes)
    │
Dashboard (HTML served locally)
    │
    └── reads ← all 3 JSON files every 5 seconds via fetch()
```

Serve the dashboard with:
```
cd C:\BlueprintLLM\dashboard
python -m http.server 8080
```
Then open http://localhost:8080/index.html

## File 1: dashboard/state.json

Written by the pipeline orchestrator at every step transition and every exam prompt completion. This is the primary live state file.

```json
{
  "version": "v5",
  "status": "running",
  "pipeline_start_time": 1740700000,
  "current_step": {
    "number": 6,
    "total_steps": 9,
    "name": "Run exams (L01-L10)",
    "started_at": 1740703000
  },
  "steps": [
    {
      "number": 1,
      "name": "Load config",
      "status": "done",
      "duration_seconds": 2
    },
    {
      "number": 2,
      "name": "Prepare dataset",
      "status": "done",
      "duration_seconds": 12,
      "detail": "587 examples"
    },
    {
      "number": 3,
      "name": "Validate data",
      "status": "done",
      "duration_seconds": 3
    },
    {
      "number": 4,
      "name": "Training",
      "status": "done",
      "duration_seconds": 2820,
      "detail": "148 steps, loss 2.41"
    },
    {
      "number": 5,
      "name": "Merge LoRA weights",
      "status": "done",
      "duration_seconds": 480
    },
    {
      "number": 6,
      "name": "Run exams",
      "status": "active",
      "detail": "L03 4/20",
      "started_at": 1740703000
    },
    {
      "number": 7,
      "name": "Run eval suite",
      "status": "pending"
    },
    {
      "number": 8,
      "name": "Generate reports",
      "status": "pending"
    },
    {
      "number": 9,
      "name": "Git push + notify",
      "status": "pending"
    }
  ],
  "training": {
    "total_steps": 148,
    "current_step": 148,
    "loss": 2.41,
    "examples": 587,
    "epochs": 2,
    "learning_rate": "2e-4",
    "elapsed_seconds": 2820
  },
  "exam_active": {
    "lesson_id": "lesson_03",
    "lesson_name": "Timers & Delays",
    "current_prompt": 4,
    "total_prompts": 20,
    "last_prompt_time_seconds": 28.4,
    "avg_prompt_time_seconds": 31.2
  }
}
```

### When to write state.json:

1. **Pipeline start** — status="running", step 1 active
2. **Each step transition** — mark previous done with duration, next active
3. **During training** — every 10 steps, update training.current_step and training.loss
4. **During exams** — after EVERY prompt completion, update exam_active.current_prompt and last_prompt_time_seconds
5. **Pipeline end** — status="idle"

### Python helper to write state:

```python
import json, time, os

DASHBOARD_DIR = r"C:\BlueprintLLM\dashboard"

def write_state(state_dict):
    """Atomically write state.json for dashboard consumption."""
    path = os.path.join(DASHBOARD_DIR, "state.json")
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state_dict, f, indent=2)
    os.replace(tmp, path)  # atomic on Windows NTFS
```

Use `os.replace` for atomic writes so the dashboard never reads a partial file.

## File 2: dashboard/exam_progress.json

Written after each exam lesson completes. Contains results for all completed lessons in the current run.

```json
{
  "version": "v5",
  "lessons": [
    {
      "lesson_id": "L01",
      "lesson_name": "Core Patterns",
      "status": "done",
      "valid_count": 17,
      "total_count": 20,
      "valid_syntax_pct": 85.0,
      "avg_similarity": 62.3,
      "duration_seconds": 480,
      "avg_prompt_time": 24.0,
      "prompts": [
        {
          "prompt_id": "L01_01",
          "category": "print_hello",
          "valid": false,
          "similarity": 100.0,
          "time_seconds": 22.9
        },
        {
          "prompt_id": "L01_02",
          "category": "rotating_actor",
          "valid": true,
          "similarity": 36.4,
          "time_seconds": 52.2
        }
      ],
      "weakest_categories": [
        {"category": "distance_check", "similarity": 28.6},
        {"category": "branch", "similarity": 33.3}
      ],
      "strongest_categories": [
        {"category": "print_hello", "similarity": 100.0},
        {"category": "delay_chain", "similarity": 85.7}
      ]
    },
    {
      "lesson_id": "L02",
      "lesson_name": "Variables & Events",
      "status": "done",
      "valid_count": 19,
      "total_count": 24,
      "valid_syntax_pct": 79.2,
      "avg_similarity": 66.6,
      "duration_seconds": 720,
      "avg_prompt_time": 30.0,
      "prompts": [],
      "weakest_categories": [],
      "strongest_categories": []
    },
    {
      "lesson_id": "L03",
      "lesson_name": "Timers & Delays",
      "status": "running",
      "valid_count": 3,
      "total_count": 20,
      "completed_prompts": 4,
      "prompts": []
    }
  ],
  "aggregate": {
    "total_prompts_completed": 48,
    "total_prompts_remaining": 116,
    "overall_valid_syntax_pct": 81.8,
    "overall_avg_similarity": 64.2,
    "estimated_remaining_seconds": 3480
  }
}
```

### When to write exam_progress.json:

1. **After each exam prompt completes** — update the current lesson's prompts array, valid_count, and aggregate stats
2. **After each lesson completes** — finalize lesson entry, compute weakest/strongest categories, start next lesson entry
3. **Aggregate section** updates after every prompt so the dashboard can show live totals and ETA

### Python integration point:

In `12_run_exam.py`, after each prompt inference completes:

```python
def update_exam_progress(lesson_id, lesson_name, prompt_result, all_results_so_far):
    """Call this after each exam prompt completes."""
    path = os.path.join(DASHBOARD_DIR, "exam_progress.json")
    
    # Load existing or create new
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
    else:
        data = {"version": VERSION, "lessons": [], "aggregate": {}}
    
    # Find or create lesson entry
    lesson = next((l for l in data["lessons"] if l["lesson_id"] == lesson_id), None)
    if not lesson:
        lesson = {
            "lesson_id": lesson_id,
            "lesson_name": lesson_name,
            "status": "running",
            "valid_count": 0,
            "total_count": prompt_result["total_in_lesson"],
            "completed_prompts": 0,
            "prompts": []
        }
        data["lessons"].append(lesson)
    
    # Append prompt result
    lesson["prompts"].append({
        "prompt_id": prompt_result["prompt_id"],
        "category": prompt_result["category"],
        "valid": prompt_result["valid"],
        "similarity": prompt_result["similarity"],
        "time_seconds": prompt_result["time_seconds"]
    })
    lesson["completed_prompts"] = len(lesson["prompts"])
    lesson["valid_count"] = sum(1 for p in lesson["prompts"] if p["valid"])
    
    # Update aggregate
    all_prompts = [p for l in data["lessons"] for p in l["prompts"]]
    total_done = len(all_prompts)
    total_remaining = TOTAL_EXAM_PROMPTS - total_done
    avg_time = sum(p["time_seconds"] for p in all_prompts) / max(total_done, 1)
    
    data["aggregate"] = {
        "total_prompts_completed": total_done,
        "total_prompts_remaining": total_remaining,
        "overall_valid_syntax_pct": round(sum(1 for p in all_prompts if p["valid"]) / max(total_done, 1) * 100, 1),
        "overall_avg_similarity": round(sum(p["similarity"] for p in all_prompts) / max(total_done, 1), 1),
        "estimated_remaining_seconds": int(avg_time * total_remaining)
    }
    
    write_state_atomic(path, data)
```

## File 3: dashboard/version_history.json

Persistent file that accumulates results across all training versions. Never overwritten — only appended to. This powers the version progression chart.

```json
{
  "versions": [
    {
      "version": "v2",
      "date": "2026-02-27T08:00:00",
      "training_examples": 391,
      "training_time_seconds": 29880,
      "system_prompt_chars": 5660,
      "eval": {
        "pass_rate": 0.82,
        "avg_score": 0.78,
        "perfect_scores": 2,
        "avg_gen_time": 221
      },
      "exam_summary": {
        "total_prompts": 44,
        "valid_syntax_pct": 2.0,
        "avg_similarity": 1.5
      },
      "lessons_tested": ["L01", "L02"]
    },
    {
      "version": "v3",
      "date": "2026-02-27T14:00:00",
      "training_examples": 391,
      "training_time_seconds": 2816,
      "system_prompt_chars": 463,
      "eval": {
        "pass_rate": 0.91,
        "avg_score": 0.88,
        "perfect_scores": 4,
        "avg_gen_time": 68
      },
      "exam_summary": {
        "total_prompts": 164,
        "valid_syntax_pct": 85.4,
        "avg_similarity": 56.0
      },
      "lessons_tested": ["L01","L02","L03","L04","L05","L06","L07","L08"],
      "lesson_scores": {
        "L01": {"syntax": 80, "similarity": 61.9},
        "L02": {"syntax": 79.2, "similarity": 63.8},
        "L03": {"syntax": 95, "similarity": 59.7},
        "L04": {"syntax": 95, "similarity": 45.2},
        "L05": {"syntax": 80, "similarity": 51.4},
        "L06": {"syntax": 85, "similarity": 53.8},
        "L07": {"syntax": 90, "similarity": 53.6},
        "L08": {"syntax": 80, "similarity": 58.6}
      }
    },
    {
      "version": "v4",
      "date": "2026-02-27T19:00:00",
      "training_examples": 414,
      "training_time_seconds": 2860,
      "system_prompt_chars": 463,
      "eval": {
        "pass_rate": 1.0,
        "avg_score": 0.936,
        "perfect_scores": 7,
        "avg_gen_time": 41
      },
      "exam_summary": {
        "total_prompts": 80,
        "valid_syntax_pct": 95.0,
        "avg_similarity": 63.2
      },
      "lessons_tested": ["L07","L08","L09","L10"],
      "lesson_scores": {
        "L07": {"syntax": 100, "similarity": 66.2},
        "L08": {"syntax": 95, "similarity": 63.9},
        "L09": {"syntax": 100, "similarity": 73.3},
        "L10": {"syntax": 85, "similarity": 49.0}
      }
    }
  ]
}
```

### When to write version_history.json:

**Once per pipeline run** — after eval completes (step 7), before git push. Load existing file, append new version entry, write back.

```python
def append_version_history(version_tag, eval_results, exam_summaries, training_info):
    path = os.path.join(DASHBOARD_DIR, "version_history.json")
    
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
    else:
        data = {"versions": []}
    
    lesson_scores = {}
    total_valid = 0
    total_prompts = 0
    total_sim = 0
    
    for summary in exam_summaries:
        lid = summary["lesson_id"].replace("lesson_", "L")
        lesson_scores[lid] = {
            "syntax": summary["valid_syntax_pct"],
            "similarity": summary["avg_similarity_score"]
        }
        total_valid += summary["valid_syntax"]
        total_prompts += summary["total_prompts"]
        total_sim += summary["avg_similarity_score"] * summary["total_prompts"]
    
    entry = {
        "version": version_tag,
        "date": datetime.now().isoformat(),
        "training_examples": training_info["total_examples"],
        "training_time_seconds": training_info["training_seconds"],
        "system_prompt_chars": training_info.get("system_prompt_chars", 463),
        "eval": {
            "pass_rate": eval_results["summary"]["passed"] / eval_results["summary"]["total"],
            "avg_score": eval_results["summary"]["avg_score"],
            "perfect_scores": sum(1 for r in eval_results["results"] if r["score"] == 1.0),
            "avg_gen_time": eval_results["summary"]["avg_time"]
        },
        "exam_summary": {
            "total_prompts": total_prompts,
            "valid_syntax_pct": round(total_valid / max(total_prompts, 1) * 100, 1),
            "avg_similarity": round(total_sim / max(total_prompts, 1), 1)
        },
        "lessons_tested": list(lesson_scores.keys()),
        "lesson_scores": lesson_scores
    }
    
    # Replace if version already exists, otherwise append
    data["versions"] = [v for v in data["versions"] if v["version"] != version_tag]
    data["versions"].append(entry)
    data["versions"].sort(key=lambda v: v["version"])
    
    write_state_atomic(path, data)
```

## Dashboard Integration (JavaScript Side)

Replace the hardcoded demo data in the HTML with fetch-based polling. Add this to the bottom of the `<script>` block, replacing the static render calls:

```javascript
// ============================================================
// LIVE DATA POLLING — replaces static demo data
// ============================================================

const POLL_INTERVAL = 5000; // 5 seconds
const BASE = '.'; // files served from same directory

async function fetchJSON(filename) {
  try {
    const resp = await fetch(`${BASE}/${filename}?t=${Date.now()}`);
    if (!resp.ok) return null;
    return await resp.json();
  } catch { return null; }
}

async function pollAndRender() {
  const [state, exams, history] = await Promise.all([
    fetchJSON('state.json'),
    fetchJSON('exam_progress.json'),
    fetchJSON('version_history.json')
  ]);

  if (state) renderState(state);
  if (exams) renderExamProgress(exams);
  if (history) renderVersionHistory(history);
}

function renderState(s) {
  // Status beacon
  const isRunning = s.status === 'running';
  document.getElementById('beacon').className = `beacon ${isRunning ? 'on' : 'off'}`;
  document.querySelector('.dot').className = `dot ${isRunning ? '' : 'off'}`;
  document.getElementById('sTxt').textContent = isRunning ? 'RUNNING' : 'IDLE';
  document.getElementById('vBadge').textContent = s.version;
  document.getElementById('cvBadge').textContent = s.version;

  // Pipeline steps
  document.getElementById('steps').innerHTML = s.steps.map(st => {
    const icon = st.status === 'done' ? '✓' : st.status === 'active' ? '▶' : '○';
    const dur = st.duration_seconds 
      ? (st.duration_seconds >= 60 ? Math.round(st.duration_seconds/60) + 'm' : st.duration_seconds + 's')
      : (st.status === 'active' && st.started_at 
          ? Math.round((Date.now()/1000 - st.started_at)/60) + 'm+' 
          : '—');
    const detail = st.detail ? `<span class="step-detail">${st.detail}</span>` : '';
    return `<div class="step ${st.status}">
      <div class="step-i ${st.status}">${icon}</div>
      <div class="step-n">${st.name} ${detail}</div>
      <div class="step-t">${dur}</div>
    </div>`;
  }).join('');

  // ETA bar
  const doneSteps = s.steps.filter(st => st.status === 'done').length;
  const pct = Math.round((doneSteps + (s.exam_active ? s.exam_active.current_prompt / s.exam_active.total_prompts * 0.5 : 0)) / s.steps.length * 100);
  document.getElementById('etaF').style.width = pct + '%';
  
  const etaDetail = s.exam_active 
    ? `Step ${s.current_step.number}/${s.steps.length} · ${s.exam_active.lesson_name} ${s.exam_active.current_prompt}/${s.exam_active.total_prompts}`
    : `Step ${s.current_step.number}/${s.steps.length} · ${s.current_step.name}`;
  document.getElementById('etaT').textContent = etaDetail;

  // Training detail in step if active
  if (s.training && s.steps.find(st => st.name === 'Training' && st.status === 'active')) {
    const trainStep = s.steps.find(st => st.name === 'Training');
    if (trainStep) trainStep.detail = `${s.training.current_step}/${s.training.total_steps}, loss ${s.training.loss}`;
  }
}

function renderExamProgress(ep) {
  // Exam table
  document.getElementById('etbody').innerHTML = ep.lessons.map(l => {
    const sx = l.valid_syntax_pct ?? (l.completed_prompts > 0 ? Math.round(l.valid_count / l.completed_prompts * 100) : 0);
    const sm = l.avg_similarity ?? (l.prompts.length > 0 ? Math.round(l.prompts.reduce((a,p) => a + p.similarity, 0) / l.prompts.length * 10) / 10 : 0);
    const sc = sx >= 80 ? 'hi' : sx >= 50 ? 'mi' : 'lo';
    const mc = sm >= 70 ? 'hi' : sm >= 45 ? 'mi' : 'lo';
    const tg = l.status === 'done' ? '<span class="tag d">✓</span>' : l.status === 'running' ? '<span class="tag r">▶</span>' : '<span class="tag p">○</span>';
    const dur = l.duration_seconds ? (l.duration_seconds >= 60 ? Math.round(l.duration_seconds/60) + 'm' : l.duration_seconds + 's') : '—';
    const done = l.status !== 'pending';
    const count = done ? `${l.valid_count}/${l.completed_prompts || l.total_count}` : '—';

    return `<tr>
      <td class="mono" style="color:var(--t3)">${l.lesson_id}</td>
      <td class="ln">${l.lesson_name}</td>
      <td class="c">${tg}</td>
      <td class="mono c">${count}</td>
      <td><div class="pc"><div class="pt"><div class="pf ${sc}" style="width:${done ? sx : 0}%"></div></div><div class="pp" style="color:${sx>=80?'var(--green)':sx>=50?'var(--amber)':'var(--t3)'}">${done ? sx+'%' : '—'}</div></div></td>
      <td><div class="pc"><div class="pt"><div class="pf ${mc}" style="width:${done ? sm : 0}%"></div></div><div class="pp" style="color:${sm>=70?'var(--blue)':sm>=45?'var(--amber)':'var(--t3)'}">${done ? sm+'%' : '—'}</div></div></td>
      <td class="mono r" style="color:var(--t3)">${dur}</td>
      <td class="mono r ds">—</td>
    </tr>`;
  }).join('');

  // Aggregate stats
  const ag = ep.aggregate;
  if (ag) {
    document.getElementById('examCt').textContent = `${ag.total_prompts_completed}/${ag.total_prompts_completed + ag.total_prompts_remaining} prompts`;
  }

  // Category heatmap from all completed prompts
  const catMap = {};
  ep.lessons.forEach(l => {
    l.prompts.forEach(p => {
      if (!catMap[p.category]) catMap[p.category] = { total: 0, count: 0 };
      catMap[p.category].total += p.similarity;
      catMap[p.category].count++;
    });
  });
  const cats = Object.entries(catMap).map(([n, v]) => ({ n, s: Math.round(v.total / v.count) })).sort((a,b) => a.s - b.s);
  
  document.getElementById('hmap').innerHTML = cats.map(c => {
    const h = c.s <= 25 ? 0 : c.s <= 50 ? 30 : c.s <= 75 ? 120 : 150;
    const tc = c.s <= 25 ? 'var(--red)' : c.s <= 50 ? 'var(--amber)' : c.s <= 75 ? 'var(--t1)' : 'var(--green)';
    return `<div class="hcell" style="background:hsl(${h},${c.s<=25?'70%':'50%'},${c.s<=25?'24%':c.s<=50?'21%':'19%'})"><span class="cn" style="color:${tc}">${c.n}</span><span class="cs" style="color:${tc}">${c.s}%</span></div>`;
  }).join('');
}

function renderVersionHistory(vh) {
  const versions = vh.versions;
  if (!versions.length) return;

  // Version chart
  document.getElementById('vchart').innerHTML = versions.map(v => `
    <div class="vgroup">
      <div class="vbars">
        <div class="vb s" data-v="${v.exam_summary.valid_syntax_pct}" style="height:${Math.max(v.exam_summary.valid_syntax_pct, 2)}%"></div>
        <div class="vb m" data-v="${v.exam_summary.avg_similarity}" style="height:${Math.max(v.exam_summary.avg_similarity, 2)}%"></div>
      </div>
      <div class="vlbl">${v.version}</div>
    </div>
  `).join('');

  // Big stats (latest vs previous)
  const cur = versions[versions.length - 1];
  const prev = versions.length > 1 ? versions[versions.length - 2] : null;
  const dSx = prev ? +(cur.exam_summary.valid_syntax_pct - prev.exam_summary.valid_syntax_pct).toFixed(1) : 0;
  const dSm = prev ? +(cur.exam_summary.avg_similarity - prev.exam_summary.avg_similarity).toFixed(1) : 0;
  const dEv = prev ? +(cur.eval.avg_score * 100 - prev.eval.avg_score * 100).toFixed(1) : 0;
  const dSpd = prev ? +(prev.eval.avg_gen_time - cur.eval.avg_gen_time).toFixed(0) : 0;
  const pv = prev ? prev.version : '—';

  document.getElementById('bstats').innerHTML = `
    <div class="bstat"><div class="bv" style="color:var(--green)">${cur.exam_summary.valid_syntax_pct}%</div><div class="bl">Valid Syntax</div><div class="bd ${dSx>0?'du':dSx<0?'dd':'ds'}">${dSx>0?'↑ +':dSx<0?'↓ ':'— '}${dSx}% vs ${pv}</div></div>
    <div class="bstat"><div class="bv" style="color:var(--blue)">${cur.exam_summary.avg_similarity}%</div><div class="bl">Avg Similarity</div><div class="bd ${dSm>0?'du':dSm<0?'dd':'ds'}">${dSm>0?'↑ +':dSm<0?'↓ ':'— '}${dSm}% vs ${pv}</div></div>
    <div class="bstat"><div class="bv" style="color:var(--amber)">${(cur.eval.avg_score*100).toFixed(1)}%</div><div class="bl">Eval Score</div><div class="bd ${dEv>0?'du':dEv<0?'dd':'ds'}">${dEv>0?'↑ +':dEv<0?'↓ ':'— '}${dEv}% vs ${pv}</div></div>
    <div class="bstat"><div class="bv" style="color:var(--cyan)">${cur.eval.avg_gen_time}s</div><div class="bl">Avg Gen Time</div><div class="bd ${dSpd>0?'du':dSpd<0?'dd':'ds'}">${dSpd>0?'↑ -':dSpd<0?'↓ +':'— '}${Math.abs(dSpd)}s vs ${pv}</div></div>`;

  // Eval grid
  // This requires eval results in version_history or a separate eval file
  // For now, show pass rate
  document.getElementById('evalP').textContent = `${cur.eval.perfect_scores} perfect / ${Math.round(cur.eval.pass_rate * 11)} passing`;
}

// Start polling
pollAndRender();
setInterval(pollAndRender, POLL_INTERVAL);
```

## File Structure

After implementation, the dashboard directory should look like:

```
C:\BlueprintLLM\dashboard\
├── index.html              ← the dashboard (copy from blueprint_mission_control.html)
├── state.json              ← written by pipeline, live state
├── exam_progress.json      ← written by pipeline, exam results
└── version_history.json    ← persistent, accumulates across versions
```

## Implementation Steps for Claude Code

### Step 1: Create dashboard directory and copy HTML

```python
import shutil, os
os.makedirs(r"C:\BlueprintLLM\dashboard", exist_ok=True)
# Copy the HTML file as index.html
# Replace the demo data script block with the live polling script block above
```

### Step 2: Create a dashboard writer utility module

Create `scripts/dashboard_writer.py` with these functions:
- `write_state(state_dict)` — atomic write to dashboard/state.json
- `update_exam_progress(lesson_id, lesson_name, prompt_result)` — append to dashboard/exam_progress.json
- `finalize_lesson(lesson_id)` — mark lesson as done, compute weakest/strongest
- `append_version_history(version, eval_results, exam_summaries, training_info)` — append to version_history.json
- `reset_run(version)` — clear state.json and exam_progress.json for a new run

### Step 3: Integrate into pipeline orchestrator (11_pipeline_orchestrator.py)

At each step transition:
```python
from dashboard_writer import write_state, reset_run
reset_run("v5")  # at pipeline start
# ... at each step:
state["steps"][step_num]["status"] = "done"
state["steps"][step_num]["duration_seconds"] = elapsed
state["steps"][step_num + 1]["status"] = "active"
write_state(state)
```

### Step 4: Integrate into exam runner (12_run_exam.py)

After each prompt inference:
```python
from dashboard_writer import update_exam_progress
update_exam_progress(
    lesson_id="L03",
    lesson_name="Timers & Delays",
    prompt_result={
        "prompt_id": "L03_04",
        "category": "timer_counter",
        "valid": True,
        "similarity": 50.0,
        "time_seconds": 28.4,
        "total_in_lesson": 20
    }
)
```

### Step 5: Integrate into training loop (04_train.py)

Every 10 training steps:
```python
from dashboard_writer import write_state
# Update state.training.current_step and state.training.loss
write_state(state)
```

### Step 6: After eval (09_evaluate.py)

```python
from dashboard_writer import append_version_history
append_version_history("v5", eval_results, exam_summaries, training_info)
```

### Step 7: Replace demo data in HTML

In the dashboard HTML, replace all the hardcoded `STEPS`, `VERS`, `EXAMS`, etc. arrays and their manual render calls with the live polling code from the "Dashboard Integration" section above. Keep the render helper functions but have them called by `pollAndRender()` instead of directly.

## Auto-Launch

Add to the pipeline orchestrator, at step 1:
```python
import subprocess
subprocess.Popen(
    ["python", "-m", "http.server", "8080"],
    cwd=r"C:\BlueprintLLM\dashboard",
    creationflags=subprocess.CREATE_NO_WINDOW
)
print("Dashboard: http://localhost:8080")
```

This starts the server silently. It persists across the pipeline run and can be killed manually or left running.

## Summary

Three JSON files, atomic writes, 5-second polling. No WebSocket complexity, no database, no build step. The pipeline writes plain JSON files. The dashboard reads them. It works even if you open the dashboard after the pipeline is already running — it picks up current state immediately.
