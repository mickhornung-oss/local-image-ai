# Technische Abschlussdoku MP-04

Stand: 2026-04-07

## Zweck

Diese Doku ist die technische Abschluss- und Uebergabedoku fuer den aktiven Produktstand nach MP-04.

Sie beschreibt:
- Repo-Struktur und aktive Hauptkomponenten
- Start-, Status-, Stop- und Pruefpfade
- lokale Services, Ports und technische Grenzen
- produktive versus experimentelle Bereiche
- bekannte Hotspots und Vorsichtspunkte fuer Weiterarbeit

## 1. Aktive Architektur auf Repo-Ebene

Das Produkt ist eine lokale Windows-App mit Browser-UI und vier lokalen Loopback-Diensten:

- Browser-UI: `web/index.html`
- Haupt-App / HTTP-Orchestrierung: `python/app_server.py` auf `127.0.0.1:8090`
- Text-Service: `python/text_service.py` auf `127.0.0.1:8091`
- Text-Runner: `vendor/text_runner/` auf `127.0.0.1:8092`
- Bild-Engine / ComfyUI: `vendor/ComfyUI/` auf `127.0.0.1:8188`

## 2. Produktive Hauptverzeichnisse und Module

- `web/`
  - sichtbare Hauptoberflaeche, Basismodus, Ergebniswelt, Experimentaltrennung
- `python/app_server.py`
  - Hauptserver, HTTP-Endpunkte, Routing, Ablaufkoordination zwischen Text-, Bild- und Ergebnispfaden
- `python/text_service.py`
  - Textmodi, Textprofilsteuerung, Prompting- und Longform-Logik
- `python/text_chat_store.py`
  - Chat-Persistenz in SQLite
- `python/text_chat_requests.py`
  - chatnahe Request-Normalisierung
- `python/text_chat_responses.py`
  - chatnahe Antwortaufbereitung
- `python/text_chat_service_orchestration.py`
  - Kopplung Chat <-> Text-Service
- `python/image_input_validation.py`
  - Upload- und Eingabebild-Validierung
- `python/upload_store.py`
  - Ablage und Metadaten fuer Bild-/Masken-/Referenzuploads
- `python/result_output.py`
  - Ergebnisfinalisierung, Export, Delete-Nachlauf
- `python/generate_endpoint_flow.py`
  - handlernahe Bild-Generate-Steuerung
- `python/general_generate_flow.py`
  - vorbereitende Bild-Generate-Normalisierung
- `config/`
  - produktrelevante lokale Konfigurationen, insbesondere `config/text_service.json`
- `scripts/`
  - Start-, Stop-, Status-, Setup- und Smoke-Skripte
- `tests/`
  - lokale Unit- und Integrationsabsicherung

## 3. Produktiv, experimentell, historisch

Produktiv:
- Text-KI mit gespeicherten Chats
- `Standard`, `Starkes Schreiben`, `Mehrsprachig`
- `Neues Bild erstellen`
- `Bild anpassen`
- `Bereich im Bild aendern`
- Ergebniswelt mit Vorschau, Download, Export, Wiederverwendung, Entfernen aus Hauptliste

Experimentell:
- `Neue Szene mit derselben Person`
- Single-Reference, Multi-Reference, Transfer, Masken-Hybrid
- `identity_research`
- experimentelle Bild-Audit- und Architektur-Doku unter `docs/v4_*`, `docs/v6_*`, `docs/v7_*`, `docs/v9_*`, `docs/v11_*`

Historisch / Nebenbestand:
- `backend/`
- `vscode-extension/`
- `main.py`
- `stable-diffusion-webui/`
- `docs/architecture.md`
- `docs/project_documentation.md`

## 4. Offizielle Betriebs- und Pruefpfade

Hauptstart:
1. `Start_Local_Image_AI.cmd`
2. Browser auf `http://127.0.0.1:8090`

Technischer Start:
1. `powershell -ExecutionPolicy Bypass -File .\scripts\run_stack.ps1 -Action start -UserMode`

Status:
1. `Status_Local_Image_AI.cmd`
2. oder `powershell -ExecutionPolicy Bypass -File .\scripts\run_stack.ps1 -Action status -UserMode`

Stop:
1. `Stop_Local_Image_AI.cmd`
2. oder `powershell -ExecutionPolicy Bypass -File .\scripts\run_stack.ps1 -Action stop -UserMode`

Setup:
- `powershell -ExecutionPolicy Bypass -File .\scripts\setup_windows.ps1`

## 5. Reale Abnahme- und Smoke-Pfade

Python-Tests:
- `venv\Scripts\python.exe -m unittest discover -s tests`

Stack-Status:
- `powershell -ExecutionPolicy Bypass -File .\scripts\run_stack.ps1 -Action status -UserMode`

Bild-Smoke:
- `powershell -ExecutionPolicy Bypass -File .\scripts\smoke_test.ps1`

UI-Smoke:
- `powershell -ExecutionPolicy Bypass -File .\scripts\ui_smoke_test.ps1`

Health / Readiness:
- `GET /health`
- `GET /identity-reference/readiness`
- `GET /identity-transfer/readiness`

## 6. Sichtbare Produktstruktur

Basismodus:
- `Text schreiben / Text-KI nutzen`
- `Neues Bild erstellen`
- `Bild anpassen`
- `Bereich im Bild aendern`

Erweitert / Experimental:
- experimenteller Szenenpfad mit derselben Person
- experimentelle Mehrbild-/Transfer-Pfade
- technische Readiness- und Spezialstarts

Ergebniswelt:
- letzte Bilder mit Vorschau
- Download
- Export in Exportordner
- Wiederverwendung als Ausgangsbild
- Entfernen aus der app-verwalteten Hauptliste

## 7. Bekannte technische Grenzen

- `web/index.html` bleibt ein grosser UI-Hotspot mit viel zusammenhaengender HTML/CSS/JS-Logik.
- `python/app_server.py` bleibt der groesste produktive Server-Hotspot.
- `Starkes Schreiben` ist auf dem lokalen CPU-Stack brauchbar, aber deutlich langsamer als `Standard` und `Mehrsprachig`.
- `Bereich im Bild aendern` ist kein verlaesslicher Grossumbaupfad fuer starke Kleidungs-/Formwechsel.
- Experimentelle Identity-Pfade bleiben technisch erreichbar, aber nicht produktiv freigegeben.

## 8. Hotspots / Vorsichtspunkte

- `web/index.html`
  - hohes Regressionsrisiko bei sichtbarer UI-Logik, Zustandswechseln und Ergebniswelt
- `python/app_server.py`
  - zentrale Endpunkt- und Ablaufverdrahtung
- `python/text_service.py`
  - textnahe Laengen-, Prompt- und Profilsteuerung
- `scripts/run_stack.ps1`
  - offizieller Start- und Statuspfad
- `scripts/ui_smoke_test.ps1`
  - reale Sichtabsicherung fuer den Hauptpfad; bei UI-Aenderungen zuerst hier pruefen

## 9. Repo- und Laufzeitgrenzen

Aktiver Produktcode:
- `python/`
- `web/`
- `scripts/`
- `config/`
- `tests/`
- Root-Startdateien

Lokale Laufzeitbestaende:
- `data/`
- `vendor/ComfyUI/`
- `vendor/text_runner/`
- `vendor/text_models/`
- `venv/`
- `local_backups/`

Hinweis:
- Modelle gehoeren nicht in Git.
- ComfyUI- und ML-Abhaengigkeiten nicht mit globalem Python 3.14 betreiben.

## 10. Uebergabehinweise

- Fuer Produktbild und Hauptfunktionen gilt `docs/product_core_mp01.md`.
- Fuer Praesentation und Vortragslogik gilt `docs/project_presentation_mp04.md`.
- Bei Aenderungen an Textkern, Bild-Hauptpfaden oder Ergebniswelt zuerst Tests, dann Stack-Status, dann Smoke- und UI-Smoke laufen lassen.
