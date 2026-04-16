# Local Image AI

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Version](https://img.shields.io/badge/version-v1-green.svg)](https://github.com/mickhornung-oss/local-image-ai/releases)
[![codecov](https://codecov.io/gh/mickhornung-oss/local-image-ai/branch/main/graph/badge.svg)](https://codecov.io/gh/mickhornung-oss/local-image-ai)
[![Tests](https://github.com/mickhornung-oss/local-image-ai/actions/workflows/python-tests.yml/badge.svg)](https://github.com/mickhornung-oss/local-image-ai/actions)

Local Windows application combining text AI (chat, writing, translation) and image AI (generation, inpainting, identity transfer) in a single browser-based UI — powered by local LLMs and ComfyUI, no cloud required.

> **Deutsch:** Lokale Windows-App fuer Text-KI und Bild-KI im selben Produkt.

## Known Limitations

- **Windows-only**: ComfyUI and local model paths are Windows-specific. Linux/Docker support is not planned.
- **`python/app_server.py` is monolithic** (~4,900 lines). Sub-modules (`text_chat_store`, `generate_endpoint_flow`, etc.) are already extracted for the most complex areas.
- **Requires local setup**: ComfyUI, local LLM models, and custom nodes must be installed separately.

## Features

| Feature | Details |
|---|---|
| Text AI | Chat with persistent slots, writing assistance, translation, prompt generation |
| Image AI | Text-to-image, inpainting, area editing via ComfyUI |
| Identity Transfer | Single-reference, multi-reference, and hybrid mask variants |
| Result Gallery | Preview, download, export, and reload generated images |
| Local-only | No API keys, no cloud — all processing runs on your machine |

## Quick Start

```powershell
# 1. Clone and set up
git clone https://github.com/mickhornung-oss/local-image-ai.git
cd local-image-ai
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Start
Start_Local_Image_AI.cmd
# → Browser opens at http://127.0.0.1:8090
```

ComfyUI and local LLM models must be installed separately via `scripts/setup_windows.ps1`.

## Tech Stack

| Component | Technology |
|---|---|
| App Server | Python `http.server` (custom async handler) |
| Text AI | Local LLM via llama.cpp / text_runner |
| Image AI | ComfyUI (local, custom nodes: InstantID, PuLID) |
| Frontend | Static HTML/CSS/JS (`web/`) |
| Persistence | SQLite (`data/text_chats.sqlite3`) |
