# StoryForge Local - Sichtpruefung Checkliste

## 1. Hauptarbeitsraum
- Startseite zeigt `StoryForge Local` und der Schreibbereich ist sichtbar.
- Aktive Szene ist im Szenenpanel klar erkennbar.
- Textkoerper ist editierbar und bleibt zentrales Arbeitsfeld.
- Textmodi (`Schreiben`, `Ueberarbeiten`, `Als Bildprompt umwandeln`) sind umschaltbar.

## 2. Diktatpfad
- Diktat-Schalter im Textbereich ist sichtbar.
- Ohne lokales STT-Backend: klare ruhige Meldung, keine kaputte UI.
- Mit lokalem STT-Backend: Aufnahme -> Transkript landet im Textkoerper.

## 3. Prompt-/Negativprompt-Fluss
- In Modus `Als Bildprompt umwandeln` wird der Prompt aus Text ableitbar.
- Negativprompt-Feld ist im Bildprompt-Modus sichtbar.
- Negativprompt-Hinweis bleibt kurz und verstaendlich (aktiv/optional).
- CTA zum Bildschritt erscheint erst bei vorhandenem Bildprompt.

## 4. Szenenbilder und Vorschau
- Szenenbilder der aktiven Szene sind im Szenenkontext sichtbar.
- Vorschau aus Szenenbildern oeffnet die bestehende Ergebnisansicht.
- `Als Ausgangsbild` funktioniert aus dem Szenenbild-Kontext.

## 5. Export und Wiederaufnahme
- Szenenexport erzeugt eine nutzbare Markdown-Datei (und JSON-Link, falls vorhanden).
- Exportstatus bleibt kurz und ohne Entwicklerjargon.
- Nach Reload wird aktive Szene wieder geladen.
- Nach Reload bleiben Szenenkontext und zugeordnete Bilder nachvollziehbar.

## 6. Zustandsqualitaet
- Leere Zustaende sind verstaendlich: keine Szene, keine Szenenbilder, kein Prompt.
- Disabled-Zustaende sind klar (z. B. Diktat/Export nur bei gueltigem Kontext).
- Fehlertexte sind kurz, ruhig, produktisch.
- Keine Statusflut und keine UI-Ueberladung im Hauptpfad.
