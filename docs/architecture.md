# Historisches Dokument - Code KI V1

Dieses Dokument beschreibt ein frueheres Teilprojekt (`Code KI V1`) und nicht den aktiven Produktkern der heutigen `Local Image AI`.

Fuer den aktiven Produktkern gelten stattdessen:
- `README.md`
- `docs/product_core_mp01.md`

# Architektur V1

## Ziel

Eine lokale Python-KI fuer VS Code, die enge Arbeitsauftraege mit sichtbarem Codekontext verarbeitet.

## V1-Bausteine

1. VS-Code-Erweiterung
- nimmt Prompt und optionalen Traceback entgegen
- liest aktive Datei und Markierung
- sendet alles an das lokale Backend
- zeigt die Antwort kontrolliert an

2. Kontextsammler
- aktive Datei
- markierter Bereich
- Workspace-Pfad
- optionaler Fehlertext

3. Regel- und Prompt-Schicht
- klarer Python-Fokus
- konservative Regeln
- keine ungefragten Grossumbauten

4. Lokales Modellbackend
- FastAPI + `llama-cpp-python`
- GGUF-Modell lokal ueber Dateipfad
- localhost-Kommunikation

5. Ausgabeblock
- reine Ergebnisanzeige
- keine automatische Uebernahme

## Warum diese Architektur

- klein genug fuer ein Abschlussprojekt
- lokal und nachvollziehbar
- spaeter modular ausbaubar
- keine unnötige Fremdschicht wie Ollama im V1-Kern
