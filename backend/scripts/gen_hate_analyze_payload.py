"""Write tmp_analyze_hate.json for POST /api/analyze (E2E test)."""
from __future__ import annotations

import base64
import io
import json
from pathlib import Path

from PIL import Image, ImageDraw

BACKEND_DIR = Path(__file__).resolve().parent.parent
OUT = BACKEND_DIR / "tmp_analyze_hate.json"

LINES = [
    "Tous les arabes sont des terrorists.",
    "They should go back to their country.",
    "Les immigres sont des rats. I hate them all.",
]


def main() -> None:
    img = Image.new("RGB", (920, 260), color="white")
    draw = ImageDraw.Draw(img)
    y = 20
    for line in LINES:
        draw.text((24, y), line, fill="black")
        y += 58
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    payload = {"userId": 99901, "age": 12, "image": b64}
    OUT.write_text(json.dumps(payload), encoding="utf-8")
    print(f"Wrote {OUT} (base64 length {len(b64)})")


if __name__ == "__main__":
    main()
