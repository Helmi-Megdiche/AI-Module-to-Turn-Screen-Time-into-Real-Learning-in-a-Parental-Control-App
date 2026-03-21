# Technical Report — AI Module for Parental Control (PFE)

**Scope:** This document describes the full technical stack of the project: screenshot ingestion, local OCR, multilingual zero-shot moderation, risk categorisation, mission assignment, persistence in PostgreSQL, and the static demo UI. It is intended as the primary engineering reference for the PFE defence and handover.

---

## 1. Project purpose

The system turns **screen content** (provided as a **Base64-encoded image** from a parental-control style workflow) into:

1. **Extracted text** (OCR) for audit and transparency.  
2. A **numeric risk score** in `[0, 1]` and a **coarse category**: `safe`, `risky`, or `dangerous`.  
3. **Matched keywords** (short labels) explaining which harm hypotheses fired above a confidence cutoff.  
4. A **behavioural mission** and **points** for the child profile, stored with the analysis in a database.  
5. **History and summary** APIs for dashboards or parent apps.

The design prioritises **local execution on CPU** (no paid cloud inference required for the demo), a **stable JSON contract** between Node and Python, and **explainability** via keywords and raw vs display text.

---

## 2. High-level architecture

```mermaid
flowchart TB
  subgraph clients
    Demo[Demo UI static HTML]
    Postman[Postman / other HTTP clients]
  end

  subgraph backend["Node.js backend :3000"]
    Express[Express + CORS + JSON 15MB]
    AnalyzeCtrl[POST /api/analyze]
    UserCtrl[GET /api/user/:id/*]
    AnalyzeSvc[analyzeService]
    AiClient[aiService → axios]
    Prisma[Prisma Client]
  end

  subgraph db[(PostgreSQL)]
    TUser[User]
    TAnalysis[Analysis]
    TMission[Mission]
  end

  subgraph ai["Python AI service :8000"]
    FastAPI[FastAPI]
    OCR[EasyOCR]
    Mod[Zero-shot moderation Transformers]
    Fallback[Rule-based risk_scoring]
  end

  Demo --> AnalyzeCtrl
  Postman --> AnalyzeCtrl
  Demo --> UserCtrl
  Postman --> UserCtrl
  AnalyzeCtrl --> AnalyzeSvc
  AnalyzeSvc --> AiClient
  AiClient -->|"POST /analyze { image }"| FastAPI
  FastAPI --> OCR
  OCR --> Mod
  Mod -.->|empty / short / degraded / error| Fallback
  AnalyzeSvc --> Prisma
  Prisma --> TUser
  Prisma --> TAnalysis
  Prisma --> TMission
```

**Data flow (analyse with image):**

1. Client sends `POST /api/analyze` with `userId`, `age`, and optional `image` (raw Base64).  
2. Backend forwards `image` to `POST http://127.0.0.1:8000/analyze` (configurable).  
3. AI service decodes Base64 → PIL image → **OCR text** → **moderation** (or fallback) → JSON.  
4. Backend computes **mission** from **risk score** (not from category string), writes **Analysis** and **Mission**, increments **User.points** in one transaction.  
5. Client can call **history** and **summary** for that `userId`.

---

## 3. Repository layout

| Path | Role |
|------|------|
| `ai-service/` | FastAPI app: OCR, moderation, `/analyze`, `/health`. |
| `ai-service/app/config.py` | Model name, hypothesis template, label map, thresholds, cache, startup timeout. |
| `ai-service/app/main.py` | HTTP API and orchestration OCR → `analyze_text` → response mapping. |
| `ai-service/app/services/ocr_service.py` | EasyOCR singleton reader. |
| `ai-service/app/services/moderation_service.py` | Transformers zero-shot pipeline, LRU cache, fallback orchestration. |
| `ai-service/app/services/risk_scoring.py` | Deterministic rule-based signals (fallback + fuzzy OCR helpers). |
| `ai-service/app/utils/image_utils.py` | Base64 → PIL. |
| `ai-service/evaluate_moderation.py` | Offline eval over `moderation_eval_dataset.json`. |
| `ai-service/moderation_eval_dataset.json` | Labelled test strings (categories, risk bands, fallback expectations). |
| `ai-service/requirements.txt` | Python dependencies and minimum versions. |
| `backend/` | Express API, Prisma, PostgreSQL. |
| `backend/prisma/schema.prisma` | `User`, `Analysis`, `Mission` models. |
| `backend/src/` | Routes, controllers, services (`analyzeService`, `aiService`, `userService`). |
| `demo/index.html` | Single-page jury demo (no build step). |
| `backend/scripts/gen_hate_analyze_payload.py` | Optional generator for E2E JSON payload (PNG + eval hate lines). |

---

## 4. AI service (Python / FastAPI)

### 4.1 Runtime and dependencies

- **Framework:** FastAPI, served with Uvicorn.  
- **Key libraries** (see `requirements.txt`): `easyocr`, `pillow`, `numpy`, `transformers`, `torch`, `sentencepiece`, `protobuf`.  
- **Device:** Pipeline is built with **`device=-1` (CPU)** in `moderation_service.py`.

### 4.2 Startup behaviour

On application startup (`main.py`):

- **EasyOCR** reader is preloaded (`ocr_service.get_reader()`). Failure logs a warning and defers load to first request.  
- **`initialize_moderation()`** loads the Hugging Face zero-shot model in a **daemon thread** bounded by **`MODERATION_STARTUP_MODEL_LOAD_TIMEOUT_SECONDS`** (default **20**). It runs a **smoke inference** on a harmless sentence.  
- If moderation fails (missing deps, timeout, load error), the service **still starts**; **`moderate()`** uses **degraded fallback-only** mode until restart.

### 4.3 OCR

- **Library:** EasyOCR.  
- **Languages:** `easyocr.Reader(["en"], gpu=False)` — **English-only** configuration. French (and mixed FR/EN) text may still be partially recognised depending on script and fonts; this is a known limitation for purely French screenshots.  
- **Output:** Space-joined line texts from `readtext`, then stripped.

### 4.4 Moderation model

- **Default model:** `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli` (multilingual NLI-oriented checkpoint, suitable for zero-shot classification).  
- **Override:** `MODERATION_MODEL_NAME`.  
- **Mechanism:** Hugging Face `pipeline("zero-shot-classification", ..., multi_label=True)` with a fixed list of **hypothesis strings** and a **hypothesis template**.

**Hypothesis template** (default): `This text contains {}.`

**Hypothesis → short label** (from `config.py`):

| Hypothesis (model input) | `matchedKeywords` label |
|--------------------------|-------------------------|
| self-harm or suicide | `self-harm` |
| violence or physical harm | `violence` |
| hate speech or identity attack | `hate speech` |
| harassment or bullying | `harassment` |
| sexual content | `sexual content` |
| threat or intimidation | `threat` |

There is **no** “safe” label: safety is implied when no hypothesis reaches high probability; the aggregate score stays low.

### 4.5 Risk score and category (model path)

1. For each label, the pipeline returns a score in `[0, 1]`.  
2. **Aggregate `riskScore`** = **maximum** of per-label scores, capped at **1.0**, rounded to **2** decimals.  
3. **`matchedKeywords`:** labels sorted by descending score, **including only** those with score ≥ **`MATCHED_KEYWORDS_THRESHOLD`**.  
4. **Category** (same thresholds for API as in eval):

   - `dangerous` if `riskScore >= DANGEROUS_THRESHOLD`  
   - else `risky` if `riskScore >= RISKY_THRESHOLD`  
   - else `safe`

**Calibrated defaults** (env vars in parentheses):

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `RISKY_THRESHOLD` | `0.4` | `MODERATION_RISKY_THRESHOLD` |
| `DANGEROUS_THRESHOLD` | `0.85` | `MODERATION_DANGEROUS_THRESHOLD` |
| `MATCHED_KEYWORDS_THRESHOLD` | `0.6` | `MODERATION_MATCHED_KEYWORDS_THRESHOLD` |
| `SHORT_TEXT_FALLBACK_THRESHOLD` | `5` | Min **non-whitespace** characters before calling the model (`MODERATION_SHORT_TEXT_FALLBACK_THRESHOLD`) |
| `CACHE_SIZE` | `256` | LRU cache entries for repeated identical OCR strings (`MODERATION_CACHE_SIZE`) |
| `STARTUP_MODEL_LOAD_TIMEOUT_SECONDS` | `20` | Max wait for model load at startup (`MODERATION_STARTUP_MODEL_LOAD_TIMEOUT_SECONDS`) |

### 4.6 Fallback behaviour (`moderation_service.moderate`)

Fallback is used when:

| Condition | Reason string (logged) |
|-----------|------------------------|
| Empty OCR text | `empty OCR text` |
| Normalised length &lt; short-text threshold | `OCR text too short` |
| Classifier not ready (degraded startup) | e.g. `classifier not ready` / startup error message |
| Exception during inference | `exception during model inference: …` |

Fallback calls **`risk_scoring.analyze_text`**: weighted **signal rules**, fuzzy token matching (Levenshtein) for OCR noise, regex patterns, and context windows. It returns `matched_keywords`, `risk_score`, and **`display_text`** with canonical keyword substitution for parent-facing UI.

**Important:** In `main.py`, the HTTP **`category`** field is always computed with **`category_from_model_score(risk_score)`** (0.4 / 0.85 thresholds), **not** with `risk_scoring.category_from_score`, so fallback categories align with the same three-band contract as the model.

`ModerationResult` exposes **`used_fallback`**, **`fallback_reason`**, and **`inference_ms`** (0 when fallback skips the transformer).

### 4.7 HTTP API (AI service)

**`GET /health`**  
Returns `{"status":"ok"}` when the process is up (does not guarantee the model finished loading).

**`POST /analyze`**  
Body: `{ "image": "<base64>" }` — **required**; empty or missing → **400**. Invalid Base64 or image decode → **400**. OCR failure → **500**.

Response model (JSON keys as returned):

| Field | Type | Meaning |
|-------|------|---------|
| `text` | string | Raw OCR text |
| `displayText` | string | Parent-facing line (keyword normalisation when fallback; otherwise typically same as OCR) |
| `matchedKeywords` | string[] | Labels above keyword threshold |
| `riskScore` | number | Aggregate score |
| `category` | string | `safe` \| `risky` \| `dangerous` |

---

## 5. Backend (Node.js / Express)

### 5.1 Stack

- Express, `cors`, `morgan`, `dotenv`.  
- Body parser: **`express.json({ limit: '15mb' })`** for large Base64 payloads.  
- **Prisma** with **PostgreSQL**.  
- **axios** to call the AI service.

### 5.2 Environment variables (`backend/.env.example`)

| Variable | Role |
|----------|------|
| `PORT` | HTTP port (default **3000**). |
| `DATABASE_URL` | PostgreSQL connection string. |
| `AI_ANALYZE_URL` | Full URL to AI analyse endpoint (default **`http://127.0.0.1:8000/analyze`**). |
| `AI_REQUEST_TIMEOUT_MS` | Axios timeout (default **10000**; increase for slow CPU OCR+inference, e.g. **60000**). |

### 5.3 Routes (all under `/api`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness JSON. |
| POST | `/analyze` | Run pipeline; persist if `image` provided. |
| GET | `/user/:id/history` | Paginated analyses + missions (`skip`, `take`). |
| GET | `/user/:id/missions` | Paginated missions only. |
| GET | `/user/:id/summary` | Points, mission count, average risk, dangerous analysis count. |

### 5.4 `POST /api/analyze`

**Body:**

- `userId` — **positive integer** (also used as explicit primary key on first `User` create).  
- `age` — **non-negative integer**.  
- `image` — optional; if absent or empty after trim, **no AI call** and **no DB write**: returns a **preview** payload with `analysis.id === null`, `mission.status === "preview"`.

**Success shape (abbreviated):**

- `success`, `timestamp`  
- `analysis`: `text`, `displayText`, `matchedKeywords`, `riskScore`, `category`, `usedAI`, ids and timestamps when persisted  
- `mission`: `mission` (string), `points`, `status` (`pending` when stored)  
- `user`: `id`, `points`, `createdAt`

**Errors:** validation **400**; AI/DB failures **500** with message.

### 5.5 Mission assignment (`analyzeService.missionForRiskScore`)

Missions depend **only** on `riskScore` from the AI response:

| Condition | Mission | Points |
|-----------|---------|--------|
| `riskScore < 0.3` | Continue your activity responsibly | 2 |
| `0.3 ≤ riskScore ≤ 0.7` | Take a 10-minute break | 5 |
| `riskScore > 0.7` | Go outside for 20 minutes | 10 |

So a **dangerous** category with score **0.98** always receives the **20-minute / 10-point** mission.

### 5.6 Persistence (Prisma)

**`User`:** `id`, `age`, `points`, `createdAt`.  
**`Analysis`:** OCR/moderation fields + `usedAI`.  
**`Mission`:** text, points, `status` default **`pending`**.

**`getSummary`:** aggregates `points`, `totalMissions`, count of analyses with `category === 'dangerous'`, and `_avg.riskScore` over all analyses for that user.

---

## 6. Demo UI (`demo/index.html`)

- **Static single file**; no bundler.  
- Fields: **API base** (default `http://localhost:3000`), **user id**, **age**, image file upload.  
- File → **raw Base64** (no `data:` URL prefix), matching backend/AI expectations.  
- Actions: **Run analyze**, **Load summary**, **Load history** (uses `take`/`skip` query params).  
- **Serve over HTTP** (e.g. `npx serve -l 5173`) — avoid `file://` for `fetch` and CORS consistency.

---

## 7. Offline evaluation

- **Script:** `python evaluate_moderation.py` (from `ai-service/` with app on `PYTHONPATH` / venv active).  
- **Data:** `moderation_eval_dataset.json` — per case: `text`, `expectedCategory`, `expectedRiskMin`/`Max`, `expectedLabels`, `expectFallback`.  
- **Metrics printed:** per-case category, risk band, label set diff, fallback flag, inference time; summary counts for category/risk/fallback/label exact match.

**Reference success case (hate speech, mixed FR/EN):** id `danger-fr-en-hate-mixed` — with calibrated thresholds, expect **`dangerous`**, **risk ≈ 0.98**, **`hate speech`** in matched labels, **no fallback** on clean text.

---

## 8. Design notes and limitations

1. **Model conservatism:** Harassment-like samples can still yield very high max-label scores (e.g. ≥ 0.93), so they may remain **`dangerous`** even with **`DANGEROUS_THRESHOLD = 0.85`**. Raising the threshold further risks borderline hate-speech cases; this trade-off was accepted for the PFE.  
2. **OCR noise:** Real screenshots produce merged or garbled tokens; moderation is robust in tests but **not identical** to eval-on-clean-text.  
3. **EasyOCR `en` only:** Full French OCR quality is not guaranteed; mixed or Latin script may partially work.  
4. **Latency:** First model load and cold OCR are slow; demo machines should allow sufficient **`AI_REQUEST_TIMEOUT_MS`**.  
5. **Security:** No authentication on APIs in this academic prototype; production would require auth, rate limits, and content-handling policies.

---

## 9. Operational checklist (local demo)

1. Start PostgreSQL; set `DATABASE_URL`; `npx prisma migrate deploy` (or `db push`) and `npm start` in `backend/`.  
2. Start AI service: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8000` from `ai-service/`.  
3. Confirm `GET /health` on both services.  
4. Serve `demo/` over HTTP; run analyze with a test image.  
5. Optional: regenerate E2E payload with `backend/scripts/gen_hate_analyze_payload.py` and `curl` `POST /api/analyze` with the generated `tmp_analyze_hate.json` (file is gitignored).

---

## 10. References

- Model card (Hugging Face): [MoritzLaurer/mDeBERTa-v3-base-mnli-xnli](https://huggingface.co/MoritzLaurer/mDeBERTa-v3-base-mnli-xnli)  
- Transformers zero-shot classification: [Hugging Face pipelines documentation](https://huggingface.co/docs/transformers/main_classes/pipelines#transformers.pipeline)  
- EasyOCR: [JaidedAI/EasyOCR](https://github.com/JaidedAI/EasyOCR)

---

*Document generated for the PFE repository. Thresholds and file paths reflect the state of the codebase at the time of writing; verify `app/config.py` and `backend/.env` for deployed values.*
