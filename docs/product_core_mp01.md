# Produktkern / Produktdoku

Stand: 2026-04-07

## Zweck dieses Dokuments

Dieses Dokument ist die kanonische Produktdoku fuer den aktiven Produktstand nach MP-04.

Es legt verbindlich fest:
- was das aktive Produkt ist
- welche Pfade produktiv sind
- welche Pfade experimentell bleiben
- welche Bereiche historisch oder Nebenbestand sind
- wie der Stack offiziell gestartet, geprueft und gestoppt wird
- welche produktiven Textmodi und Bildpfade zum Hauptprodukt gehoeren
- welche bekannten Produktgrenzen offen und ehrlich gelten

## Aktives Produkt

Das aktive Produkt ist eine lokale Windows-App fuer Text-KI und Bild-KI mit Browser-UI.

Aktive Hauptkomponenten:
- `web/index.html`
- `python/app_server.py`
- `python/text_service.py`
- `scripts/run_stack.ps1`
- `config/text_service.json`
- `python/` als aktiver Produktcode
- `web/` als aktive Produkt-UI
- `tests/` als aktive lokale Absicherung

Lokale Laufzeitdienste:
- Haupt-App auf `127.0.0.1:8090`
- Text-Service auf `127.0.0.1:8091`
- Text-Runner auf `127.0.0.1:8092`
- ComfyUI auf `127.0.0.1:8188`

## Produktive Hauptfunktionen

Text:
- `Text schreiben / Text-KI nutzen`
- gespeicherte Chats in `data/text_chats.sqlite3`
- Prompt-Hilfe / Prompt-Schreiben
- Uebersetzen / Umformulieren
- Prompt-Uebergabe in die Bild-KI

Bild:
- `Neues Bild erstellen`
- `Bild anpassen`
- `Bereich im Bild aendern`
- Ergebnisvorschau, Galerie, Download, Export, Wiederverwendung und Entfernen aus der Hauptliste

## Textmodi

- `Standard`
  - produktiver Default fuer normales Schreiben, mittlere Nutztexte und Prompt-Hilfe
  - praxisnah fuer grob `140-220` Woerter bei einem Ziel von `160-200`
- `Starkes Schreiben`
  - produktiver Langtextmodus fuer laengere Schreibaufgaben
  - lokal auf CPU deutlich langsamer, aber fuer grob `500-800` Woerter gedacht
- `Mehrsprachig`
  - produktiver Modus fuer Uebersetzen und Umformulieren mit klarer Zielsprache

## Sichtbare Bildpfade

- `Basismodus`
  - `Neues Bild erstellen`
  - `Bild anpassen`
  - `Bereich im Bild aendern`
- `Erweitert / Experimental`
  - `Neue Szene mit derselben Person`
  - Mehrbild-/Transfer-/Masken-Hybrid-Pfade
  - technische Readiness- und Teststarts

## Verbindliche Klassifikation

### Produktiv

Diese Pfade und Faehigkeiten gehoeren zum produktiven Hauptkern:

- `Text schreiben / Text-KI nutzen`
- lokale gespeicherte Chats
- Prompt-Hilfe / Prompt-Schreiben / Prompt-Uebergabe
- Uebersetzen / Umformulieren ueber die Text-Arbeitsmodi
- `Neues Bild erstellen`
- `Bild anpassen`
- `Bereich im Bild aendern`
- Ergebnisgalerie
- Ergebnisvorschau
- Download / Export / Wiederladen / Loeschen

Produktiv relevante Repo-Bereiche:
- `python/`
- `web/`
- `scripts/`
- `config/text_service.json`
- `config/app_config.json`
- `tests/`
- `docs/product_readiness_snapshot.md`

### Experimentell

Diese Pfade bleiben Bestandteil des aktiven Projekts, sind aber nicht als gleich stabiler Hauptpfad zu lesen:

- `Neue Szene mit derselben Person`
- `V6.1 Single-Reference`
- `V6.2 Multi-Reference`
- `V6.3 Identity Transfer`
- `V6.8 Masken-Hybrid`
- `identity_research`
- `scripts/run_identity_research_ab.py`
- `docs/identity_research_test_series_v1.json`
- Architektur- und Audit-Doku zu den experimentellen Bildpfaden unter `docs/v4_*`, `docs/v6_*`, `docs/v7_*`, `docs/v9_*`, `docs/v11_*`

Regel:
- experimentell bedeutet hier: aktiv vorhanden, bewusst erhalten, aber nicht als voll gleichwertiger Standard-Hauptpfad zu behandeln

### Historisch / Nebenbestand

Diese Bereiche verwischen nicht mehr den aktiven Produktpfad:

- `backend/`
- `vscode-extension/`
- `main.py`
- `stable-diffusion-webui/`
- `docs/architecture.md`
- `docs/project_documentation.md`

Regel:
- diese Bereiche bleiben erhalten, sind aber nicht der offizielle Produktkern

## Bekannte Produktgrenzen

- `Neue Szene mit derselben Person` bleibt experimentell und ist nicht als stabiler Produkt-Hauptpfad freigegeben.
- `Bereich im Bild aendern` ist brauchbar fuer kleinere lokale Aenderungen, aber nicht verlaesslich genug fuer groessere Kleidungs-/Formwechsel mit Form-Erhalt.
- `Starkes Schreiben` ist produktiv nutzbar, auf dem lokalen CPU-Stack aber deutlich langsamer als `Standard` und `Mehrsprachig`.
- Die produktive Bild- und Textnutzung ist lokal und damit von vorhandenen Modellen, lokalem Speicher und der Laufzeit des Zielrechners abhaengig.

## Offizieller Nutzpfad

### Hauptstart fuer normale Nutzung

1. `Start_Local_Image_AI.cmd`
2. Browser auf `http://127.0.0.1:8090`

### Technischer Hauptstart

1. `powershell -ExecutionPolicy Bypass -File .\scripts\run_stack.ps1 -Action start -UserMode`

### Offizieller Statuspfad

1. `Status_Local_Image_AI.cmd`
2. alternativ: `powershell -ExecutionPolicy Bypass -File .\scripts\run_stack.ps1 -Action status -UserMode`

### Offizieller Stop-Pfad

1. `Stop_Local_Image_AI.cmd`
2. alternativ: `powershell -ExecutionPolicy Bypass -File .\scripts\run_stack.ps1 -Action stop -UserMode`

## Offizieller Minimal-Abnahmepfad

Lokale Minimalfreigabe fuer den Produktkern:

1. `venv\Scripts\python.exe -m unittest discover -s tests`
2. `powershell -ExecutionPolicy Bypass -File .\scripts\run_stack.ps1 -Action start -UserMode`
3. `powershell -ExecutionPolicy Bypass -File .\scripts\run_stack.ps1 -Action status -UserMode`
4. `powershell -ExecutionPolicy Bypass -File .\scripts\smoke_test.ps1`
5. `powershell -ExecutionPolicy Bypass -File .\scripts\ui_smoke_test.ps1`
6. `GET /health`
7. `GET /identity-reference/readiness`
8. `GET /identity-transfer/readiness`

## Repo-Grenzen

Aktiver Produktcode:
- `python/`
- `web/`
- `scripts/`
- `config/`
- `tests/`
- relevante aktive Root-Startdateien (`Start_Local_Image_AI.cmd`, `Status_Local_Image_AI.cmd`, `Stop_Local_Image_AI.cmd`)

Lokale Laufzeit- und Arbeitsbestaende, nicht Teil des aktiven Produktcodes:
- `data/`
- `vendor/ComfyUI/`
- `vendor/text_runner/`
- `vendor/text_models/`
- `venv/`
- `local_backups/`
- `stable-diffusion-webui/`
- Log- und Statusdateien im Repo-Root

## Wichtige Hinweise fuer Uebergabe und Weiterarbeit

- Bestehende Faehigkeiten bleiben erhalten; MP-01 entfernt keine Kernfunktion.
- Experimentelle Pfade bleiben bestehen, werden aber bewusst nicht als gleichwertiger Standard-Hauptpfad beschrieben.
- Historische und Nebenbestaende bleiben im Repository, bestimmen aber nicht mehr das aktive Produktbild.
- Fuer den MP-04-Abschluss gelten zusaetzlich:
  - technische Uebergabe: `docs/technical_closeout_mp04.md`
  - Praesentation / Abgabe: `docs/project_presentation_mp04.md`
- Falls andere Dokumente diesem Bild widersprechen, gilt fuer den aktiven Produktkern dieses Dokument zusammen mit dem Root-`README.md`.
