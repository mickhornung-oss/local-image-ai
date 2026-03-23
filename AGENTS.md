# Repo Notes

- Use `scripts/setup_windows.ps1` to provision a compatible Python venv for ComfyUI on Windows.
- Do not use the globally installed Python 3.14 for ML dependencies in this repo.
- Keep large model files out of git; place them under `vendor/ComfyUI/models/`.
- The automation client under `python/` talks to ComfyUI over `http://127.0.0.1:8188`.
