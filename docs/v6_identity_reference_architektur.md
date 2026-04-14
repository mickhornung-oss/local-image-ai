# V6 Identity / Reference Architektur

## Ist-Zustand
- `python/app_server.py` orchestriert heute drei stabile Bildpfade gegen ComfyUI:
  - `txt2img`
  - `img2img` mit genau einem Source-Bild
  - `inpainting` mit genau einem Source-Bild plus genau einer Maske
- Source- und Maskenbilder liegen app-kontrolliert unter `data/input_images/` und `data/mask_images/`.
- `python/render_text2img.py` staged Source-/Mask-Dateien nach `vendor/ComfyUI/input/local-image-app/` und ruft einen klar getrennten SDXL-Workflow auf.
- Die UI kennt heute bereits:
  - Source-Upload / Clipboard
  - Masken-Upload / Browser-Maske
  - getrennte Modi fuer `txt2img`, `img2img`, `inpainting`

## Problemgrenze Heute
- `img2img` erhaelt grobe Bildmerkmale, driftet aber bei neuer Pose, anderem Koerper oder staerkerer Umkomposition sichtbar in Gesicht, Frisur und Identitaet.
- `inpainting` eignet sich fuer lokale Korrekturen, nicht fuer eine robuste Identitaetsuebertragung auf neue Pose oder neuen Koerper.
- Es gibt heute keinen expliziten Identity-Signalpfad:
  - keine Face-Embeddings
  - keine Referenzaggregation
  - keine posegefuehrte Identitaetssteuerung
- Fuer das V6-Ziel reicht der aktuelle Source-/Mask-Stand deshalb technisch nicht aus.

## Zusaetzliche Anforderungen Fuer V6
- Single-Reference:
  - eine Referenz derselben Person
  - neue Pose / neues Framing / neue Kleidung bei maximaler Aehnlichkeit
- Multi-Reference:
  - mehrere Bilder derselben Person gemeinsam nutzbar
  - Auswahl / Gewichtung / Aggregation statt blindem Durchreichen
- Kontrollierte Personenuebertragung:
  - Gesicht / Kopf einer Person auf neuen Koerper, neue Pose oder neue Szene
  - moeglichst wenig Drift in Augen, Gesichtsschnitt, Haarlinie, Hautbild
- Dafuer braucht V6 zusaetzlich zu V1-V3:
  - explizite Identity-Extraktion
  - pose- oder keypoint-basierte Steuerung
  - dedizierten Referenzpfad getrennt vom normalen `img2img`
  - spaeter optional Referenzranking / Referenzfusion

## Gepruefte Varianten

### A. Reiner ComfyUI-Workflow-Ausbau
- Idee:
  - nur neue ComfyUI-Custom-Nodes und ein zusaetzlicher Workflow
  - Referenzbilder direkt in ComfyUI laden
- Vorteil:
  - geringster Python-Backend-Eingriff
  - ComfyUI bleibt alleinige Identity-Engine
- Nachteil:
  - schwache Kontrolle ueber Referenzsammlung, Referenzqualitaet und spaetere Multi-Reference-Logik
  - hohes Knoten-/Datei-/Modell-Chaos im heute stabilen Bildpfad
  - Windows-/Dependency-Risiko steigt direkt im Kernpfad von ComfyUI
- Urteil:
  - fuer erste Experimente ok, als Zielarchitektur fuer dieses Repo zu unruhig

### B. Separater Identity-Adapter im Python-Backend plus generischer ComfyUI-Workflow
- Idee:
  - Backend uebernimmt Vorverarbeitung, Referenzverwaltung, evtl. Embeddings
  - ComfyUI bekommt nur bereits vorbereitete Inputs
- Vorteil:
  - gute Kontrolle ueber Referenzdaten und spaetere UX
  - klarere Trennung gegen den stabilen V1-V3-Hauptpfad
- Nachteil:
  - zu viel Intelligenz wuerde ins Backend wandern
  - Gefahr von doppelter Logik neben ComfyUI
  - hoeheres Implementierungsrisiko schon in V6.1
- Urteil:
  - als alleinige Richtung zu backend-lastig

### C. Hybrider Ansatz mit getrenntem V6-Pfad
- Idee:
  - dedizierter Identity-Adapter im Backend nur fuer:
    - Referenzvalidierung
    - spaetere Multi-Reference-Buendelung
    - deterministisches Staging
  - dedizierter ComfyUI-Identity-Workflow fuer die eigentliche Bilderzeugung
- Vorteil:
  - beste Trennung gegen den stabilen Hauptpfad
  - gute Erweiterbarkeit fuer Single-Reference, spaeter Multi-Reference und Pose-/Body-Transfer
  - Backend behaelt Referenzhoheit, ComfyUI bleibt Bild-Engine
  - Windows-tauglicher als ein grosser Mischpfad, weil neue Abhaengigkeiten nur den V6-Zweig betreffen
- Nachteil:
  - etwas mehr Integrationsarbeit als A
- Urteil:
  - beste Zielarchitektur

## Empfohlene Zielarchitektur
- V6 soll Variante C nutzen:
  - ein klar getrennter, opt-in Identity-/Reference-Pfad
  - separater Python-Identity-Adapter fuer Referenzverwaltung und Staging
  - separater dedizierter ComfyUI-Workflow fuer Identity-Generation
- Startpunkt fuer V6.1:
  - Single-Reference nur auf SDXL
  - ein dedizierter InstantID-artiger Workflow mit pose-/keypoint-faehigem Identity-Signal
  - kein Vermischen mit dem bestehenden `img2img`-Workflow
- Begruendung:
  - InstantID ist explizit fuer tuning-freie identity-preserving generation aus einem einzelnen Bild ausgelegt und koppelt Identity-Signal und ControlNet-basiertes Pose-Signal.
  - Reines `img2img` oder lokales Inpainting erreicht diese Trennung nicht.
  - IP-Adapter FaceID und PuLID bleiben technisch relevante Vergleichs-/Erweiterungsbausteine, sollten aber nicht gleichzeitig den ersten V6-Pfad aufblaehen.

## Ausbaupfad In Kleinen Bloecken

### V6.1 Single-Reference-Grundlage
- genau ein neuer, getrennter Identity-Pfad
- genau ein Referenzbild
- dedizierter Identity-Workflow
- kein Multi-Reference
- kein Body-Transfer-UI

### V6.2 Multi-Reference
- Referenzset derselben Person
- Backend waehlt/staged Referenzen kontrolliert
- ComfyUI-Workflow bekommt klar aggregierte Referenzeingaenge

### V6.3 Kontrollierte Pose-/Body-Transfer-Verbesserung
- zusaetzliche Pose-/Kompositionssteuerung
- gezielte lokale Nachkorrektur per Inpainting nur als zweiter Schritt
- kein unkontrolliertes Vermischen mit dem normalen Inpainting-Flow

## No-Gos
- Keine Identity-Logik direkt in den bestehenden `txt2img`-/`img2img`-/`inpainting`-Pfad einweben.
- Kein gleichzeitiges Einfuehren mehrerer Identity-Methoden im ersten V6-Schnitt.
- Keine UI mit vielen Gewichten, Slidern und Mehrdeutigkeiten im ersten Block.
- Keine versteckte Umbenennung von `img2img` zu "Identity", obwohl technisch nur Drift-reiches Source-Conditioning laeuft.
- Keine ungetestete Multi-Reference-Fusion im Hauptpfad.
- Keine automatische Modell-/Node-Downloads im spaeteren V6.1-Startblock.
- Lizenz-/Nutzungspruefung fuer InsightFace-bezogene Assets nicht ueberspringen.

## V6.1 Realer Startstand

### Lokal Vorhanden
- ein funktionierender SDXL-Basis-Checkpoint:
  - `vendor/ComfyUI/models/checkpoints/sdxl-base.safetensors`
- stabiler Source-/Mask-/Result-Store im Python-Backend
- stabiler SDXL-Hauptpfad mit getrennten Workflows fuer:
  - `txt2img`
  - `img2img`
  - `inpainting`
- kontrolliertes Staging von Eingabebildern nach `vendor/ComfyUI/input/local-image-app/`
- `vendor/ComfyUI/custom_nodes/ComfyUI_InstantID`
  - lokal bereitgestellt
  - wird von ComfyUI real erkannt (`/object_info`)
- Runtime-Unterbau im ComfyUI-venv:
  - `onnxruntime 1.23.2`
  - `opencv-python-headless 4.13.0.92`
  - `insightface 0.7.3`
  - Python `3.10.11` in `vendor/ComfyUI/venv`
  - MSVC-Build-Kontext real nachgewiesen ueber `VsDevCmd.bat`
    - `cl.exe`: `VC\\Tools\\MSVC\\14.44.35207\\bin\\Hostx64\\x64\\cl.exe`
    - Compiler: `Microsoft (R) C/C++ Optimizing Compiler Version 19.44.35224 for x64`
  - fuer den erfolgreichen Build war der Windows-Python-SDK-Kontext noetig:
    - `DISTUTILS_USE_SDK=1`
    - `MSSdk=1`
- Minimalmodelle lokal bereitgestellt:
  - `vendor/ComfyUI/models/insightface/models/antelopev2/*`
  - `vendor/ComfyUI/models/instantid/ip-adapter.bin`
  - `vendor/ComfyUI/models/controlnet/instantid/diffusion_pytorch_model.safetensors`
- dedizierte V6.1-Workflow-Vorlage vorhanden:
  - `python/workflows/v6_1_instantid_single_reference_api.json`
- enger separater V6.1-Smoke real gruen:
  - Referenzbild aus `data/input_images/`
  - ComfyUI-Completion ueber dedizierten InstantID-Workflow
  - ComfyUI-Output: `vendor/ComfyUI/output/v6_1_instantid_20260311204310_00001_.png`
  - app-kontrollierter Ergebnisstore: `result-20260311204530-d842ac79`

### Lokal Fehlend
- kein weiterer zwingender Runtime-Baustein fuer den engen V6.1-Single-Reference-Smoke
- optional spaeter fehlend:
  - expliziter Pose-Eingang fuer staerkere Kompositionskontrolle
  - eigene Backend-Schnittstelle fuer einen produktiven, getrennten V6.1-Generate-Pfad

### Optional Spaeter, Aber Aktuell Nicht Kritisch
- ein separates Pose-Bild kann spaeter als V6.1-Zusatzeingang sinnvoll sein
- fuer den ersten echten Start ist das kein Blocker mehr
- der naechste sinnvolle Schritt ist jetzt Stabilisierung des getrennten V6.1-Pfads, nicht weiterer Runtime-Unterbau

### Konsequenz Fuer Diesen Stand
- Der lokale Stack ist jetzt ehrlich `bereit fuer V6.1-Smoke`.
- Real erreicht:
  - Node-Erkennung in ComfyUI
  - Modelldateien an den erwarteten Stellen
  - getrennte Workflow-Vorlage fuer den V6.1-Single-Reference-Pfad
- funktionierende `insightface 0.7.3`-Runtime fuer `FaceAnalysis(name=\"antelopev2\", providers=[...])`
- enger separater Single-Reference-Smoke bis Completion
- app-kontrollierte Ergebnisablage fuer den Smoke
- Weiterhin bewusst nicht angelegt:
  - keine Vermischung mit dem bestehenden `img2img`-Pfad
  - keine UI-Integration fuer V6.1

## V6.1 Minimal Stabilisiert
- separater Backend-Pfad vorhanden:
  - `POST /identity-reference/generate`
  - `GET /identity-reference/readiness`
- der Readiness-Pfad prueft jetzt nur lesend:
  - Workflow-Datei vorhanden und parsebar
  - Minimalmodelle vorhanden
  - `insightface`-Runtime in der ComfyUI-venv inkl. Version und `FaceAnalysis(name='antelopev2', ...)`
  - InstantID-Nodes in ComfyUI `/object_info`
- keine Fallbacks auf `txt2img` oder `img2img`
- Fehlerfaelle sind strukturiert und nicht-destruktiv pruefbar:
  - fehlende Referenz -> `missing_reference_image`
  - fehlender Workflow -> `identity_workflow_missing`
  - fehlende Identity-Modelle -> `identity_models_missing`
- destruktive Live-Negativtests wie Node-/Modell-Entfernung sind bewusst nicht Teil des Standardlaufs
- V6.1 ist jetzt real wiederholbar:
  - `result-20260311214135-7c0ff910`
  - `result-20260311214223-7bc2e4f3`
  - beide im app-kontrollierten Ergebnisstore mit `mode=identity_reference` und `checkpoint=sdxl-base.safetensors`

## V6.2 Multi-Reference Architektur

### Ausgangspunkt V6.1
- V6.1 hat heute:
  - genau ein Referenzbild
  - einen getrennten InstantID-Pfad
  - stabile Readiness-Pruefung
  - getrennte Ergebnisablage mit `mode=identity_reference`
- Reale Grenze von V6.1:
  - Identitaetsstabilitaet haengt stark an genau einem Bild
  - schwankt sichtbar bei stark anderem Winkel, Ausdruck, Licht oder teilweiser Verdeckung
  - feine stabile Merkmale wie Haaransatz, Augenpartie und Gesichtsbreite driften schneller als gewuenscht

### Ziel Von V6.2
- mehrere Referenzbilder derselben Person gemeinsam nutzbar machen
- robustere Identitaet unter neuer Pose, Perspektive und Variation
- geringere Drift bei Details, die in einem einzelnen Referenzbild nur unvollstaendig sichtbar sind
- klar abgegrenzt gegen V6.3:
  - V6.2 ist kein Kopf-auf-fremden-Koerper-Ausbau
  - V6.2 ist keine grosse Pose-/Body-Transfer-Optimierung
  - V6.2 bleibt bei Multi-Reference fuer dieselbe Person

### Gepruefte Varianten

#### A. Mehrere Referenzbilder vor einem einzelnen Identity-Workflow aggregieren
- Idee:
  - Referenzbilder vorab zu einem einzigen Sammelartefakt oder Auswahlbild verdichten
  - danach weiter fast wie V6.1 laufen
- Vorteil:
  - kleinster Eingriff in den Workflow
  - niedrigstes ComfyUI-Risiko
- Nachteil:
  - zu viel Informationsverlust vor dem eigentlichen Identity-Pfad
  - schlechte Nachvollziehbarkeit, welches Referenzbild welchen Effekt hatte
  - begrenztes Potenzial fuer spaetere Qualitaetssteuerung
- Urteil:
  - als schnelle Behelfsidee ok, als Zielarchitektur zu schwach

#### B. Python-seitiger Multi-Reference-Adapter plus dedizierter ComfyUI-Workflow
- Idee:
  - Backend verwaltet mehrere Referenzen derselben Person getrennt
  - Adapter prueft, normiert, priorisiert und staged genau das Multi-Reference-Set fuer einen dedizierten Workflow
  - ComfyUI bleibt die eigentliche Bild-Engine
- Vorteil:
  - beste Kontrolle ueber Referenzqualitaet und spaetere Referenzauswahl
  - sauber getrennt von V6.1 und vom Hauptpfad
  - spaeter gut erweiterbar fuer Gewichtung oder Referenzranking, ohne den Workflow zu verchaotisieren
- Nachteil:
  - etwas mehr Adapterlogik als V6.1
  - eigener dedizierter Multi-Reference-Workflow noetig
- Urteil:
  - beste Zielrichtung fuer dieses Repo

#### C. Mehrere parallele Identity-Conditionings direkt im Workflow
- Idee:
  - mehrere Referenzen direkt in ComfyUI parallel einspeisen und dort kombinieren
- Vorteil:
  - maximale Kontrolle direkt im Workflow
  - wenig Python-seitige Vorlogik
- Nachteil:
  - hoechstes Integrations- und Wartungsrisiko
  - Workflow wird schnell unruhig und schwer debugbar
  - lokaler Windows-Betrieb wird fragiler, wenn mehrere Conditioning-Pfade gleichzeitig haengen
- Urteil:
  - fuer spaetere Spezialfaelle denkbar, fuer V6.2 als erster Ausbau zu riskant

### Empfohlene Richtung Fuer V6.2
- V6.2 soll Variante B nutzen:
  - separater Multi-Reference-Adapter im Python-Backend
  - dedizierter Multi-Reference-ComfyUI-Workflow
  - weiterhin klar getrennt von `txt2img`, `img2img`, `inpainting` und V6.1
- Begruendung:
  - beste Balance aus Identitaetstreue, Wartbarkeit und Konfliktfreiheit zum stabilen Stand
  - Referenzen koennen sauber gesammelt, validiert und spaeter sinnvoll priorisiert werden
  - ComfyUI bleibt weiter Bild-Engine statt Referenzdatenbank

### Kleiner Ausbaupfad
- V6.2.1:
  - mehrere Referenzbilder derselben Person getrennt annehmen und speichern
  - noch ohne neue Nutzerlogik im Hauptpfad
- V6.2.2:
  - dedizierten Multi-Reference-Adapter bauen
  - Referenzen normieren, qualitaetsseitig grob pruefen und deterministisch in den Workflow stagen
- V6.2.3:
  - separaten Multi-Reference-Smoke auf dem neuen Pfad fahren
  - Ergebnisstore weiter mit eigenem `mode`/Metadaten fuehren

### Zusaetzliche Readiness-Frage Gegenueber V6.1
- neue Nodes/Modelle:
  - fuer einen ersten ehrlichen V6.2-Start voraussichtlich nicht zwingend, solange der bestehende InstantID-/insightface-Stack weiterverwendet wird
  - spaeter moeglich, aber nicht Teil des minimalen V6.2-Starts
- neue Workflow-Komplexitaet:
  - ja, zwingend
  - ein eigener Multi-Reference-Workflow ist noetig
- zusaetzlicher Preprocessing-Schritt:
  - ja, sinnvoll und fuer die bevorzugte Richtung zentral
  - Referenzen muessen vor dem Workflow mindestens validiert, geordnet und deterministisch gestaged werden

### Bewusst Noch Nicht Teil Von V6.2
- echter Kopf-auf-fremden-Koerper-Ausbau
- weitergehende Pose-/Body-Transfer-Optimierung
- parallele Identity-Frameworks neben InstantID
- UI mit Gewichten, Referenzranking oder manueller Referenzmischung
- automatische Modell-/Node-Beschaffung

## V6.2.1 Multi-Reference-Grundlage
- jetzt vorhanden:
  - separater Store unter `data/multi_reference_images/`
  - maximal 3 Referenzslots
  - stabiler Slot-Status mit `reference_count` und `multi_reference_ready`
  - gezieltes Befuellen von Slot 1/2/3 oder Auto auf ersten freien Slot
  - Reset pro Slot und kompletter Reset
- bewusst noch nicht vorhanden:
  - kein Multi-Reference-Generate
  - kein dedizierter Multi-Reference-Workflow-Lauf
  - keine Vermischung mit V6.1-Single-Reference oder dem Hauptpfad
- Konsequenz:
  - V6.2.1 stellt nur den getrennten Referenzbestand bereit
  - der naechste enge Schritt bleibt ein Python-seitiger Multi-Reference-Adapter vor jedem echten Workflow-Lauf

## V6.2.2 Multi-Reference-Adapter
- jetzt vorhanden:
  - separater Python-Adapter fuer den V6.2-Bestand
  - geordnete Referenzsammlung strikt nach Slot `1..3`
  - `primary_reference` stabil:
    - Slot `1`, wenn belegt
    - sonst die erste vorhandene Referenz
  - read-only Adapter-Readiness unter `GET /identity-multi-reference/readiness`
  - vorbereiteter Staging-Schnitt fuer V6.2.3:
    - `target_subfolder = identity_multi_reference`
    - stabile Zielnamen pro Slot
- Fehlerbild jetzt strukturiert:
  - `insufficient_multi_reference_images`
  - `missing_multi_reference_file`
  - `invalid_multi_reference_metadata`
  - `invalid_multi_reference_image`
  - `duplicate_multi_reference_slot`
- bewusst noch nicht vorhanden:
  - kein Multi-Reference-Generate
  - kein dedizierter Multi-Reference-Workflow-Run
  - keine Vermischung mit V6.1-Single-Reference oder dem Hauptpfad
- Konsequenz:
  - V6.2.2 liefert jetzt die saubere Python-seitige Uebergabestruktur fuer V6.2.3
  - der naechste enge Schritt ist erst der getrennte echte Multi-Reference-Smoke

## V6.2.3 Erster Echter Multi-Reference-Smoke
- lokal ehrlich moeglich:
  - ja
  - ueber einen getrennten dedizierten InstantID-Workflow mit realem Mehrfach-Referenzpfad
- wie mehrere Referenzen real verwendet werden:
  - die geordneten Referenzen aus V6.2.2 gehen als echter `IMAGE`-Batch in den dedizierten Workflow
  - `ImageBatch` fuehrt Slot `1..N` deterministisch zusammen
  - `ApplyInstantID` verarbeitet diesen Batch direkt
  - der lokale InstantID-Node mittelt die Face-Embeddings des Batches real (`average`)
  - die primaere Referenz bleibt das erste geordnete Bild und liefert explizit `image_kps`
- jetzt vorhanden:
  - separater Runner fuer `identity_multi_reference`
  - separater Endpunkt `POST /identity-multi-reference/generate`
  - dedizierter Workflow `python/workflows/v6_2_instantid_multi_reference_api.json`
  - Ergebnisstore mit sauber getrenntem `mode=identity_multi_reference`
  - Metadaten fuer:
    - `reference_count`
    - `reference_slots`
    - `reference_image_ids`
    - `multi_reference_strategy=instantid_image_batch_average`
- real bestaetigt:
  - erster enger Multi-Reference-Smoke bis Completion gruen
  - Ergebnis im app-kontrollierten Ergebnisstore vorhanden
- bewusst noch nicht gemacht:
  - kein Multi-Reference-UI-Ausbau
  - keine parallelen Identity-Zweige
  - kein V6.3-Transferpfad

## V6.2 Stabilisierung
- V6.2 ist jetzt klein und real wiederholbar:
  - Lauf mit `3` Referenzen bis Completion gruen
  - Lauf mit `2` Referenzen bis Completion gruen
- zentrale nicht-destruktive Readiness ist jetzt schaerfer:
  - mindestens `2` Referenzen vorhanden
  - Multi-Reference-Adapter ready
  - dedizierter Workflow vorhanden
  - InstantID-Nodes sichtbar
  - benoetigte Modelle vorhanden
  - `insightface`-Runtime brauchbar
- Ergebnisstore/Metadaten sind stabil getrennt:
  - `mode=identity_multi_reference`
  - `reference_count`
  - `reference_slots`
  - `reference_image_ids`
  - `multi_reference_strategy=instantid_image_batch_average`
- Fehlerfaelle sind strukturiert und nicht-destruktiv pruefbar:
  - nur `1` Referenz -> `insufficient_multi_reference_images`
  - fehlender Workflow -> `identity_workflow_missing`
  - fehlende Identity-Modelle -> `identity_models_missing`
- destruktive Live-Negativtests wie Node-/Modell-Entfernung sind bewusst nicht Teil des Standardlaufs

## V6.3 Kontrollierte Personenuebertragung

### Ausgangspunkt V6.1 und V6.2
- V6.1 liefert heute:
  - hohe Identitaetstreue aus genau einer Referenz
  - getrennten Single-Reference-Identity-Pfad
- V6.2 liefert heute:
  - mehrere Referenzen derselben Person
  - robustere Identitaetsstabilitaet ueber den getrennten Multi-Reference-Pfad
- reale Grenze beider Pfade:
  - noch kein gezielter Kopf-/Gesicht-auf-neuen-Koerper- oder neue-Pose-Stack
  - Hals-, Schulter-, Perspektiv- und Lichtuebergaenge sind noch nicht als eigener Transferpfad geloest
  - vorhandenes `inpainting` hilft lokal punktuell, ist aber noch kein kontrollierter Personenuebertragungs-Workflow

### Ziel Von V6.3
- gleiche Person kontrolliert auf:
  - anderen Koerper
  - andere Pose
  - neue Komposition
- dabei:
  - hohe Identitaetstreue im Gesicht/Kopf
  - moeglichst saubere Uebergaenge an Hals, Haarlinie, Schultern und Lichtkante
  - kontrollierte Pose-/Kompositionsfuehrung
- bewusst noch nicht Teil von V6.3:
  - spaetere Qualitaetsstufe mit feiner manueller Retusche
  - automatische perfekte Body-Integration fuer alle Extremfaelle
  - V7-Themen wie vollwertiger Editor oder komplexe Guided-UX

### Gepruefte Varianten

#### A. Identity-Referenz plus Pose-Control plus Inpainting in getrenntem Hybridpfad
- Idee:
  - Identity-Referenz erzeugt die Person
  - Pose-/Control-Schritt fuehrt Koerperhaltung und Komposition
  - Inpainting/Maske stabilisiert Kopf-Hals-Uebergaenge lokal
- Vorteil:
  - beste Trennung der Teilprobleme
  - vorhandene Staerken aus V2/V3/V6.1/V6.2 bleiben nutzbar
  - gute Chance auf sauberere Uebergaenge als mit reinem Identity-Prompting
- Nachteil:
  - eigener Hybrid-Workflow und klarer Rollenadapter noetig
  - etwas hoehere Workflow-Komplexitaet
- Urteil:
  - beste Zielrichtung fuer dieses Repo

#### B. Reiner Identity-Workflow mit staerkerem Prompt-/Masken-/Pose-Conditioning
- Idee:
  - alles in einem staerkeren Identity-Workflow halten
  - Prompt, Pose und optionale Maske direkt zusammen in einem Pfad erzwingen
- Vorteil:
  - nur ein Workflow-Pfad
  - wenig Python-seitige Vorlogik
- Nachteil:
  - hohes Risiko fuer unruhige Ergebnisse und schwer debugbare Uebergaenge
  - schlechtere Trennung zwischen Identitaetsproblem und Compositing-/Inpainting-Problem
- Urteil:
  - fuer erste V6.3-Ausbaustufe zu fragil

#### C. Python-seitiger Vorbereitungsadapter plus dedizierter ComfyUI-Composite-/Transfer-Workflow
- Idee:
  - Python bereitet Rollen und Staging vor
  - ComfyUI bekommt danach einen dedizierten Transfer-/Composite-Workflow
- Vorteil:
  - klare Rollenaufteilung
  - spaeter gut fuehrbar fuer Zielkoerper, optionale Pose und optionale Maske
- Nachteil:
  - ohne expliziten Hybrid aus Pose-Control und Inpainting bleibt die Uebergangsqualitaet zu schwach
  - als alleinige Richtung zu abstrakt und zu nah an halbfertigen Face-Swap-Basteleien
- Urteil:
  - sinnvoll als Baustein, aber nicht als alleinige Zielarchitektur

### Empfohlene Richtung Fuer V6.3
- V6.3 soll Variante A mit C als technischem Unterbau nutzen:
  - separater Python-Transfer-Adapter fuer Rollen/Staging
  - getrennter ComfyUI-Hybridpfad aus:
    - Identity-Referenz
    - Pose-/Control-Fuehrung
    - lokalem Inpainting fuer Uebergaenge
- Begruendung:
  - beste Balance aus Identitaetstreue, Uebergangsqualitaet und Wartbarkeit
  - vorhandene stabile Pfade koennen weiter getrennt bleiben
  - geringstes Konfliktrisiko fuer V6.1/V6.2 und den Hauptpfad

### Kleiner Ausbaupfad
- V6.3.1:
  - Input-/Rollenmodell festlegen:
    - Kopf-/Gesichtsreferenz
    - Zielkoerperbild
    - optionale Pose
    - optionale Maske fuer Uebergangsbereich
- V6.3.2:
  - dedizierten Python-Transfer-Adapter bauen
  - Rollen validieren, normieren und deterministisch stagen
- V6.3.3:
  - separaten Hybrid-Workflow-Smoke fahren
  - Ergebnisstore mit eigenem `mode` sauber getrennt fuehren

### V6.3.1 Status
- Stand:
  - vorhanden als getrenntes Input-/Rollenmodell ohne Generate-Pfad
- Pflichtrollen:
  - `identity_head_reference`
  - `target_body_image`
- Optionalrollen:
  - `pose_reference`
  - `transfer_mask`
- Verhalten:
  - pro Rolle genau ein aktuelles Bild
  - Einzel-Reset pro Rolle und kompletter Reset vorhanden
  - `v6_3_transfer_ready=true` nur bei belegter Kopf-/Gesichtsreferenz plus Zielkoerperbild
- Bewusst noch nicht enthalten:
  - kein Transfer-Generate
  - kein dedizierter V6.3-Workflow-Run
  - keine Vermischung mit normalem Source-/Mask-State, V6.1 oder V6.2

### V6.3.2 Status
- Stand:
  - dedizierter Python-Transfer-Adapter ist vorhanden
  - read-only Adapter-Readiness unter `GET /identity-transfer/readiness`
- Adapter-Vertrag:
  - Pflichtrollen:
    - `identity_head_reference`
    - `target_body_image`
  - Optionalrollen:
    - `pose_reference`
    - `transfer_mask`
  - Ausgabe:
    - `ready`
    - `roles`
    - `required_roles_present`
    - `optional_roles_present`
    - `ordered_roles`
    - `staging_plan`
- Verhalten:
  - `ready=true` nur bei vorhandener Kopf-/Gesichtsreferenz plus Zielkoerperbild
  - optionale Pose und optionale Maske erweitern nur die Readiness-Struktur
  - strukturierte Fehler fuer fehlende Pflichtrollen, fehlende Dateien, inkonsistente Metadaten und ungueltige Bilder
- Bewusst noch nicht enthalten:
  - kein Transfer-Generate
  - kein Live-Workflow-Run
  - keine Vermischung mit V6.1, V6.2 oder dem normalen Bild-Flow

### V6.3.3 Status
- Stand:
  - erster separater Hybrid-Smoke ist lokal real gruen
  - dedizierter Endpunkt: `POST /identity-transfer/generate`
  - dedizierter Workflow: `v6_3_identity_transfer_api.json`
- Ehrlich genutzter Hybridweg:
  - `identity_head_reference` geht ueber InstantID ein
  - `target_body_image` geht als echtes Init-Latent ueber `LoadImage -> VAEEncode -> KSampler` ein
  - Strategie: `instantid_target_body_init_image`
- Im ersten Smoke bewusst noch nicht genutzt:
  - `pose_reference`
  - `transfer_mask`
  - Grund: kein halbfertiger Scheinpfad ohne echte Control-/Inpaint-Verkettung
- Ergebnis:
  - separater Ergebnisstore-Eintrag mit `mode=identity_transfer`
  - Metadaten halten verwendete Rollen plus `pose_reference_used=false` und `transfer_mask_used=false`

## V6.3 Minimal Stabilisiert
- V6.3 ist jetzt klein und real wiederholbar:
  - Pflichtrollen-only-Lauf bis Completion gruen
  - zweiter Lauf mit vorhandener optionaler Pose und vorhandener Transfer-Maske bis Completion gruen
- zentrale nicht-destruktive Readiness ist jetzt schaerfer:
  - `identity_head_reference` vorhanden
  - `target_body_image` vorhanden
  - V6.3.2-Adapter ready
  - dedizierter Workflow vorhanden
  - InstantID-Nodes sichtbar
  - benoetigte Modelle vorhanden
  - `insightface`-Runtime brauchbar
  - optionale Rollen getrennt sichtbar:
    - `pose_reference` vorhanden ja/nein
    - `transfer_mask` vorhanden ja/nein
- Ergebnisstore/Metadaten sind stabil getrennt:
  - `mode=identity_transfer`
  - `used_roles`
  - `pose_reference_used`
  - `transfer_mask_used`
  - `identity_transfer_strategy=instantid_target_body_init_image`
  - `identity_head_reference_image_id`
  - `target_body_image_id`
  - optional `pose_reference_image_id`
  - optional `transfer_mask_image_id`
- Stabiler real genutzter Rollenstand heute:
  - aktiv genutzt:
    - `identity_head_reference`
    - `target_body_image`
  - nur praesent, aber bewusst noch nicht im stabilen Hybridpfad genutzt:
    - `pose_reference`
    - `transfer_mask`
- Fehlerfaelle sind strukturiert und nicht-destruktiv pruefbar:
  - fehlende Kopf-Referenz -> `missing_identity_head_reference`
  - fehlendes Zielkoerperbild -> `missing_target_body_image`
  - fehlender Workflow -> `identity_workflow_missing`
  - fehlende Identity-Bausteine -> `identity_models_missing` oder `identity_nodes_missing`
- destruktive Live-Negativtests wie Node-/Modell-Entfernung sind bewusst nicht Teil des Standardlaufs

### Readiness/Gaps Gegenueber V6.1 und V6.2
- neue Workflow-Komplexitaet:
  - ja, klar hoeher als V6.1/V6.2
  - separater Hybrid-Workflow ist noetig
- zusaetzlicher Pose-/Control-Schritt:
  - ja, fuer V6.3 sinnvoll bis wahrscheinlich zwingend
- sinnvoller Masken-/Inpainting-Einsatz:
  - ja, besonders fuer Hals-, Schulter- und Haarlinien-Uebergaenge
- eventuelle weitere lokale Bausteine:
  - moeglich, aber vor V6.3.1 noch bewusst offen
  - aktuell nichts installieren oder herunterladen

### No-Gos Fuer V6.3
- keine Vermischung in den stabilen Standard-Generate-Pfad
- keine halbfertigen Face-Swap-Sonderwege ohne klaren Rollenadapter
- keine Prompt-only-Scheinloesung fuer Koerpertransfer
- keine UI, die Zielkoerper, Pose und Maske chaotisch in denselben Block wirft
- keine automatische Modell-/Node-Beschaffung im Hauptpfad

## V6.3 Qualitaetsblocker Isoliert
- reproduzierbarer Minimalfall:
  - dieselbe Kopf-Referenz
  - dasselbe Zielbild
  - derselbe Prompt
  - `seed=123456789`
  - `1024x1024`
  - `steps=20`
  - `cfg=6.5`
  - optionale Pose/Maske nicht aktiv genutzt
- hartes Fehlerbild vor dem Fix:
  - Run ging technisch bis Completion
  - Ergebnis war kein "nur schwaches" Transferbild, sondern RGB-Rauschen / Farbzerfall
- eng gepruefte Hauptverdachte:
  - Zielbild-Init-Latent
  - `ApplyInstantID`-Gewichtung
  - Sampler-/Scheduler-Pfad
- klare Isolationskette:
  - V6.3 mit `ddpm + karras` -> kaputtes Noise-Bild
  - nur geringeres `ApplyInstantID.weight` -> weiter kaputtes Noise-Bild
  - nur `euler + normal` bei sonst gleichem V6.3-Pfad -> wieder plausibles Transferbild
- Hauptursache:
  - die Sampler-/Scheduler-Kombination im V6.3-Init-Latent-Pfad
  - konkret: `ddpm + karras` war der reproduzierte Qualitaetskiller
- minimaler Fix:
  - `python/workflows/v6_3_identity_transfer_api.json`
  - `sampler_name: ddpm -> euler`
  - `scheduler: karras -> normal`
- Stand nach dem Fix:
  - der kaputte Noise-/Farbzerfall-Zustand ist auf dem realen Produktpfad beseitigt
  - der Transfer bleibt noch weich und nicht auf Endqualitaet
  - der Pfad ist aber wieder ehrlich brauchbar statt visuell zerfallen
- reale Produktlaeufe nach dem Fix:
  - `result-20260315182157-abae6f36` mit `sdxl-base.safetensors`
  - `result-20260315182421-cbce6e93` mit `photo_standard`

## V6.3 Nach Dem Fix Erneut Verifiziert
- verifizierter Satz auf demselben stabilen Rollenstand:
  - `identity_head_reference=identity_head_reference-20260315175232-f1cd4086`
  - `target_body_image=target_body_image-20260315171559-9889f953`
  - `pose_reference_used=false`
  - `transfer_mask_used=false`
- reale Verifikationslaeufe:
  - `sdxl-base.safetensors`, `seed=123456789`, Standardprompt
  - `photo_standard`, `seed=123456789`, Standardprompt
  - `sdxl-base.safetensors`, `seed=123456790`, leicht variierter Prompt
- Ergebnislage:
  - kein erneuter RGB-Rausch-/Farbzerfall
  - kein kompletter Workflow-Zerfall
  - Gesicht/Kopf bleiben in allen drei Laeufen plausibel erkennbar
  - `photo_standard` wirkt im aktuellen stabilen Stand etwas klarer als `sdxl-base.safetensors`
- ehrliche Einordnung:
  - V6.3 ist nach dem Sampler-/Scheduler-Fix stabil brauchbar
  - der Pfad bleibt noch weich und nicht auf Endqualitaet
  - Pose und Transfer-Maske sind im stabilen Pfad weiter nur praesent, aber nicht aktiv als Qualitaetshebel genutzt

## V6.4 Qualitaetsblock Fuer Den Stabilen V6.3-Pfad
- Qualitaetsziel:
  - weniger Weichzeichnung
  - klarere Gesichtszuege
  - plausiblerer Transfer bei unveraenderter Stabilitaet
- eng gepruefte Hebel auf demselben festen Foto-Fall:
  - `steps: 20 -> 28`
  - `cfg: 6.5 -> 7.0`
  - `ApplyInstantID.weight: 0.8 -> 0.65`
- Ergebnis der isolierten Tests:
  - mehr Schritte brachten im engen Bereich keinen sichtbaren Qualitaetsgewinn
  - hoeheres CFG brachte im engen Bereich keinen sichtbaren Qualitaetsgewinn
  - geringere Identity-Gewichtung auf `0.65` brachte sichtbar mehr Klarheit und weniger Weichheit, ohne den Pfad wieder zu destabilisieren
- neuer stabiler Qualitaetsstand:
  - `python/workflows/v6_3_identity_transfer_api.json`
  - `ApplyInstantID.weight = 0.65`
  - `sampler_name = euler`
  - `scheduler = normal`
- reale Verifikation nach dem Qualitaetsfix:
  - `sdxl-base.safetensors`, `seed=123456789`
  - `photo_standard`, `seed=123456789`
  - `sdxl-base.safetensors`, `seed=123456790` mit leicht variiertem Prompt
- ehrliche Einordnung:
  - V6.3 ist damit sichtbar angezogen und bleibt stabil
  - `photo_standard` wirkt im aktuellen V6.3-Pfad klarer als `sdxl-base.safetensors`
  - trotzdem bleibt der Pfad noch weich im Vergleich zu einem spaeteren echten Pose-/Masken-Ausbau

## V6.5 Pose-/Masken-Nutzung Im Stabilen V6.3-Pfad
- Ausgangszustand vor diesem Schritt:
  - `pose_reference` und `transfer_mask` waren im Rollenstore und in der UI bereits vorhanden
  - im stabilen Renderpfad wurden beide aber noch nicht aktiv als Qualitaetshebel genutzt
- eng gepruefte Aktivierung:
  - Pose zuerst isoliert ueber `ApplyInstantID.image_kps`
  - Transfer-Maske danach separat in zwei minimalen Varianten:
    - maskierter Inpaint-Latent-Pfad
    - direkte `ApplyInstantID.mask`-Anbindung
- Ergebnis Pose:
  - `pose_reference` ist jetzt im bestehenden V6.3-Pfad aktiv nutzbar
  - Produktlauf nach sauberem App-Neustart:
    - `result-20260315223855-8e0efdb2`
    - `used_roles=["identity_head_reference","target_body_image","pose_reference"]`
    - `pose_reference_used=true`
    - `transfer_mask_used=false`
  - die Pose beeinflusst die Kopf-/Haltungsrichtung plausibel, ohne den stabilen Transferpfad zu zerstoeren
- Ergebnis Transfer-Maske:
  - im aktuellen stabilen V6.3-Pfad noch nicht ehrlich nutzbar
  - beide minimalen Aktivierungsvarianten fuehrten weiter zu unbrauchbaren Artefakten:
    - graue Silhouetten / harte Maskenfehler im Inpaint-Latent-Zweig
    - sichtbare Artefakt-/Lochbildung bei direkter `ApplyInstantID.mask`-Nutzung
- neuer ehrlicher Stand:
  - Pose: aktiv und stabil nutzbar
  - Transfer-Maske: weiter praesent im Store/UI, aber im stabilen Pfad noch bewusst nicht aktiviert
  - damit bleibt V6.3 stabil, ohne eine unehrliche Masken-Freigabe zu behaupten

## V6.6 Transfer-Masken-Blocker Im Stabilen V6.3-Pfad
- Ist-Zustand zu Beginn:
  - `transfer_mask` ist im Rollenstore und in der UI sauber vorhanden
  - im stabilen Codepfad wird sie aber weiterhin bewusst nicht angeschlossen:
    - `transfer_mask_used = false`
    - `ApplyInstantID.mask` wird aktiv entfernt
    - der Latent-Pfad bleibt bei `LoadImage -> VAEEncode`
- fester Referenzfall fuer die Isolation:
  - dieselbe Kopf-Referenz
  - ein menschlicher Zielkoerper aus `result-20260323084219-4e40db90.png`
  - `prompt = same person on a different body pose, realistic portrait, natural light, detailed face`
  - `seed=123456789`
  - `1024x1024`
  - `steps=20`
  - `cfg=6.5`
  - `sampler=euler`
  - `scheduler=normal`
  - Pose bewusst aus
- Basislauf ohne Maske:
  - `v6_3_transfer_123456789_human_baseline_00001_.png`
  - bleibt technisch stabil und visuell zumindest plausibel
- eng gepruefte Minimalanschluesse:
  - nur `ApplyInstantID.mask`
    - `v6_3_transfer_123456789_human_mask_apply_only_00001_.png`
    - Ergebnis: klarer Artefakt-/Lochzustand statt brauchbarer Begrenzung
  - nur `VAEEncodeForInpaint` im Init-Latent
    - `v6_3_transfer_123456789_human_mask_inpaint_only_00001_.png`
    - Ergebnis: graue Silhouettenflaeche ueber dem Zielkopf
- Hauptursache:
  - die Transfer-Maske ist nicht nur "noch nicht verdrahtet", sondern der aktuelle stabile V6.3-Einpass vertraegt keinen der beiden naheliegenden Minimalanschluesse ehrlich nutzbar
  - konkret kollidiert die Maskenlokalisierung entweder
    - mit dem InstantID-Conditioning (`ApplyInstantID.mask`)
    - oder mit dem Zielbild-Init-Latent (`VAEEncodeForInpaint`)
- ehrliche Entscheidung:
  - Transfer-Maske ist im aktuellen stabilen V6.3-Pfad weiter nicht aktiv und nicht ehrlich freigebbar
  - ein sauberer Fix wuerde ueber einen groesseren Hybridpfad gehen und war fuer diesen engen V6.6-Schritt bewusst nicht zulaessig

## V6.7 Separater Hybridpfad Fuer Transfer-Maske
- stabiler Produktpfad bleibt unveraendert:
  - `python/render_identity_transfer.py`
  - `python/workflows/v6_3_identity_transfer_api.json`
  - keine stille Aktivierung der Maske im bestehenden V6.3-Standardpfad
- neuer separater Prototyp:
  - `python/workflows/v6_3_identity_transfer_mask_hybrid_api.json`
  - `python/render_identity_transfer_mask_hybrid.py`
- Hybrididee:
  - InstantID bleibt ohne direkte `mask`-Einspeisung
  - Zielbild geht weiter ueber `LoadImage -> VAEEncode`
  - die Transfer-Maske greift getrennt nur ueber `LoadImageMask -> SetLatentNoiseMask` in das Ziel-Latent ein
  - Strategie: `instantid_target_body_masked_latent`
- enger Zwischenfehler waehrend der Prototyp-Arbeit:
  - der erste Hybridrunner teilte sich noch denselben Staging-Unterordner mit dem stabilen V6.3-Pfad
  - dadurch konnte ein nachfolgender Basislauf die maskierte Hybriddatei aus dem ComfyUI-Input wegraeumen
  - minimaler Fix:
    - separater Staging-Unterordner nur fuer den Hybridpfad
    - stabiler V6.3-Pfad bleibt davon unberuehrt
- ehrlicher Minimalbefund:
  - mit einer ungefuellten Konturmaske blieb der Eingriff praktisch wirkungslos
  - mit einer sehr groben gefuellten Maske auf einem Nicht-Menschen-Ziel blieb der Hybridpfad zwar stabiler begrenzt, erzeugte aber weiter unbrauchbare Gesichtsartefakte
- Verifikation auf drei engen Menschen-Faellen:
  - gleicher Referenzkopf
  - gleicher Prompt, gleicher Seed, gleicher Samplerpfad
  - nur realistische Einzelpersonen mit sinnvoll gefuellter Kopfmaske
  - Fall 1:
    - Ziel: `result-20260323084219-4e40db90.png`
    - Basis: `v6_3_transfer_123456789_00013_.png`
    - Hybrid: `v6_3_transfer_mask_hybrid_123456789_00004_.png`
    - Ergebnis:
      - Basislauf veraenderte Koerper, Outfit und Gesamtszene deutlich staerker
      - Hybridlauf hielt Koerper, Outfit und Bildaufbau sichtbar naeher am Zielbild
  - Fall 2:
    - Ziel: `result-20260323085038-d9cb5db7.png`
    - Basis: `v6_3_transfer_123456789_00014_.png`
    - Hybrid: `v6_3_transfer_mask_hybrid_123456789_00005_.png`
    - Ergebnis:
      - Hybridlauf begrenzte die Aenderung klarer auf den Kopfbereich
      - das Zielportrait blieb als Gesamtbild naeher am Ursprung als im Basislauf
  - Fall 3:
    - Ziel: `input-20260323084915-fbde289c.png`
    - Basis: `v6_3_transfer_123456789_00015_.png`
    - Hybrid: `v6_3_transfer_mask_hybrid_123456789_00006_.png`
    - Ergebnis:
      - auch im dritten Portrait blieb der Hybridpfad stabil
      - die sichtbare Veraenderung blieb raeumlich enger als im Basislauf
- V6.7-Entscheidung:
  - der separate Masken-Hybridpfad ist fuer enge Menschen-Faelle tragfaehig
  - tragfaehig bedeutet aktuell:
    - realistische Einzelpersonen
    - sinnvoll gefuellte Kopfmasken
    - kein Fantasy-/Nicht-Menschen-Ziel
  - der Pfad bleibt bewusst getrennt vom stabilen V6.3-Produktpfad
  - noch keine Nutzerfreigabe:
    - Konturmasken ohne gefuellte Flaeche bringen kaum Nutzen
    - grobe oder unpassende Masken koennen weiter dunkle Kopf-/Haarartefakte erzeugen
    - Nicht-Menschen-/Fantasy-Ziele bleiben unruhig

## V6.8 Ehrliche Freigabe Des V6.7-Masken-Hybridpfads
- Leitentscheidung:
  - stabiler V6.3-Standardpfad bleibt technisch unveraendert und bleibt der normale Produktweg
  - kein stilles Ueberschreiben von `/identity-transfer/generate`
- separater Produktzugang fuer den Spezialfall:
  - Readiness: `GET /identity-transfer/mask-hybrid/readiness`
  - Generate: `POST /identity-transfer/mask-hybrid/generate`
  - Runner: `python/render_identity_transfer_mask_hybrid.py`
- klare Trennung im Produkt:
  - V6.3-Standardstart bleibt separat
  - V6.8-Masken-Hybridstart ist zusaetzlich als eigener Spezial-Start sichtbar
  - Nutzerhinweis bleibt kurz und explizit auf den engen Gueltigkeitsbereich begrenzt
- ehrlicher Gueltigkeitsbereich:
  - realistische Einzelpersonen
  - sinnvoll gefuellte Kopfmasken
  - Konturmasken allein sind in der Regel wenig wirksam
  - Fantasy-/Nicht-Mensch-Ziele sind nicht freigegeben
- explizit weiter nicht behauptet:
  - keine Allgemeinfreigabe fuer alle Zieltypen
  - keine Freigabe grober oder unpassender Masken als robusten Normalfall

## V6.9 Nutzerfreundliche Absicherung Des V6.8-Masken-Hybridpfads
- kein neuer Bildpfad:
  - V6.3-Standard bleibt unveraendert
  - V6.8 bleibt derselbe getrennte Masken-Hybridpfad
- Fokus nur auf ehrliche Nutzungsfuehrung:
  - Scope-Hinweise klarer und kuerzer
  - V6.8-Readiness im UI mit klareren Hinweisen, was konkret fehlt
  - bessere Fehlermeldungen fuer bekannte Blocker statt generischem "fehlgeschlagen"
- Maskenfuehrung ohne neue Kernlogik:
  - gefuellte Kopfmaske klar empfohlen
  - Konturmasken als meist zu schwach klar benannt
  - Hinweis bei unpassender Zielbild-/Maskengroesse
- weiterhin klar nicht freigegeben:
  - Fantasy-/Nicht-Mensch-Ziele bleiben ausserhalb des ehrlichen V6.8-Geltungsbereichs

## V6.10 Qualitaets-Konstanz Zwischen V6.3 Und V6.8
- Zielbild in diesem Schritt:
  - kein neuer Pfad, kein Architekturumbau
  - nur enge Qualitaetshebel fuer weniger weiche Ausreisser und stabilere Gesichtstreue pruefen
- kleiner Vergleichssatz (nur reale Einzelpersonen):
  - 3 enge Faelle mit fixer Aufloesung `1024x1024`, fixem Sampler `euler`, fixem Checkpoint `sdxl-base.safetensors`
  - feste Seeds pro Fall: `20260321`, `20260322`, `20260323`
  - jeweils V6.3-Standard und V6.8-Masken-Hybrid getrennt durchlaufen
- getestete enge Hebel (einzeln, keine Kombinationen):
  - `steps`: `20 -> 24`
  - `cfg`: `6.5 -> 6.2`
  - `denoise`: `0.65 -> 0.60`
  - `ApplyInstantID.weight`: `0.65 -> 0.70` (nur als Laufzeittest im Benchmark, ohne Produktverdrahtung)
  - ein kleiner Prompt/Conditioning-Hebel: geschaerfter Negativprompt gegen Weichheit
- Ergebnis:
  - kein Hebel zeigte ueber beide Pfade und alle engen Faelle einen stabilen Nettogewinn
  - `denoise 0.60` reduzierte teils Weichheit, erzeugte aber deutliche Gesichtstreue-Ausreisser im Standardpfad
  - `steps 24`, `cfg 6.2`, `weight 0.70` und der Prompt-Hebel waren fallabhaengig und nicht robust genug fuer einen neuen stabilen Default
  - deshalb bleibt der produktive Defaultstand unveraendert (ehrliche Restgrenze statt Scheinverbesserung)
- geschaerfte Produktlinie (ohne neue UI-Funktion):
  - V6.3-Standard bleibt Default fuer den Normalfall und fuer moeglichst konstante Gesichtstreue
  - V6.8-Masken-Hybrid bleibt der getrennte Spezialpfad fuer realistische Einzelpersonen mit sinnvoll gefuellter Kopfmaske, wenn die Aenderung lokal am Kopfbereich bleiben soll

## Fehlende Lokale V6.1-Bausteine

### A. Custom Nodes
- `ComfyUI_InstantID`
  - Zweck: nativer InstantID-Knotenpfad fuer Single-Reference-Identity auf SDXL
  - Lokal vorhanden: ja
  - Fuer V6.1: zwingend
  - Hinweis: der Node-Stack bringt zusaetzliche Python-Runtime-Anforderungen mit (`insightface`, `onnxruntime`)

### B. Modellordner / Modelldateien
- `vendor/ComfyUI/models/insightface/models/antelopev2/*`
  - Zweck: Gesichtsanalyse / Face-Embedding / Keypoints fuer die Referenzperson
  - Lokal vorhanden: ja
  - Fuer V6.1: zwingend
- `vendor/ComfyUI/models/instantid/*`
  - Zweck: InstantID-Hauptmodell fuer identity-preserving Conditioning
  - Lokal vorhanden: ja
  - Fuer V6.1: zwingend
- `vendor/ComfyUI/models/controlnet/*` mit passendem SDXL-ControlNet fuer den InstantID-Pfad
  - Zweck: Pose-/Struktursteuerung im Identity-Workflow
  - Lokal vorhanden: ja
  - Fuer V6.1: zwingend

### C. Workflow-Datei
- dedizierte V6.1-Workflow-Datei fuer Single-Reference-Identity auf SDXL
  - Zweck: separater Generate-Pfad ausserhalb von `txt2img` / `img2img` / `inpainting`
  - Lokal vorhanden: ja
  - Fuer V6.1: zwingend

### D. Runtime-Unterbau
- `insightface >= 0.7.x`
  - Zweck: kompatible `FaceAnalysis`-Runtime fuer `antelopev2` plus Provider-Auswahl
  - Lokal vorhanden: ja
  - Fuer V6.1: zwingend
- `onnxruntime`
  - Zweck: ONNX-Ausfuehrung fuer Face-Analyse
  - Lokal vorhanden: ja
  - Fuer V6.1: zwingend
- `opencv-python` oder `opencv-python-headless`
  - Zweck: `cv2` fuer den InstantID-Node
  - Lokal vorhanden: ja
  - Fuer V6.1: zwingend

### E. Optionale, Aber Nicht Zwingende Zusatzbausteine
- separates Pose-Bild als zusaetzlicher Input
  - Zweck: explizite Posevorgabe statt nur Referenz-Keypoints
  - Lokal vorhanden: nein
  - Fuer V6.1: optional
- zusaetzliche Stil-/Kompositionskomponenten wie IPAdapter-Styling oder weitere ControlNets
  - Zweck: spaetere Feinsteuerung
  - Lokal vorhanden: nein
  - Fuer V6.1: optional
- Multi-Reference-Fusion
  - Zweck: mehrere Referenzen derselben Person kombinieren
  - Lokal vorhanden: nein
  - Fuer V6.1: nicht noetig

## Minimaler Bereitstellungs-Schnitt
- genau ein Identity-Custom-Node-Stack:
  - `ComfyUI_InstantID`
- genau ein zugehoeriger Runtime-Unterbau fuer diesen Stack:
  - `insightface >= 0.7.x`
  - `onnxruntime`
  - `opencv-python` oder `opencv-python-headless`
- genau diese Modellbausteine lokal unter `vendor/ComfyUI/models/`:
  - `insightface/models/antelopev2`
  - `instantid/*`
  - ein passendes SDXL-ControlNet im `controlnet/`-Ordner
- genau eine dedizierte V6.1-Workflow-Datei fuer Single-Reference
- genau ein Referenzbild als Input

## Noch Nicht Noetig Fuer V6.1
- Multi-Reference
- gesonderter Body-Transfer-Ausbau
- PhotoMaker
- PuLID
- FaceID-/IPAdapter-Parallelpfad
- zusaetzliche UI fuer mehrere Referenzslots
- automatische Modell-/Node-Beschaffung

## Quellen
- InstantID official repo: https://github.com/instantX-research/InstantID
- ComfyUI IPAdapter reference implementation: https://github.com/comfyorg/comfyui-ipadapter
- ComfyUI InstantID native support: https://github.com/cubiq/ComfyUI_InstantID
- PuLID ComfyUI native implementation: https://github.com/cubiq/PuLID_ComfyUI
- ComfyUI core repo: https://github.com/Comfy-Org/ComfyUI
