# Product Readiness Snapshot

Stand: 2026-03-27

Hinweis MP-04:
- Dieses Dokument bleibt ein Arbeits- und Verlaufssnapshot zur Produktreife.
- Es ist nicht die kanonische Hauptdokumentation.
- Fuer den verbindlichen MP-04-Abschluss gelten stattdessen:
  - `docs/product_core_mp01.md`
  - `docs/technical_closeout_mp04.md`
  - `docs/project_presentation_mp04.md`

## Produktkurzbild
- Lokales KI-Produkt fuer Text- und Bildarbeit auf Windows
- produktive Hauptstaerken:
  - lokale Text-KI mit 5 Chat-Slots, 3 Arbeitsmodi und 3 kuratierten Modellprofilen
  - `Neues Bild erstellen` als staerkster Bild-Hauptpfad
  - `Bild anpassen` als brauchbarer Bild-Hauptpfad
  - lokale Ergebniswelt mit Vorschau, Download, Export, Wiederladen und Loeschen
- bewusst begrenzte Pfade:
  - `Neue Szene mit derselben Person` nur experimentell / nicht verlaesslich
  - `Bereich im Bild aendern` nur eingeschraenkt verlaesslich bei groesseren Kleidungs-/Formwechseln

## Basismodus
- `Text schreiben / Text-KI nutzen`: nutzbar mit lokalem Modellpfad
- `Neues Bild erstellen`: nutzbar
- `Bild anpassen`: nutzbar
- `Neue Szene mit derselben Person`: aktuell nicht verlaesslich freigegeben; im Basismodus sichtbar als experimenteller Pfad zurueckgestuft
- `Bereich im Bild aendern`: nutzbar fuer kleinere lokale Aenderungen; grosse Kleidungs-/Formwechsel aktuell nicht verlaesslich genug

## V34.3 Produktklarheit
- `Neue Szene mit derselben Person` wird aktuell nicht mehr wie ein verlaesslicher Hauptmodus gefuehrt
- der Pfad bleibt technisch erreichbar, ist aber im Basismodus jetzt sichtbar als experimentell / nicht verlaesslich freigegeben eingeordnet
- damit wird fuer normale Nutzer keine falsche stabile Nutzbarkeit mehr suggeriert

## V35.3 Produktklarheit
- `Bereich im Bild aendern` bleibt sichtbar und nutzbar, wird aber im Basismodus jetzt ehrlicher eingeordnet
- klare Staerke:
  - kleinere lokale Korrekturen
  - kleinere Teilbereichswechsel
  - klar begrenzte Objekt-/Detailaenderungen
- klare Restgrenze:
  - grosse Kleidungs-/Farbwechsel mit Form-Erhalt sind auf diesem lokalen Stand nicht verlaesslich genug
- damit wird der Modus nicht mehr wie ein voll verlaesslicher Praezisions-Alleskönner verkauft

## Erweitert / Experimental
- `V6.1 Single-Reference` technische Ansicht: erreichbar und stabil getrennt
- `Mehrere Referenzbilder nutzen` (V6.2): erreichbar und stabil getrennt
- `Kopf/Gesicht auf Zielbild uebertragen` (V6.3): erreichbar und stabil getrennt
- `V6.8 Masken-Hybrid`: als Spezialpfad im gueltigen Scope getrennt erreichbar
- interner Research-Pfad `identity_research`:
  - separater Experimental-Endpunkt fuer Backbone-Vergleiche
  - nicht in den normalen Basismodus integriert
  - schreibt Vergleichs-Metadaten pro Lauf in `data/results/*.json`
  - aktuell real:
    - `instantid` bereit
    - `pulid_v11` bereit als zweiter isolierter Research-Provider
  - Ziel bleibt rein experimentell:
    - kein Basismodus-Umbau
    - keine normale Nutzerintegration
    - Grundlage fuer spaetere echte Backbone-Vergleiche
  - interner Vergleichshelfer vorhanden:
    - `scripts/run_identity_research_ab.py`
    - feste Serie: `docs/identity_research_test_series_v1.json`

## Ergebniszentrale / Output
- zentrale Ergebnisflaeche ist produktiv nutzbar:
  - Galerie mit Vorschaubild, Pfad, Zeit und Bilddaten
  - grosse Vorschau per Bildklick oder `Vorschau`-Button
  - separater Download pro Ergebnis
- Output ist klar getrennt:
  - `data/results` = app-verwalteter Haupt-Output mit Retention
  - `data/exports` = bewusster Nutzer-Export ohne Auto-Cleanup
- V15.2 Cleanup-Stand:
  - konservativer Housekeeping-Schritt bereinigt nur app-gemanagte `result-*`-Altlasten in `data/results`
  - `data/exports` bleibt ausdruecklich geschuetzt (`exports_protected=true` im Storage-Status)

## Prompt-System (Allgemeine Bildpfade)
- Hauptprompt bleibt primar
- optionaler Negativ-Prompt ist jetzt produktiv durchgaengig:
  - sichtbar in `Neues Bild erstellen`, `Bild anpassen`, `Bereich im Bild aendern`
  - wird real bis zum Renderpfad durchgereicht
  - ungueltige Eingaben werden klar abgefangen (`negative_prompt_not_string`, `negative_prompt_too_long`)

## Expertenbereich
- bleibt als technische Zusatzebene erhalten
- ist nicht mehr der notwendige Standardweg fuer die sichtbaren Hauptaufgaben

## V17 UI-/Produkt-Polierstand
- sichtbare Doppelungen und uneinheitliche Expertentexte wurden weiter reduziert
- Ergebniszentrale und Aktuelles Ergebnis sind im Expertenmodus visuell konsistenter eingebettet
- Klick-Vorschau, Download und Export bleiben unveraendert nutzbar

## V18 Galerie-/Ergebnis-Komfort
- Ergebniszentrale hat jetzt eine bequemere Grossvorschau:
  - `Vorheriges` / `Naechstes`
  - Tastatur: `Pfeil links/rechts`, `Escape`
- direkter Wiederverwendungsweg ist produktiv:
  - `Als Eingabebild laden` aus Ergebniskarte oder Grossvorschau
  - nutzt den bestehenden Input-Bild-Pfad und aktualisiert die aktive Eingabebild-Vorschau sauber

## V19 Produktstruktur Und Prompt-Uebergabe
- Basismodus ist produktlogisch auf Kernaufgaben verdichtet; Spezialpfade sind klar im Bereich `Erweitert / Experimental` gesammelt
- Text-KI bleibt vorne sichtbar und hat jetzt eine direkte Aktion `Als Bildprompt verwenden`
- die Prompt-Uebernahme fuehrt sauber in `Neues Bild erstellen` (ohne neue Pipeline)
- bei `Bild anpassen` und `Bereich im Bild aendern` ist der Ablauf in der Basissicht geordnet: erst Eingabebild/Maskenbereich, dann Prompt/Start

## V20.1 Produktschnitt 2.0 Und Text-KI-Vorbereitung
- Basismodus zeigt jetzt genau 5 Hauptaufgaben:
  - `Text schreiben / Text-KI nutzen`
- `Neues Bild erstellen`
- `Bild anpassen`
- `Experimentell: Neue Szene mit derselben Person`
- `Bereich im Bild aendern`
- Prompt-Uebernahme aus der Text-KI ist jetzt zielgerichtet:
  - `Neues Bild erstellen`
  - `Bild anpassen`
  - `Bereich im Bild aendern`
- `Bild anpassen` zeigt das aktive Eingabebild direkt am Prompt-Bereich fuer einen klareren Arbeitsfluss
- keine neue Pipeline, keine Modellumschaltung, keine neue V6-Kernlogik

## V20.2 Bildweg-Trennung Nachgeschaerft
- `Bild anpassen` fuehrt sichtbarer als leichter/mittlerer Aenderungsweg mit Ausgangsbild als Basis
- fuer neuen Bildaufbau gibt es aktuell keinen verlaesslich freigegebenen Hauptpfad mit derselben Person; der Szenenpfad ist sichtbar als experimentell zurueckgestuft
- Rueckweg ist ebenso direkt sichtbar:
  - von `Neue Szene mit derselben Person` zurueck zu `Bild anpassen`
- keine neue Pipeline, keine Modellaenderung, keine V6-Logikneubauten

## V21 Sicherer Galerie-Loeschpfad
- Ergebniszentrale hat jetzt einen Loeschweg pro App-Ergebnis (`data/results`):
  - Loeschbutton in der Ergebniskarte
  - Loeschbutton in der Grossvorschau
  - Loeschen nur nach Bestaetigung
- Backend-Schutz:
  - neuer Endpunkt `/results/delete`
  - nur gueltige app-gemanagte `result-*`-IDs
  - keine Pfadfreiheit aus dem Frontend
  - keine Loeschung ausserhalb von `data/results`
- `data/exports` bleibt ausdruecklich tabu und unberuehrt.

## V22 Visueller Produkt-Feinschliff (hell/frisch/waermer)
- Frontend-Flaechen wurden auf einen helleren, ruhigeren Produktlook umgestellt:
  - Off-White-Hintergruende, sanfte Gruen-Akzente, waermere Neutrals
  - bessere visuelle Lesbarkeit bei Karten, Eingaben, Statusflaechen, Galerie und Vorschau
- Keine Produktlogik geaendert:
  - keine neuen Features
  - keine Pipeline-/Modell-Aenderung
  - bestehende Pfade bleiben funktional unveraendert

## V23 Inpainting-Lokalitaet (Bereich im Bild aendern)
- Der Inpainting-Pfad wurde gezielt auf lokale Bearbeitung geschaerft:
  - striktere Maskennutzung (serverseitig binaer normalisiert)
  - engerer Inpaint-Rand im Workflow (`grow_mask_by=2`)
  - konservativeres Default-/Grenzverhalten fuer `Aenderungsstaerke` (`0.30`, max `0.60` im Inpaint-Pfad)
  - kurzer, sichtbarer und editierbarer Personen-/Koerper-Negativprompt im Inpaint-Modus vorbelegt
- Produktgrenze bleibt:
  - lokale Aenderungen werden kontrollierter; sehr grosse inhaltliche Umdeutungen bleiben weiterhin kein Ziel dieses Modus
- spaeterer Folgepunkt, bewusst noch nicht umgesetzt:
  - `Komplette Galerie oeffnen` als ruhiger Gesamtueberblick ueber app-gemanagte Ergebnisse

## V20 Modell-/Stilstrategie (eingegrenzt, ohne Rollout)
- Text-KI:
  - aktiver Standard bleibt `Qwen2.5-7B-Instruct GGUF`
  - spaeterer Ausbau nur als kontrollierter Einzel-Upgradepfad (kein Modellzoo, kein Mehrmodellbetrieb)
- Anime:
  - `anime_standard` bleibt als freier Stilmodus im Hauptprodukt
  - enge Motivtreue wird nicht als Standardversprechen gefuehrt
  - spaeterer motivtreuer Anime-Ausbau nur als getrennte Speziallinie

## V16 Packaging-/Install-Komfort
- klarer Hauptstartweg fuer normale Nutzer:
  - `Start_Local_Image_AI.cmd`
- optionale Nutzerhelfer:
  - `Status_Local_Image_AI.cmd`
  - `Stop_Local_Image_AI.cmd`
- optionaler Desktop-Shortcut-Komfort:
  - `Create_Local_Image_AI_Desktop_Verknuepfung.cmd`
  - erstellt `Local Image AI starten.lnk` auf dem Desktop
- technischer Weg bleibt getrennt ueber `scripts/run_stack.ps1`

## Text-KI-Reifegrad
- aktueller produktiver Standard:
  - `Qwen2.5-7B-Instruct GGUF`
- stark fuer:
  - Bildprompt-Hilfe
  - Umformulierungen
  - kurze Alltagsantworten
- V26 Arbeitsstand:
  - 5 feste lokale Chat-Slots
  - lokale Speicherung in `data/text_chats.sqlite3`
  - aktiver Slot liefert Kontext, inaktive Slots bleiben gespeichert
  - rollende Kurz-Zusammenfassung fuer aeltere Chatteile
  - Copy, Spracheingabe und `Als Bildprompt verwenden` bleiben im Hauptbereich aktiv
- V27 Arbeitsmodi:
  - `Schreiben` fuer freie kreative Schreibarbeit und Fortsetzungen
  - `Ueberarbeiten` fuer Umformulieren, Straffen und stilistische Verbesserung bestehender Texte
  - `Als Bildprompt umwandeln` fuer kurze, visuelle Prompt-Ausgabe mit weiter bestehender Handoff-Aktion in die Bild-KI
- V27.1 UI-Validierung:
  - sichtbare Browser-Klicks fuer Slots, Moduswechsel, Copy, Prompt-Uebergabe, Reload und Leeren real geprueft
  - sichtbare Kurz-Zusammenfassung bei laengerem Verlauf real bestaetigt
  - kleine UX-Korrektur: Prompt-Uebergabe meldet den Erfolg jetzt auch sichtbar im Ziel-Bildpfad
- V28 kuratierte Modell-Slots:
  - genau 3 sichtbare Modellprofile statt Modellzoo:
    - `Standard`
    - `Starkes Schreiben`
    - `Mehrsprachig`
  - pro Chat-Slot wird das gewaehlte Modellprofil mitgespeichert
  - der aktuelle lokale Realstand ist bewusst ehrlich:
    - `Standard` ist aktiv und nutzbar
    - `Starkes Schreiben` ist vorbereitet, aber lokal noch nicht verfuegbar
    - `Mehrsprachig` ist vorbereitet, aber lokal noch nicht verfuegbar
  - keine freie Modellliste, kein Download-Center, keine Importstrecke fuer normale Nutzer
- V29 kontrollierte Modellwechsel-Basis:
  - der Text-Runner kann fuer kuratierte Profile jetzt kontrolliert neu initialisiert werden
  - der aktive Chat traegt sein Profil weiter sauber mit
  - `Standard` laeuft stabil und kann nach Runner-Ausfall wieder kontrolliert hochgezogen werden
  - vorbereitete Profile bleiben ehrlich:
    - im Chat speicherbar
    - sichtbar als `Vorbereitet`
    - Requests werden sauber mit Statusfehler abgewiesen, solange das Zielmodell lokal fehlt
  - keine freie Modellliste, kein Modellzoo, kein Download-Center
- V30 produktiver Schreibslot:
  - `Starkes Schreiben` ist jetzt real lokal verfuegbar und lauffaehig
  - reales GGUF:
    - `mistral-small-3.1-24b-instruct-2503-jackterated-hf.Q4_K_S.gguf`
  - Runner-Wechsel ist real geprueft:
    - `Standard -> Starkes Schreiben`
    - `Starkes Schreiben -> Standard`
  - Schreib-, Ueberarbeiten- und Bildprompt-Test auf `Starkes Schreiben` sind real gruen
  - aktiver Chat und Runner werden beim Laden der Text-Uebersicht wieder sauber synchronisiert
  - sichtbarer Browser-Wechsel zwischen `Standard` und `Starkes Schreiben` ist real bestaetigt
- V31 produktiver Mehrsprachig-Slot:
  - `Mehrsprachig` ist jetzt real lokal verfuegbar und lauffaehig
  - reales GGUF:
    - `google_gemma-3-12b-it-Q5_K_M.gguf`
  - Runner-Wechsel ist real geprueft:
    - `Standard -> Mehrsprachig -> Standard`
    - `Starkes Schreiben -> Mehrsprachig -> Starkes Schreiben`
  - mehrsprachige Nutzwerttests real gruen:
    - Deutsch
    - Englisch
    - Spanisch
    - Rewrite auf Franzoesisch
    - englische Bildprompt-Ausgabe
  - sichtbare Browser-Aktivierung und Statuswechsel fuer `Mehrsprachig` real bestaetigt
- ehrliche Restgrenze:
  - kurze Wissensfragen bleiben sichtbar schwaecher
- Produktlinie:
  - drei kuratierte Modell-Slots sind jetzt produktiv:
    - `Standard`
    - `Starkes Schreiben`
    - `Mehrsprachig`
  - spaeter nur kontrolliert erweitern, wenn die Zielmodelle lokal wirklich produktiv verfuegbar sind
- V36 Langprompt-/Runner-Stabilitaet:
  - Runner-Start fuer starke Profile hat jetzt ein realistisch groesseres Startfenster
  - Langform-Requests warten deutlich laenger und fallen nicht mehr vorschnell auf `runner_unreachable`
  - Text-Service unterscheidet jetzt zwischen echtem Runner-Ausfall und echtem Request-Timeout bei weiter laufendem Runner
  - Wortziel-/Bereichsangaben wie `350 bis 450 Woerter` oder `260 to 340 words` steuern wieder den Langformpfad statt still in den Kurzpfad zu fallen
  - lange Rewrite-Antworten werden nicht mehr serverseitig auf Mini-Format abgeschnitten
- V36.1 Laengensteuerung:
  - Wortzielbereiche werden jetzt als echte Bounds verarbeitet statt nur als weiche Einzelzahl
  - Rewrite-Auftraege bekommen die Laengenvorgabe jetzt direkt im eigentlichen Ueberarbeitungsauftrag
  - Rewrite- und Langform-Retry pruefen Untergrenzen jetzt enger gegen die gewuenschte Wortspanne
  - real sichtbar besser:
    - `strong_writing` traf `350 bis 450 Woerter` mit `408` Woertern
    - `multilingual` traf `260 bis 340 words` mit `304` Woertern
  - ehrliche Restgrenze:
    - lange Rewrite-Auftraege koennen noch ueber die obere Grenze hinausschiessen
- V36.2 Rewrite-Obergrenzen:
  - Rewrite-Retry fuehrt die Wortspanne jetzt neutraler und widerspruchsfrei
  - wenn ein erster Rewrite-Entwurf ueber der Obergrenze liegt, wird der Retry intern mit engerem Token-Korridor gefahren statt weiter aufgeblasen
  - real sichtbar besser auf `strong_writing`:
    - `300 bis 380 Woerter` traf `311` Woerter
    - `260 bis 340 Woerter` traf `331` Woerter
  - ehrliche Restgrenze:
    - `multilingual`-Rewrite blieb im Test unter der Untergrenze
    - kurzer `standard`-Rewrite blieb im Kontrolltest zu kurz
- Text-Vollanzeige:
  - der lange Antworttext wurde nicht im Backend gekappt
  - API, Chatdaten und DOM enthielten denselben Volltext
  - der sichtbare Cut entstand im UI durch zu enge feste Hoehen fuer Antwort- und Verlaufscontainer
  - diese Container sind jetzt deutlich groesser; der Antwortblock bleibt zusaetzlich vertikal vergroesserbar
- End-to-End-Volltextschutz:
  - der Langtextpfad im Text-Service wurde gegen echte abgeschnittene Runner-Enden nachgezogen
  - lange Texte werden im Chat wieder voll gespeichert und im Verlauf 1:1 aus dem gespeicherten Chat gerendert
  - der Copy-Pfad kopiert den Volltext des gerenderten Antwortblocks statt nur einen sichtbaren Ausschnitt
- V36.5 Textqualitaet und Laengensteuerung:
  - Sprachbindung fuer mehrsprachige Auftraege wurde expliziter
  - Wortzielanweisungen fuehren Unter- und Obergrenzen klarer
  - Rewrite fuer kurze Zielspannen wird nicht mehr nur verdichtet, sondern gezielt als vollwertiger Kurztext gefuehrt
  - ehrlicher Reststand:
    - `strong_writing`-Schreiben ist brauchbar im Zielbereich
    - `strong_writing`-Rewrite und `multilingual` liegen knapp unter der Untergrenze
    - kurzer `standard`-Rewrite liegt noch ueber der Obergrenze
- V37 Browser-/Produktreife:
  - `Neuer Chat` legt auf einem aktiv gewaehlten freien Slot jetzt den Chat in genau diesem Slot an statt im ersten freien Slot
  - neue oder automatisch erzeugte leere Chats starten jetzt auf dem sicheren Profil `standard` statt ein gerade aktives schweres Profil mitzuerben
  - der sichtbare Hauptfluss wurde real im Browser geprueft:
    - Text-KI inkl. Slotwechsel, Neu, Umbenennen, Leeren, Copy und Prompt-Uebergabe
    - `Neues Bild erstellen`
    - `Bild anpassen`
    - `Bereich im Bild aendern`
    - Ergebniswelt inkl. Vorschau, Download, Export, Als Eingabebild laden und Loeschen
  - `Neue Szene mit derselben Person` bleibt im sichtbaren Hauptfluss ehrlich experimentell markiert
- V39 UI-/UX-Polish:
  - Ergebniswelt:
    - Prompt und Negativprompt sind jetzt direkt auf den Ergebniskarten selektierbar
    - kleine Copy-Buttons fuer diese Texte sind als ruhiger Fallback vorhanden
  - Negativprompt:
    - optionaler Standard-Negativprompt ist jetzt per Toggle nutzbar
    - Standardtext startet sinnvoll aktiv, bleibt editierbar und wird beim Umschalten nicht staendig erzwungen
  - Optik:
    - Hilfetexte, Nebeninfos, Karten und Preview-Kontexte sind etwas klarer abgesetzt und besser lesbar

## Bewusster Produkt-Stopp
- Die sichtbaren Hauptpfade fuer normale Nutzer sind vorhanden.
- Weitere Arbeit ist jetzt kein Pflichtblock fuer Grundnutzbarkeit, sondern gezielter Wunsch- oder Qualitaetsausbau.
