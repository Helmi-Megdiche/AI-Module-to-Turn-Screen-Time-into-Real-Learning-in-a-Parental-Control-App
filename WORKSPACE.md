# Single project root (canonical path)

Use **one** folder for opening the repo in Cursor and for running servers/tests:

**`C:\Users\helmi\OneDrive\Bureau\PFE\AI-Module-to-Turn-Screen-Time-into-Real-Learning-in-a-Parental-Control-App`**

## How to open in Cursor / VS Code

1. **Recommended:** double-click **`PFE-Parental-Control.code-workspace`** in that folder (sets Python to `ai-service\.venv` automatically).
2. Or: **File → Open Folder…** and choose the OneDrive path above (not a `.cursor\worktrees\…` copy).

## Terminals

`cd` to that path before `npm run dev`, `uvicorn`, etc., so code and `.venv` match what you edit.

**Git worktrees** (e.g. under `.cursor\worktrees\…`) are optional; avoid using them for day-to-day work if you want a single source of truth.

This removes “edited here but ran from another clone” confusion.
