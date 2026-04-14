# Projektpraesentation MP-04

Stand: 2026-04-07

## Zweck

Dieses Dokument ist die belastbare Praesentationsgrundlage fuer Abgabe, Demo und Abschlussvortrag.

Es ist bewusst als Folienskelett mit Sprecherlogik aufgebaut und orientiert sich am realen Repo- und Produktstand.

## Folie 1 - Titel / Kurzbild

Titel:
- `Local Image AI - lokale Text- und Bild-KI fuer Windows`

Kernaussage:
- Ein lokales Produkt fuer Schreiben, Prompt-Hilfe und Bildarbeit ohne Cloud-Zwang.

## Folie 2 - Problem / Ziel

Problem:
- Viele KI-Workflows sind cloudbasiert, schwer kontrollierbar oder fuer lokale kreative Arbeit zu verstreut.

Ziel:
- Ein lokales, ernsthaft nutzbares Produkt fuer:
  - Schreiben und Ueberarbeiten von Texten
  - Uebersetzen und Prompt-Hilfe
  - Erstellen und Bearbeiten von Bildern
  - lokale Ergebnisverwaltung ohne Cloud-Abhaengigkeit

## Folie 3 - Projektidee

- Browser-UI als einfacher Hauptzugang
- lokaler App-Server orchestriert Text- und Bildpfade
- lokaler Text-Stack mit kuratierten Profilen
- lokaler Bild-Stack ueber ComfyUI
- klare Trennung zwischen produktiven Hauptpfaden und experimentellen Pfaden

## Folie 4 - Produktumfang

Produktiv:
- Text-KI mit gespeicherten Chats
- `Standard`, `Starkes Schreiben`, `Mehrsprachig`
- `Neues Bild erstellen`
- `Bild anpassen`
- `Bereich im Bild aendern`
- Ergebniswelt mit Vorschau, Download, Export und Wiederverwendung

Experimentell:
- `Neue Szene mit derselben Person`
- Mehrbild-/Transfer-/Masken-Hybrid-Pfade
- Research- und Spezialstarts

## Folie 5 - Aktive Architektur

Komponenten:
- Browser-UI: `web/index.html`
- Haupt-App: `python/app_server.py`
- Text-Service: `python/text_service.py`
- Text-Runner auf `8092`
- ComfyUI auf `8188`

Lokale Ports:
- `8090` Haupt-App
- `8091` Text-Service
- `8092` Text-Runner
- `8188` ComfyUI

## Folie 6 - Text-KI

Produktnutzen:
- normales Schreiben
- laengeres Schreiben
- Uebersetzen / Umformulieren
- Prompt-Hilfe
- gespeicherte Chats

Textmodi:
- `Standard` fuer Alltags- und mittlere Schreibaufgaben
- `Starkes Schreiben` fuer laengere Texte
- `Mehrsprachig` fuer Uebersetzen / Umformulieren

## Folie 7 - Bild-KI

Produktive Hauptpfade:
- `Neues Bild erstellen`
- `Bild anpassen`
- `Bereich im Bild aendern`

Wichtiger Produktpunkt:
- Der sichtbare Hauptpfad ist auf alltagstaugliche Bildarbeit reduziert.
- Experimentelle Bildpfade sind getrennt und nicht mehr mit dem Hauptweg vermischt.

## Folie 8 - Ergebniswelt

- Galerie mit letzten Bildern
- grosse Vorschau
- Download
- Export in separaten Exportordner
- Wiederverwendung als Ausgangsbild
- Entfernen aus der app-verwalteten Hauptliste

Nutzen:
- Das Produkt endet nicht beim Generate-Button, sondern hat einen nutzbaren Nachlauf.

## Folie 9 - Trennung von produktiv und experimentell

Produktiv:
- Text-Hauptpfad
- drei Bild-Hauptpfade
- Ergebniswelt

Experimentell:
- gleiche Person in neuer Szene
- Transfer-/Mehrbild-/Masken-Hybrid-Pfade

Historisch:
- alte V1-/VS-Code-/Backend-Bestaende bleiben im Repo, sind aber klar nicht der aktive Produktkern

## Folie 10 - Technische Herausforderungen

- lokaler Windows-Stack statt Cloud
- Modell- und Laufzeitgrenzen auf CPU / lokalem Rechner
- grosse UI-Datei und grosser App-Server-Restkern
- unterschiedliche Reifegrade zwischen produktiven und experimentellen Bildpfaden

## Folie 11 - Wichtigste Verbesserungen

- MP-01:
  - Produktiv / Experimentell / Historisch festgezogen
  - offizieller Start-/Status-/Pruefpfad festgelegt
- MP-02R:
  - Text-KI auf produktiv nutzbaren Stand gezogen
  - Rollen der Textmodi verbindlich gemacht
- MP-03:
  - Basismodus beruhigt
  - Experimentalbereich klar getrennt
  - Ergebniswelt alltagstauglicher gemacht
- MP-04:
  - kanonische Produktdoku
  - technische Abschlussdoku
  - echte Schlussabnahme

## Folie 12 - Bekannte Grenzen

- Langes Schreiben ist nutzbar, aber auf CPU langsamer als normale Schreibaufgaben.
- `Bereich im Bild aendern` ist nicht fuer grosse Form-/Kleidungswechsel gedacht.
- Identity-/Research-Pfade bleiben experimentell.
- `web/index.html` und `python/app_server.py` bleiben technische Hotspots.

## Folie 13 - Schlussfazit

- Das Projekt ist kein Greenfield-Entwurf mehr, sondern ein lokal nutzbares Produkt mit klaren Hauptpfaden.
- Text-KI und Bild-KI sind im selben Produkt sinnvoll verbunden.
- Die staerksten Hauptpfade sind produktiv, die schwaecheren Pfade sind ehrlich getrennt.
- Der Projektstand ist abgabefaehig, uebernahmefaehig und praesentierbar.

## Empfohlene Live-Demo-Reihenfolge

1. Produkt kurz zeigen: Basismodus versus `Erweitert / Experimental`
2. Text-KI:
   - kurzen Schreib- oder Prompt-Hilfe-Fall zeigen
   - `Als Bildprompt verwenden`
3. Bild-KI:
   - `Neues Bild erstellen`
   - Ergebnisvorschau
   - `Als Ausgangsbild verwenden`
4. `Bild anpassen`
5. Ergebniswelt:
   - Download / Export / Wiederverwendung
6. Experimentellen Bereich nur kurz als bewusst getrennten Sonderbereich zeigen

## Nicht als Hauptdemo verkaufen

- `Neue Szene mit derselben Person`
- grosse Kleidungs-/Formwechsel im Inpainting-Pfad
- tiefe technische Spezialstarts
