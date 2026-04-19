# StoryForge Local

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://github.com/mickhornung-oss/local-image-ai/actions/workflows/python-tests.yml/badge.svg)](https://github.com/mickhornung-oss/local-image-ai/actions/workflows/python-tests.yml)

Lokales Schreibwerkzeug fuer kreative Textarbeit mit direkter Bruecke zu Bildmaterial.
Texte schreiben, ueberarbeiten, Bildprompts ableiten, Stil waehlen und Bilder erzeugen — alles in einer Browser-Oberflaeche auf deinem Rechner, ohne Cloud.

> **Deutsch:** StoryForge Local arbeitet textzentriert. Szenen sind das persistente Arbeitsobjekt. Bild folgt dem Text.

---

### Hinweis / Note

**DE:** StoryForge Local befindet sich in aktiver Weiterentwicklung. Die Kernfunktionen laufen bereits und liefern gute Ergebnisse, aber es gibt noch kleinere Fehler, UI-/UX-Unsauberkeiten und offenen Feinschliff. Das Projekt ist benutzbar, jedoch noch nicht vollstaendig finalisiert.

**EN:** StoryForge Local is still under active development. The core features are already working and produce good results, but there are still smaller issues, UI/UX inconsistencies, and unfinished polish. The project is usable, but not yet fully finalized.

---

## Demo

![StoryForge Local – Schreibbereich und Bildgenerierung](images/local-image-ai-demo.png)

---

## Hauptfluss

1. Neue Szene anlegen und benennen
2. Text in den Schreibbereich schreiben oder einfuegen
3. Text ueberarbeiten oder verfeinern (KI-gestuetzt)
4. Bildprompt aus Abschnitt oder ganzem Text ableiten, optional mit Negativprompt
5. Stil waehlen: Foto oder Anime
6. Bild erzeugen — Bildbezug wird der Szene zugeordnet
7. Ergebnis ansehen und an der Szene weitermachen
8. Szene speichern, spaeter wieder aufnehmen

## Features

| Feature | Details |
|---|---|
| Szenenmodell | Szenen als persistentes Arbeitsobjekt: Titel, Text, Wiederaufnahme |
| Schreibbereich | Textkörper direkt an aktive Szene gebunden |
| Textmodi | Schreiben, Ueberarbeiten, Bildprompt ableiten |
| Text-zu-Bild-Bruecke | Prompt aus Markierung oder ganzem Text, optional mit Negativprompt |
| Text-Bild-Kopplung | Erzeugte Bilder werden der aktiven Szene zugeordnet |
| Szenenbilder | Zugeordnete Bilder direkt im Szenenbereich mit Vorschau und schnellem Wiederverwenden |
| Szenenexport | Aktive Szene als lokaler Export (Markdown + JSON mit Bildbezuegen) |
| Wiederaufnahme | Aktive Szene und Textkörper bleiben nach Neustart erhalten |
| Lokaler Sprachpfad | Diktat im Schreibfluss: Aufnahme starten, lokal transkribieren, in den Textkörper einfuegen |
| Bildstilwahl | Foto/Realismus oder Anime |
| Lokale Bildgenerierung | Text-to-image, Bildanpassung und Bereichsaenderung via ComfyUI |
| Ergebnisgalerie | Vorschau, Download, Export und Wiederverwendung |
| Lokal-first | Keine API-Keys, keine Cloud, Verarbeitung auf deinem Rechner |

## Known Limitations

- **Windows-only**: ComfyUI and local model paths are Windows-specific. Linux/Docker support is not planned.
- **`python/app_server.py` is monolithic** (~4,900 lines). Sub-modules (`text_chat_store`, `generate_endpoint_flow`, etc.) are already extracted for the most complex areas.
- **Requires local setup**: ComfyUI, local LLM models, and custom nodes must be installed separately.

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
# -> Browser opens at http://127.0.0.1:8090
```

ComfyUI and local LLM models must be installed separately via `scripts/setup_windows.ps1`.

## Tech Stack

| Component | Technology |
|---|---|
| App Server | Python `http.server` (custom async handler) |
| Text AI | Local LLM via llama.cpp / text_runner |
| Image AI | ComfyUI (local, custom nodes: InstantID, PuLID) |
| Frontend | Static HTML/CSS/JS (`web/`) |
| Persistence | SQLite (`data/text_chats.sqlite3`, `data/scenes.sqlite3`) |

## Lokaler Sprachpfad

- Der Diktierbutton nimmt Audio im Browser auf und sendet es an einen lokalen Transkriptionspfad (`/speech/transcribe`).
- Die Transkription laeuft lokal ueber `faster-whisper` oder `openai-whisper` (wenn in der Projekt-venv installiert).
- Ohne lokales STT-Backend bleibt der Diktierknopf deaktiviert; Schreib- und Bildfluss bleiben unveraendert nutzbar.

## Szenen-Arbeitsraum

- Die aktive Szene zeigt Titel, Textkoerper und zugeordnete Szenenbilder in einem zusammenhaengenden Arbeitsbereich.
- Szenenbilder koennen direkt im Szenenkontext als Vorschau geoeffnet oder als Ausgangsbild wiederverwendet werden.
- Szenenexport erstellt lokal eine Markdown- und JSON-Datei mit Text und Bildbezuegen der aktiven Szene.

## Sichtpruefung

- Eine kompakte Sichtpruefungs-/Smoke-Checkliste liegt unter `docs/sichtpruefung_checkliste.md`.
- Sie deckt den Hauptpfad ab: Szene, Text, Diktat, Prompt/Negativprompt, Bildbezug, Export und Wiederaufnahme.
