# Historisches Dokument - Code KI V1

Dieses Dokument beschreibt ein frueheres Teilprojekt (`Code KI V1`) und nicht den aktiven Produktkern der heutigen `Local Image AI`.

Fuer den aktiven Produktkern gelten stattdessen:
- `README.md`
- `docs/product_core_mp01.md`

# Projektbeschreibung

## Ausgangsproblem

Online-KIs sind stark im Planen und Prompten, aber fuer lokales, kontrolliertes Python-Arbeiten in VS Code fehlt oft eine kleine eigene Loesung.

## Zielsetzung

Entwicklung einer lokal laufenden Python-KI fuer VS Code, die:
- Arbeitsanweisungen entgegennimmt
- relevanten Codekontext einbezieht
- nachvollziehbare Python-Unterstuetzung liefert

## Abgrenzung

V1 ist bewusst kein autonomer Vollagent.

Nicht Teil von V1:
- Multi-Datei-Autonomie
- Git-Automation
- automatische Testorchestrierung
- automatische Patch-Anwendung

## Verwendete Technologien

- Python 3.12
- FastAPI
- `llama-cpp-python`
- GGUF-Modell lokal
- VS-Code-Erweiterung in plain JavaScript

## Praktischer Nutzen

- enge Python-Arbeitsauftraege lokal ausfuehren
- aktuelle Datei und Auswahl direkt einbeziehen
- kontrollierte Hilfe statt chaotischer Agentik

## Grenzen

- Qualitaet haengt stark vom lokalen GGUF-Modell ab
- grosse Projekte werden in V1 nur begrenzt verstanden
- keine sichere Auto-Edit-Funktion

## Ausbau

- strukturierte Patch-Ausgabe
- Testintegration
- Projektweite Kontextsicht
- agentischere Folgeversionen
