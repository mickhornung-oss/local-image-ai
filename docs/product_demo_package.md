# Produkt- und Demo-Paket

Stand: 2026-03-27

Hinweis MP-04:
- Dieses Dokument bleibt als aeltere Demo-Arbeitsgrundlage erhalten.
- Fuer die verbindliche Praesentationslogik des Abschlussstands gilt jetzt `docs/project_presentation_mp04.md`.

## 1. Produktueberblick
- Dieses Projekt ist ein lokales KI-Produkt fuer Text- und Bildarbeit auf Windows.
- Es kombiniert:
  - lokale Text-KI mit Chat-Slots und Modellprofilen
  - lokale Bild-KI mit klar gefuehrten Hauptpfaden
  - lokale Ergebniswelt mit Galerie, Vorschau, Export und Wiederverwendung
- Hauptnutzen:
  - Texte lokal schreiben, ueberarbeiten und in Bildprompts umwandeln
  - Bilder lokal erzeugen und auf Basis eines Eingabebilds weiterbearbeiten
  - Ergebnisse ohne Cloud-Abhaengigkeit lokal behalten

## 2. Kernfunktionen
- Text-KI:
  - 5 lokale Chat-Slots
  - lokale Speicherung
  - 3 Arbeitsmodi:
    - `Schreiben`
    - `Ueberarbeiten`
    - `Als Bildprompt umwandeln`
  - 3 kuratierte Modellprofile:
    - `Standard`
    - `Starkes Schreiben`
    - `Mehrsprachig`
  - Copy und Prompt-Handoff in die Bild-KI
- Bild-KI:
  - `Neues Bild erstellen`
  - `Bild anpassen`
  - `Bereich im Bild aendern`
  - Ergebniszentrale mit Vorschau, Download, Export, Wiederladen und Loeschen

## 3. Starke Hauptpfade
- `Text schreiben / Text-KI nutzen`
  - produktiv nutzbar fuer lokale Schreib-, Rewrite- und Prompt-Arbeit
- `Neues Bild erstellen`
  - staerkster Bildpfad
  - klarer Prompt-zu-Bild-Hauptweg
- `Bild anpassen`
  - brauchbarer Hauptpfad fuer Aenderungen auf Basis eines vorhandenen Bilds
- Ergebniswelt
  - alltagstauglich fuer Vorschau, Download, Export und Weiterverwendung

## 4. Ehrliche Grenzen
- `Neue Szene mit derselben Person`
  - bewusst experimentell
  - aktuell nicht verlaesslich genug als Hauptmodus
- `Bereich im Bild aendern`
  - brauchbar fuer kleinere lokale Aenderungen
  - nicht verlaesslich genug fuer groessere Kleidungs-/Farbwechsel mit Form-Erhalt
- Text-KI
  - insgesamt nutzbar, aber Wortzieltreue und Rewrite-Laenge sind nicht in jedem Profil perfekt
  - kurze Wissensfragen bleiben schwaecher als Schreib- und Umformulierungsaufgaben

## 5. Start und Nutzung
- Normaler Start:
  1. `Start_Local_Image_AI.cmd`
  2. Browser auf `http://127.0.0.1:8090`
- Status pruefen:
  - `Status_Local_Image_AI.cmd`
- Stoppen:
  - `Stop_Local_Image_AI.cmd`
- Empfohlene Nutzung:
  1. erst Text oder Bild-Hauptaufgabe waehlen
  2. bei Bildaufgaben klare Prompts nutzen
  3. Ergebnisse ueber Galerie/Vorschau weiterverwenden
  4. experimentelle oder begrenzte Pfade nicht als sichere Demo-Hauptstrecke nutzen

## 6. Empfohlener Demo-Ablauf
- Demo 1: Text-KI
  1. freien Chat-Slot oeffnen
  2. `Schreiben` zeigen
  3. `Ueberarbeiten` zeigen
  4. `Als Bildprompt umwandeln` zeigen
  5. `Als Bildprompt verwenden` in den Bildpfad uebergeben
- Demo 2: Bild-KI
  1. `Neues Bild erstellen` mit dem uebergebenen Prompt starten
  2. Ergebnis in der Vorschau zeigen
  3. Download / Export / `Als Eingabebild laden` zeigen
- Demo 3: Bildbearbeitung
  1. `Bild anpassen` mit geladenem Eingabebild zeigen
  2. `Bereich im Bild aendern` nur mit kleiner lokaler Aenderung zeigen
- Nicht als Hauptdemo verkaufen:
  - `Neue Szene mit derselben Person`
  - grosse Kleidungs-/Formwechsel im Inpaint-Pfad

## 7. Aktueller Reifegrad
- Produktlogisch ernstzunehmender lokaler Stand
- sichtbarer Hauptfluss browserseitig real geprueft
- starke Kernpfade klar vorhanden
- Grenzen ehrlich im Produkt eingeordnet
- geeignet fuer:
  - Demo
  - Abgabe
  - Dozentenpraesentation
  - nachvollziehbare Projektuebergabe

## 8. Realer Abschlussstand
- Text-KI:
  - lokal nutzbar
  - Volltext bleibt erhalten, sichtbar und kopierbar
- Bild-KI:
  - Hauptpfade browserseitig real geprueft
  - Ergebniswelt bedienbar
- Produktdarstellung:
  - starke Pfade vorne
  - schwache Pfade ehrlich begrenzt
