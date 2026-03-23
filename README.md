# Local ComfyUI AMD DirectML Setup

This repository provisions a local ComfyUI setup for AMD GPUs on Windows and deliberately avoids the globally installed Python 3.14 for ML dependencies. ComfyUI and `torch-directml` are installed into a dedicated virtual environment created with `py -3.10` when available, or `py -3.11` as a fallback.

## Quickstart

1. Run `powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1`
2. Put at least one SDXL checkpoint into `vendor/ComfyUI/models/checkpoints/`
3. Normal user start: run `.\Start_Local_Image_AI.cmd`
4. Technical start: `powershell -ExecutionPolicy Bypass -File .\scripts\run_stack.ps1 start`
5. Check the stack state with `powershell -ExecutionPolicy Bypass -File .\scripts\run_stack.ps1 status`
6. Run `powershell -ExecutionPolicy Bypass -File .\scripts\smoke_test.ps1`
7. Stop only the stack-managed services with `powershell -ExecutionPolicy Bypass -File .\scripts\run_stack.ps1 stop`
8. Check generated images under `vendor/ComfyUI/output`

## Local Versioning

- The project now has a local Git baseline for code, docs, config, and UI changes.
- Runtime artifacts under `vendor/` and generated/user data under `data/` stay local and are intentionally ignored.
- Use `git status` and `git diff` before and after change blocks to keep future agent runs recoverable.

## Why Python 3.14 Is Not Used

The machine can keep Python 3.14 installed for general work, but many Windows ML wheels still target Python 3.10 or 3.11 first. This repo therefore forces a separate venv under `vendor/ComfyUI/venv` using the Python Launcher `py`. The setup script prefers Python 3.10 and falls back to 3.11.

If neither version is installed, `scripts/setup_windows.ps1` stops with explicit instructions:

- `winget install Python.Python.3.10`
- Manual fallback: install Python 3.10.x 64-bit from python.org and enable the Python Launcher (`py`)

## Repository Layout

```text
.
|-- README.md
|-- AGENTS.md
|-- scripts/
|   |-- setup_windows.ps1
|   |-- run_comfyui.ps1
|   `-- smoke_test.ps1
|-- vendor/
|   `-- ComfyUI/
`-- python/
    |-- requirements.txt
    |-- comfy_client.py
    |-- render_text2img.py
    `-- workflows/
```

## Models

Place model files here:

- SDXL checkpoints: `vendor/ComfyUI/models/checkpoints/`
- VAE files if needed: `vendor/ComfyUI/models/vae/`
- LoRAs if needed: `vendor/ComfyUI/models/loras/`

The provided API workflows use a placeholder checkpoint name, `sd_xl_base_1.0.safetensors`. Replace that file name in the workflow JSON if your checkpoint uses a different name, or rename your local file to match.

## AMD / DirectML Notes

- Start ComfyUI with `--directml`; the run script already does this.
- DirectML is functional on AMD, but usually slower than CUDA. Expect lower throughput, especially with SDXL.
- If VRAM pressure is high, reduce `width`, `height`, `steps`, or switch to a smaller batch size.
- Some ComfyUI custom nodes assume CUDA and will not work on DirectML. Start with the stock nodes first.
- First-run model loading can take time; the UI may appear idle while weights are read from disk.
- If generation fails with out-of-memory errors, start at `1024x1024` or lower and reduce steps to 20-24.

## Workflows

Two minimal API workflows are included:

- `python/workflows/sdxl_text2img_api_photoreal.json`
- `python/workflows/sdxl_text2img_api_anime.json`

They are intentionally simple and rely on standard ComfyUI nodes. The render script updates prompt text, negative prompt, seed, steps, CFG, width, and height when those fields exist.

If your local ComfyUI version or model setup differs, export a fresh API workflow from ComfyUI:

1. Build a working text-to-image graph in the UI
2. Use `Save (API Format)`
3. Replace the corresponding JSON file under `python/workflows/`

## Scripts

### `scripts/setup_windows.ps1`

- Verifies the Python Launcher `py`
- Detects Python 3.10 first, otherwise 3.11
- Clones ComfyUI into `vendor/ComfyUI` if missing
- Creates `vendor/ComfyUI/venv`
- Installs `torch-directml`, ComfyUI requirements, and the Python client requirements
- Prints next steps

### `scripts/run_comfyui.ps1`

- Activates the dedicated ComfyUI venv
- Starts ComfyUI on port `8188` with `--directml`

### `scripts/run_stack.ps1`

- Starts the full local stack in dependency order: ComfyUI, text runner, text service, app
- Reports a short status table for all four services on `start`, `status`, and `stop`
- Avoids duplicate starts by reusing already running stack services
- Stops only the processes that were started by the stack launcher itself

### `Start_Local_Image_AI.cmd`

- Simple project-root entry point for normal users on Windows
- Reuses `scripts/run_stack.ps1 start` unchanged
- Prints the local app URL and opens `http://127.0.0.1:8090` after a successful start

### `scripts/smoke_test.ps1`

- Checks whether ComfyUI responds over HTTP
- Runs a sample render through the Python client
- Prints the output directory and the newest generated file

## Python Automation

The HTTP client lives under `python/` and can queue API-format workflows against `http://127.0.0.1:8188`.

Example:

```powershell
python\comfy_client.py --help
python\render_text2img.py --workflow photoreal --prompt "cinematic portrait, shallow depth of field"
```

## Troubleshooting

### `py` command not found

Install Python with the launcher:

- `winget install Python.Python.3.10`
- Or manually install Python 3.10.x 64-bit and ensure the Python Launcher is enabled

### Setup still uses Python 3.14

It should not. The setup script only accepts `py -3.10` or `py -3.11`. If it cannot find those versions, it exits instead of creating the ML venv with Python 3.14.

### ComfyUI starts but generation fails immediately

- Confirm a valid SDXL checkpoint exists in `vendor/ComfyUI/models/checkpoints/`
- Check the checkpoint name inside the selected workflow JSON
- Review the ComfyUI terminal output for missing model or node errors

### Port 8188 already in use

Stop the existing process, or free the port before running `scripts/run_comfyui.ps1`. The Python client reports a clear error if it cannot reach the expected API.

### Output image is not found

The smoke test waits for a new file under `vendor/ComfyUI/output`. If a workflow writes elsewhere, update the workflow or pass `--output-dir` to the Python render script.
