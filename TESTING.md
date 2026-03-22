# Testing discipline

This repo uses **fast automated checks** on every commit (optional **Husky** hook) and a **slower full moderation evaluation** before important milestones.

## Happy Path Walkthrough (manual)

**Prerequisites:** PostgreSQL running; `backend/.env` has `DATABASE_URL` and `AI_ANALYZE_URL=http://127.0.0.1:8000/analyze`; Prisma migrated (`npx prisma migrate deploy` or `db push` from `backend/`).

1. **Start AI service** (from `ai-service/` with `.venv`):  
   `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` or `.\run-dev.ps1`  
2. **Start backend:** `cd backend && npm run dev`  
3. **Serve demo UI:** e.g. `npx serve -l 5173` from `demo/` (or repo root pointing at `demo`).  
4. Open the demo URL, set **API base** to `http://localhost:3000`, **User id** to an existing user (e.g. `1`), and a plausible **age**.

5. **Safe path:** Upload a neutral screenshot (e.g. plain UI text or a harmless quote). Click **Run analyze**. Expect **low risk**, category **`safe`**, and a **low-points** mission (e.g. “Continue your activity responsibly”).  
6. **High-risk path:** Upload a screenshot whose OCR text matches hate/threat content (or use a test image from your PFE set). Expect **high risk**, category **`dangerous`** or **`risky`**, and a **stronger** mission (e.g. break / go outside).  
7. **History & summary:** Click **Load history** — new rows should appear; **Load summary** — total points and counts should reflect the missions you triggered.

**Regression check:** From repo root, run **`npm test`** before commits; before milestones run **`npm run test:full`**.

For a compact checklist, see **`TECHNICAL_REPORT.md` §9 — Operational checklist (local demo)**.

## What runs

| Layer | Command | What it does |
|--------|---------|----------------|
| Backend | `cd backend && npm test` | **Jest**: `missionForRiskScore` bands; **`aiService.analyzeImage`** with mocked `axios`. |
| AI service | `cd ai-service && python -m pytest tests -q` (or `py -3`) | **pytest**: `moderate()` fallbacks (empty / short / classifier not ready / exception) and mocked classifier scores. |
| AI service (slow) | `cd ai-service && python evaluate_moderation.py` | **15-case** offline eval over `moderation_eval_dataset.json` (loads real model). |
| AI service (CI gate) | `cd ai-service && python evaluate_moderation.py --strict` | Same as above, but **exits 1** if any fallback flag mismatches **or** the flagship case `danger-fr-en-hate-mixed` is not `dangerous` with risk ≥ **0.85** and **`hate speech`** in labels. |

## One-shot runner (recommended)

From the **repository root**:

```bash
# Fast: Jest + pytest (no model load)
npm test
# or:
node scripts/run-all-tests.js
```

```bash
# Full: Jest + pytest + evaluate_moderation.py --strict (~ tens of seconds / minutes on CPU)
npm run test:full
# or:
node scripts/run-all-tests.js --full
```

On Unix shells you can use:

```bash
chmod +x scripts/run_tests.sh
./scripts/run_tests.sh          # fast
./scripts/run_tests.sh --full    # includes strict eval
```

### Prerequisites

- **Backend:** `cd backend && npm install` (includes **Jest**).  
- **Root (hooks):** `npm install` at repo root (installs **Husky**).  
- **AI service:** use the **same virtualenv** you use for Uvicorn (`pip install -r requirements.txt` and `pip install -r requirements-dev.txt`). Unit tests import `moderation_service`, which requires **transformers** / **torch** at import time — a bare `python` without that stack will fail collection.

**Optional (Windows / multiple Pythons):** set `AI_VENV_PYTHON` to the full path of `python.exe` inside your `ai-service` `.venv` so `npm test` picks it up:

```powershell
$env:AI_VENV_PYTHON = "C:\path\to\ai-service\.venv\Scripts\python.exe"
npm test
```

## Pre-commit hook (Option A)

1. From repo root: `npm install` (runs `prepare` → `husky`).  
2. `.husky/pre-commit` runs **`npm test`** (fast suite only).  
3. If a hook step fails, **Git aborts the commit**.

To skip temporarily (emergency only):

```bash
git commit --no-verify -m "message"
```

**Policy:** Do **not** use `--no-verify` for normal work; fix or update tests instead.

## Manual rule (Option B)

If you do not use Husky, follow this before every commit:

1. `cd backend && npm test`  
2. `cd ai-service && python -m pytest tests -q`  
3. Optionally before milestones: `python evaluate_moderation.py --strict`  

**Do not commit** if any step fails.

## Changing behaviour vs changing tests

- **Tests** should reflect **current intended behaviour**. If the product changes (e.g. mission thresholds), update tests in the same commit.  
- If **`evaluate_moderation.py --strict`** fails after a deliberate model/threshold change, fix **calibration or dataset expectations** in a dedicated change; do not weaken `--strict` checks without review.

## Troubleshooting

- **`pytest` not found:** `pip install -r ai-service/requirements-dev.txt` inside the same venv you use for the AI service.  
- **Jest fails after clone:** `cd backend && npm install`.  
- **Husky does not run:** run `npm install` from **repo root**; ensure `.husky/pre-commit` is executable on Unix (`chmod +x .husky/pre-commit`).  
- **Full eval OOM or timeout:** run `npm run test:full` on a machine with enough RAM; first inference after startup is slower than cached steady state.
