# Jury demo (static web page)

Single file: `index.html` — no build step.

## Run

1. Start the **backend**: `cd backend && npm run dev` (port **3000**).
2. Optional: start the **AI service** on **8000** if you want real OCR (not simulation).
3. Serve this folder over **HTTP** (avoid `file://` — CORS / fetch quirks):

```bash
cd demo
npx --yes serve -l 5173
```

Open **http://localhost:5173** in the browser.

## What to show

- **Analyze**: pick an image or leave empty for simulated AI; shows category, risk, text, mission, raw JSON.
- **Summary**: points, average risk, dangerous count, mission count.
- **History**: last analyses and missions (with `displayText` / keywords when stored).

You can change **API base URL** and **User ID** at the top if needed.
