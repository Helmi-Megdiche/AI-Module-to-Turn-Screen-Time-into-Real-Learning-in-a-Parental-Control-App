# Latest Technical Report for ChatGPT

## Project title

AI Module to Turn Screen Time into Real Learning in a Parental Control App

## 1. Current project purpose

This Final Year Project (PFE) is a hybrid AI + backend parental control system. Its goal is not only to block harmful content, but to transform children's screen time into a real educational experience.

The system is designed to:

- analyze what appears on the child's screen
- detect dangerous or inappropriate content
- generate real-world educational missions
- apply gamification through points and missions
- provide parents with monitoring and reward tools

## 2. Current system architecture

The project currently contains three main parts.

### 2.1 Backend

Stack:

- Node.js
- Express
- Prisma
- PostgreSQL

Responsibilities:

- receive analysis requests from the frontend/demo
- call the AI service
- store OCR and moderation results
- generate missions
- expose parent monitoring endpoints

Existing endpoints:

- `POST /api/analyze`
- `GET /api/user/:id/history`
- `GET /api/user/:id/missions`
- `GET /api/user/:id/summary`
- `GET /api/health`

Important constraint:

The backend contract must not change. The AI service must continue to return:

```json
{
  "text": "string",
  "displayText": "string",
  "matchedKeywords": ["string"],
  "riskScore": 0.82,
  "category": "safe | risky | dangerous"
}
```

### 2.2 AI service

Stack:

- Python
- FastAPI
- EasyOCR

The AI service is responsible for:

- decoding incoming base64 screenshots
- running OCR
- analyzing extracted text
- returning a normalized moderation result to the backend

### 2.3 Demo UI

A lightweight HTML demo exists to:

- upload an image
- trigger analysis
- show OCR text
- show score and category
- show matched labels
- show generated mission
- show summary and history

## 3. Detection evolution so far

### 3.1 Original approach

The first detection layer was based on manual keyword rules in `ai-service/app/services/risk_scoring.py`.

This approach was improved over time with:

- contextual rule groups
- weighted risk scoring
- fuzzy OCR-tolerant matching
- specific self-harm and danger signals

However, it still remained rule-driven and therefore limited.

### 3.2 Main weaknesses of pure rule-based logic

- difficult to scale
- hard to maintain
- weak semantic generalization
- sensitive to OCR noise
- poor handling of varied French and English phrasing

### 3.3 OpenAI moderation attempt

An OpenAI moderation integration was tested as a quick production-style upgrade.

What was verified:

- API key reading worked
- model listing worked
- requests reached OpenAI successfully

Why it was removed:

- the project hit quota and billing issues
- real moderation calls returned `insufficient_quota`
- the project requirement now is fully local inference

Result:

- OpenAI logic was removed from the codebase
- the project returned to a local-only architecture

## 4. Latest implemented update

The latest real update is the addition of a **local multilingual transformer moderation layer** inside the AI service.

This was implemented in:

- `ai-service/app/services/moderation_service.py`
- `ai-service/app/main.py`
- `ai-service/requirements.txt`

The fallback layer remains in:

- `ai-service/app/services/risk_scoring.py`

## 5. Latest pipeline

The AI pipeline is now:

```text
base64 image
  -> image decoding
  -> OCR with EasyOCR
  -> local transformer moderation model
  -> riskScore + category + matchedKeywords + displayText
  -> fallback to rule-based scoring if text is too short or the model fails
```

In practice:

1. The image is received in base64.
2. It is converted into a PIL image.
3. EasyOCR extracts text.
4. The extracted text is passed to `moderation_service.py`.
5. If the moderation model cannot be used, the system falls back to `risk_scoring.py`.

## 6. Latest moderation module

New file created:

- `app/services/moderation_service.py`

The current implementation uses:

- Hugging Face `transformers`
- `pipeline("text-classification", ...)`
- CPU inference only with `device=-1`

Current model:

- `unitary/multilingual-toxic-xlm-roberta`

Main behavior:

- load the model once and reuse it
- classify OCR text after extraction
- compute a normalized `riskScore`
- derive `category`
- return `matchedKeywords`
- use fallback rules if OCR text is too short or inference fails

## 7. Mapping logic currently implemented

The current moderation thresholds are:

- if `score >= 0.75` -> `dangerous`
- if `0.4 <= score < 0.75` -> `risky`
- if `score < 0.4` -> `safe`

`matchedKeywords` currently contains model labels whose score is above `0.4`.

`displayText` is currently the same as the OCR text.

Fallback behavior:

- if normalized OCR text length is below `5`, use `risk_scoring.py`
- if the transformer fails, use `risk_scoring.py`

## 8. Actual latest code state

### 8.1 FastAPI integration

The service now preloads both OCR and the moderation model at startup.

Relevant file:

- `ai-service/app/main.py`

Current behavior:

- OCR is still the first stage
- moderation is now the main analysis layer
- fallback is transparent to the backend
- API response format remains unchanged

### 8.2 Moderation service behavior

Relevant file:

- `ai-service/app/services/moderation_service.py`

Current technical design:

- singleton-style cached classifier via `_classifier`
- model loaded once through `get_classifier()`
- score extraction from Hugging Face pipeline output
- mapping from model score to app category
- conversion to the existing `RiskAnalysis` shape

### 8.3 Requirements added

Relevant file:

- `ai-service/requirements.txt`

New dependencies added:

- `transformers`
- `torch`
- `sentencepiece`
- `protobuf`

These were necessary because the chosen XLM-Roberta model requires extra tokenizer dependencies on this machine.

## 9. Important limitation discovered in the latest update

This is the most important technical point to give to ChatGPT:

Although the requested model was integrated successfully, the model itself exposes only one effective label in this setup:

- `toxic`

This means the current model does **not** provide rich moderation classes such as:

- self-harm
- violence
- hate
- harassment

Instead, it mainly returns a toxicity score.

That creates an architectural mismatch with the project ambition, because the parental control system needs more fine-grained safety signals than a single toxicity label.

## 10. Practical consequence of this limitation

With the current model:

- `riskScore` works
- `category` works
- the response format is preserved
- CPU inference is local
- French/English toxicity detection is improved compared to pure rules

But:

- `matchedKeywords` is usually just `["toxic"]` or `[]`
- the model is not sufficiently expressive for categories like self-harm and violence
- part of the project's semantic safety objective still depends on fallback rules

In short:

The implementation is technically correct, but the chosen model is only a partial fit for the full moderation objective.

## 11. What was validated technically

The following points were validated during implementation:

- `transformers` installation succeeded
- `torch` is available locally
- model config loads correctly
- the classifier can be instantiated
- direct sample inference returns a real toxicity score
- the FastAPI service can preload the moderation model
- no backend contract change was introduced
- linter errors were not introduced in the modified files

## 12. Why this still matters as a useful milestone

Even with the limitation above, this update is still important because it proves:

- the AI service can host a local NLP moderation model
- transformer inference fits inside the current architecture
- OCR -> moderation -> normalized backend response works cleanly
- fallback logic can coexist with a model-first design

So this is a successful **architectural migration** from rule-first logic to model-first logic.

## 13. Current recommendation after the latest update

The best next step is **not** to go back to pure keyword engineering.

The best next step is:

1. keep the current `moderation_service.py` structure
2. replace the current single-label toxicity model with a richer moderation model
3. preserve `risk_scoring.py` as fallback for OCR noise and exceptional cases

In other words:

- the architecture is now correct
- the current model is the weak point

## 14. Best guidance for ChatGPT

If ChatGPT is asked to help on the next iteration, it should understand the following:

- the project already has a working local transformer moderation integration
- the backend must stay unchanged
- OCR must remain in the pipeline
- the fallback rules must remain available
- the main improvement now is **model quality / label richness**, not basic plumbing

## 15. Prompt to give to ChatGPT

Use the following prompt:

---

I have a parental control PFE project with three parts:

- backend in Node.js / Express / Prisma / PostgreSQL
- AI service in Python / FastAPI
- demo HTML UI

The backend contract must not change. The AI service must continue to return:

```json
{
  "text": "string",
  "displayText": "string",
  "matchedKeywords": ["string"],
  "riskScore": 0.82,
  "category": "safe | risky | dangerous"
}
```

Current AI pipeline:

```text
base64 image -> OCR with EasyOCR -> local transformer moderation -> normalized response
```

I have already implemented a local moderation module in `app/services/moderation_service.py` using Hugging Face `transformers`, with fallback to `risk_scoring.py` when OCR text is too short or the model fails.

The currently integrated model is:

- `unitary/multilingual-toxic-xlm-roberta`

This model works technically, but in practice it mainly exposes one label:

- `toxic`

So it does not provide rich categories like self-harm, violence, hate, and harassment, which are important for my parental control use case.

I want you to help me choose and integrate a better fully local multilingual moderation model that:

- runs on CPU
- supports French and English
- works after OCR
- gives richer moderation signals than a single toxicity score
- keeps the exact same backend response contract
- keeps `risk_scoring.py` as fallback only

Please propose:

1. the best model candidates
2. the best one for a PFE scope
3. how to adapt `moderation_service.py`
4. how to map model outputs to:
   - `matchedKeywords`
   - `riskScore`
   - `category`
5. how to evaluate false positives and false negatives
6. how to keep inference CPU-friendly

---

## 16. Final technical conclusion

Latest update status:

- local transformer moderation integration: done
- OCR-first architecture preserved: done
- backend response compatibility preserved: done
- fallback rule layer preserved: done
- fully local inference: done
- rich moderation categories: not yet achieved with the current chosen model

So the project has successfully moved to a stronger architecture, but it now needs a **better local moderation model** to fully satisfy the original parental control detection goals.
