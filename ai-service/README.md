# AI service (FastAPI)

Always run this service with the **project virtualenv** so PyTorch (CPU or CUDA) matches `requirements.txt`:

```powershell
cd ai-service
.\.venv\Scripts\Activate.ps1   # Windows — or use `.\run-dev.ps1` (uses `.venv\Scripts\python.exe` directly)
```

**GPU / EasyOCR:** If logs show `WARNING:easyocr...Using CPU` but `python -c "import torch; print(torch.cuda.is_available())"` is `True`, restart the server after pulling the latest code (CUDA warm-up before EasyOCR). Prefer:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

If EasyOCR still loads CPU, try **without** `--reload` once (rare Windows subprocess quirks). OCR time dominates total latency; moderation on GPU alone will not cut total time much if OCR stays on CPU.

## Dependencies

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt
```

## PyTorch: CPU vs CUDA (GPU)

The default `pip install -r requirements.txt` pulls a **CPU** build of PyTorch from PyPI (~100 MB). That is enough for development; `torch.cuda.is_available()` will be `False` unless you install a CUDA-enabled wheel.

### Why a CUDA install can fail

The official **CUDA 12.4** Windows wheel from [download.pytorch.org](https://download.pytorch.org/whl/cu124) is **~2.5 GB**. On slow or unstable networks, pip’s default read timeout can abort mid-download (`ReadTimeoutError` / `Read timed out`).

### Fix: retry with a long timeout and current pip

Upgrade pip first, then:

```powershell
pip install torch torchvision torchaudio `
  --index-url https://download.pytorch.org/whl/cu124 `
  --default-timeout 3600 `
  --retries 10
```

(`--default-timeout 3600` allows up to one hour per read chunk for a ~2.5 GB wheel; increase further if needed. Default pip timeout is 15s, which causes `Read timed out` on slow links.)

Prefer a **stable Ethernet** connection, **off-peak** hours, or download the `.whl` in a browser and install from disk:

```powershell
pip install C:\path\to\torch-2.x.x+cu124-cp310-cp310-win_amd64.whl
```

### After a failed CUDA attempt

If you uninstalled torch and the CUDA install failed, restore a working CPU build from PyPI:

```powershell
pip install "torch>=2.10.0" torchvision --default-timeout 600
```

Then retry CUDA when you have time for a multi-hour download.

### Check GPU

```powershell
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
```

You want `True` and a CUDA build (e.g. `+cu124` in the full wheel name), not `+cpu`.
