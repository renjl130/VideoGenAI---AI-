# VideoGenAI - Start Here

## Recommended setup

From the project directory, install the pinned NVIDIA CUDA environment:

```powershell
python scripts/setup_environment.py --backend cuda --venv .venv
```

Then verify that PyTorch can use the NVIDIA GPU:

```powershell
.\.venv\Scripts\python.exe scripts/verify_project.py --mode environment
```

Start the app with `start.bat`, or run:

```powershell
.\.venv\Scripts\python.exe launcher.py
```

## First model

Choose `wan2.1-t2v-1.3b` in the application and click **Download Model**. The complete Diffusers package is approximately 27 GiB. Interrupted downloads remain incomplete and can be resumed safely; only a **Ready** model may be loaded.

## Important

- `requirements.txt` intentionally excludes PyTorch. Do not use a generic package mirror as a substitute for the CUDA setup workflow.
- Run `scripts/verify_project.py --mode runtime` only after the complete default model is present.
- An 8 GiB GPU should use the low-VRAM performance profile and start with a small T2V request.