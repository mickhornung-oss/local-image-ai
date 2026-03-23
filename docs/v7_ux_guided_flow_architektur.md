# V7 UX / Guided Flow Architektur

## Ist-Zustand
- Die Hauptseite zeigt heute mehrere technisch getrennte Bloecke direkt nebeneinander:
  - `Generate`
  - `Text-Service-Test`
  - `Eingabebilder`
  - `Identity-Referenztest`
  - `Identity Multi-Reference Test`
  - `V6.3.1 Transfer-Rollen`
  - `V6.3 Transfer-Test`
  - `Aktuelles Ergebnis`
  - `Letzte Ergebnisse`
- Der technische Unterbau ist stabil, aber die sichtbare Struktur ist fuer normale Nutzer zu breit.
- Die vorhandenen Testpfade fuer V6.1, V6.2 und V6.3 sind wertvoll, gehoeren aber nicht in die Primaernavigation fuer Alltagsnutzung.

## UX-Probleme Heute
- Zu viele technische Begriffe statt aufgabenbezogener Sprache.
- Zu viele getrennte Bloecke ohne klare Reihenfolge.
- Zu wenig Fuehrung bei der Frage: "Was will ich eigentlich tun?"
- Normalmodus und Test-/Expertenpfade stehen zu nah nebeneinander.
- Identitaetsfunktionen erscheinen heute als technische Spezialpfade statt als gefuehrte Aufgabe.

## Zielbild
- Ein normaler Nutzer denkt spaeter zuerst in Aufgaben, nicht in Pipelines oder internen Modi.
- Primaere Nutzerfrage:
  - `Was willst du tun?`
- Daraus folgt dann automatisch:
  - welche Eingaben sichtbar werden
  - welche optionalen Bilder gebraucht werden
  - welcher Startbutton aktiv ist
  - wie das Ergebnis erklaert wird

## Sichtbare Nutzerpfade
- `Neues Bild aus Prompt`
- `Bild veraendern`
- `Bereich im Bild aendern`
- `Dieselbe Person in neuer Variante`
- `Mehrere Referenzbilder nutzen`
- `Kopf/Gesicht auf Zielbild uebertragen`

## Gepruefte Varianten

### A. Alles auf einer Seite, aber stark gefaltet
- Vorteil:
  - kleinster Eingriff in die bestehende Seite
- Nachteil:
  - strukturell bleibt alles ein grosses Cockpit
  - Test- und Normalpfade bleiben zu eng gekoppelt
  - Nutzer muessen weiter viele Begriffe gleichzeitig sortieren
- Urteil:
  - fuer dieses Repo zu wenig echte Vereinfachung

### B. Gefuehrter Aufgabenmodus
- Vorteil:
  - fuer normale Nutzer am intuitivsten
  - Eingaben koennen klar pro Aufgabe eingeblendet werden
- Nachteil:
  - ohne separate Trennung bleiben bestehende Test-/Expertenflaechen weiter stoerend
  - hoehere Umbaukosten direkt auf der Hauptseite
- Urteil:
  - stark fuer den spaeteren Normalmodus, aber allein noch nicht sauber genug gegen die vorhandenen Testpfade abgegrenzt

### C. Einfacher Basismodus plus separater Experten-/Testbereich
- Vorteil:
  - beste Trennung zwischen Normalnutzung und technischen Spezialpfaden
  - geringstes Konfliktrisiko mit dem stabilen Ist-Stand
  - bestehende V6.1/V6.2/V6.3-Testpfade koennen erhalten bleiben, ohne den Normalmodus zu verstopfen
  - spaeter gut mit aufgabenbezogener Fuehrung im Basismodus kombinierbar
- Nachteil:
  - erfordert klare Sichtbarkeitsregeln statt blosses Ein-/Ausklappen
- Urteil:
  - beste Zielarchitektur fuer dieses Repo

## Empfohlene Zielarchitektur
- V7 soll Variante C nutzen:
  - ein einfacher Basismodus fuer normale Nutzer
  - ein klar abgetrennter Experten-/Testbereich fuer V6.1, V6.2, V6.3 und spaetere Spezialpfade
- Der Basismodus wird spaeter aufgabenbezogen gefuehrt, aber bleibt in der Primaaroberflaeche bewusst klein.
- Der Experten-/Testbereich ist kein Standardarbeitsplatz, sondern ein bewusst separater Technikbereich.

## Sichtbarkeitsregeln

### Im Normalmodus sichtbar
- Aufgabenwahl in Alltagssprache:
  - `Neues Bild`
  - `Bild veraendern`
  - `Bereich aendern`
  - `Person mit Referenz variieren`
- Nur die zur gewaehlten Aufgabe passenden Eingaben
- Ein klarer Startbereich
- Aktuelles Ergebnis
- Letzte Ergebnisse

### Nur kontextabhaengig sichtbar
- Source-Bild nur bei Bildveraenderung / Inpainting / Referenzpfaden
- Maske nur bei Bereichsaenderung oder spaeterem Transferkontext
- Referenzbilder nur bei Identitaetsaufgaben
- Multi-Reference nur, wenn die Aufgabe das wirklich braucht
- Transferrollen nur im spaeteren V6.3-Kontext

### In den Experten-/Testbereich
- `Text-Service-Test`
- `Identity-Referenztest`
- `Identity Multi-Reference Test`
- `V6.3.1 Transfer-Rollen`
- `V6.3 Transfer-Test`
- technische Readiness-Hinweise
- Entwicklernahe Detailzustande

## No-Gos
- Kein ueberladenes Cockpit mit allen Bloecken gleichzeitig.
- Kein Mega-Status-Panel fuer normale Nutzer.
- Keine drei Identity-Bloecke direkt im Normalmodus.
- Keine Primaarnavigation ueber technische Begriffe wie `img2img`, `V6.2` oder `Transfer-Rollen`.
- Keine Vermischung von Testmodus und Normalmodus auf derselben Hauptebene.
- Keine Rohzustands- oder Debug-Flaechen fuer Alltagsnutzung.

## Enger Ausbaupfad

### V7.1 Navigations-/Aufgabenmodell
- klare Aufgabenwahl fuer den Basismodus
- Test-/Expertenbereich aus der Primaarflaeche herausloesen
- real umgesetzt:
  - oberer Einstieg `Was moechtest du machen?`
  - Umschaltung `Basismodus` / `Experten-/Testbereich`
  - sechs klare Aufgaben fuer die stabile Zuordnung zu V1/V6-Pfaden
  - Basismodus blendet nur den passenden Hauptbereich plus Ergebnisse ein
  - Experten-/Testbereich haelt die bestehenden Technikbloecke weiter erreichbar
- bewusst noch nicht Teil von V7.1:
  - keine Detailvereinfachung der Formulare
  - keine neue Pipeline- oder Featurelogik

### V7.2 Vereinfachte gefuehrte Eingabeflaeche
- je Aufgabe nur die relevanten Eingaben
- Startaktion und Ergebnis klar koppeln
- real umgesetzt:
  - `Neues Bild erstellen` zeigt im Basismodus nur Prompt plus Start
  - `Bild veraendern` zeigt Eingabebild, Prompt, Denoise und Start
  - `Bereich im Bild aendern` zeigt Eingabebild, Maske/Masken-Editor, Prompt und Start
  - `Dieselbe Person neu erzeugen` zeigt nur den V6.1-Referenzpfad mit Prompt, Readiness und Start
  - `Mehrere Referenzbilder nutzen` zeigt Slots, Readiness, Prompt und den getrennten V6.2-Start
  - `Kopf/Gesicht auf Zielbild uebertragen` zeigt Pflichtrollen, optionale Zusatzrollen, Readiness, Prompt und den getrennten V6.3-Start
  - unpassende Eingaben bleiben im Basismodus versteckt
  - Experten-/Testbereich bleibt separat und zeigt die technischen Bloecke weiter bewusst gesammelt
- bewusst noch nicht Teil von V7.2:
  - keine Detailvereinfachung der Backend-Pipelines
  - kein groesserer visueller Umbau

### V7.3 Experten-/Testbereiche sauber abtrennen
- bestehende V6.1/V6.2/V6.3-Testflaechen erhalten
- aber ausserhalb des Normalmodus fuehren
- real umgesetzt:
  - Basismodus zeigt jetzt zuerst eine ruhige Aufgaben-Zusammenfassung statt halb offener Testflaechen
  - die fortgeschrittenen Aufgaben `Dieselbe Person neu erzeugen`, `Mehrere Referenzbilder nutzen` und `Kopf/Gesicht auf Zielbild uebertragen` fuehren im Basismodus nur noch gezielt in den Experten-/Testbereich
  - `Text-Service-Test`, V6.1, V6.2 und V6.3 liegen sichtbar gesammelt im Experten-/Testbereich
  - der Basismodus zeigt nur Aufgabenwahl, gefuehrte Eingaben und Ergebnisbereiche
- bewusst noch nicht Teil von V7.3:
  - kein groesserer visueller Relaunch
  - keine Detailvereinfachung der Expertenflaechen selbst

### V7.4 Mikrotexte und Begriffsvereinfachung
- Basismodus sprachlich vereinfachen, ohne die bestehenden Pfade umzubauen
- real umgesetzt:
  - klarere Begriffe im Basismodus: `Bild`, `Referenzbild`, `Zielbild`, `Maske`, `Ergebnis`
  - kuerzere Schrittfuehrung pro Aufgabe direkt an den sichtbaren Basismodus-Bloecken
  - nutzernaehere Statussaetze wie `Jetzt kannst du starten`, `Bild fehlt noch`, `Maske fehlt noch`, `Bild geladen`
  - technische Details bleiben im Experten-/Testbereich erlaubt und werden im Basismodus nicht weiter aufgeblasen
  - Bild- und Maskenmetadaten werden im Basismodus knapp statt als technische JSON-Zusammenfassung gezeigt
- bewusst noch nicht Teil von V7.4:
  - kein weiterer UI-Umbau
  - keine neue Pipeline- oder Featurelogik

### V7.5 Status-/Hinweislogik
- Basismodus zeigt pro Aufgabe nur noch einen klaren Leithinweis fuer `fehlt`, `bereit`, `laeuft` oder `fertig`
- real umgesetzt:
  - `Neues Bild erstellen`: `Gib zuerst einen Prompt ein`, `Jetzt kannst du starten`, `Bild wird erstellt...`, `Ergebnis ist fertig`
  - `Bild veraendern`: `Lade zuerst ein Bild hoch`, `Beschreibe danach die Aenderung`, `Jetzt kannst du starten`, `Bild wird bearbeitet...`
  - `Bereich im Bild aendern`: `Lade zuerst ein Bild hoch`, `Maske fehlt noch`, `Beschreibe den markierten Bereich`, `Bildbereich wird geaendert...`
  - V6.1, V6.2 und V6.3 zeigen im Basismodus nur noch fehlende Pflichtangaben, Readiness und den klaren Hinweis auf den Experten-/Testbereich
  - doppelte Upload-, Masken- und ruhende Systemhinweise wurden im Basismodus reduziert
- bewusst noch nicht Teil von V7.5:
  - kein weiterer Design-Umbau
  - keine Backend- oder Pipeline-Aenderung

### V7.6 Experten-/Testbereich blockweise trennen
- Expertenpfade klar getrennt halten, ohne die bestehenden Testpfade umzubauen
- real umgesetzt:
  - `Text-Service-Test`, `V6.1 Single-Reference`, `V6.2 Multi-Reference` und `V6.3 Transfer` erscheinen jetzt als klar getrennte Expertenbloecke
  - jeder Pfad hat seine eigene Eingabezone, eigene Readiness-/Statuszone, eigenen Startpunkt und eigene Ergebnis-/Fehlerzone
  - V6.3 fuehrt Rollenpflege und separaten Transfer-Start jetzt sichtbar unter einem gemeinsamen Transfer-Block zusammen
  - V6.2 zieht seine Ergebnis-Metadaten im Expertenblock jetzt sauber aus dem Ergebnisstore nach (`Referenzen`, `Slots`, `Strategie`)
  - Basismodus bleibt davon unberuehrt und zeigt keine offenen Technikbloecke
- bewusst noch nicht Teil von V7.6:
  - kein weiterer Qualitaets- oder Design-Ausbau
  - kein neuer Normalnutzerpfad fuer die Expertenfunktionen

### V7.7 Text-KI als sichtbarer Basispfad
- der Basismodus zeigt jetzt auch `Text schreiben / Text-KI nutzen` als eigene Aufgabe fuer normale Nutzer
- real umgesetzt:
  - eigener ruhiger Basismodus-Block fuer Text mit Texteingabe, Startbutton, kompaktem Status und kompakter Antwortanzeige
  - der Basispfad nutzt weiter denselben Haupt-App-Pfad zum separaten lokalen Text-Service
  - der aktuelle Stand bleibt ehrlich sichtbar:
    - ohne Runner oder Modell bleibt der Pfad sauber im Test-/Nicht-bereit-Stand
    - mit lokalem Runner und GGUF-Modell nutzt derselbe sichtbare Pfad jetzt echte lokale Antworten
  - der technische `Text-Service-Test` bleibt getrennt im Experten-/Testbereich
- bewusst noch nicht Teil von V7.7:
  - kein Chatverlauf
  - kein Streaming
  - kein echter Modellpfad fuer normale Nutzer

### V8.3 Text-KI im Basismodus ehrlich auf Modellbetrieb ziehen
- der sichtbare Text-KI-Pfad im Basismodus spiegelt jetzt den echten lokalen Modellbetrieb sprachlich und statusseitig sauber wider
- real umgesetzt:
  - bei `real_model_ready` zeigt der Basismodus jetzt nutzernahe Hinweise wie `Lokale Text-KI ist bereit`, `Antwort wird erzeugt` und `Antwort ist fertig`
  - wenn Modell oder Runner nicht bereit sind, bleibt der Basispfad kurz und ehrlich: `Text-KI aktuell nicht verfuegbar` oder `Lokales Modell noch nicht bereit`
  - Stub-/Testsprache bleibt aus dem Normalpfad raus, sobald der echte lokale Modellbetrieb verfuegbar ist
  - der technische `Text-Service-Test` bleibt getrennt im Experten-/Testbereich und darf weiter technischer formuliert sein
- bewusst noch nicht Teil von V8.3:
  - kein Chatverlauf
  - kein Streaming
  - keine neue Text-UI ausserhalb des bestehenden Basispfads

### V8.4 Text-KI-Nutzersprache und Leithinweise beruhigen
- der Basismodus fuehrt den sichtbaren Text-KI-Pfad jetzt ruhiger und klarer durch die naechsten Schritte
- real umgesetzt:
  - nutzernaehere Beschriftungen wie `Dein Text` und `Antwort holen`
  - klarere Leithinweise fuer die Zustaende `Text fehlt`, `bereit`, `Antwort wird erzeugt`, `Antwort ist fertig`, `nicht verfuegbar`
  - kuerzere Zweithinweise wie `Gib deinen Text ein und starte dann` oder `Du kannst jetzt direkt den naechsten Text eingeben`
  - keine Stub-/Runner-/JSON-Sprache im sichtbaren Basispfad fuer normale Nutzer
- bewusst noch nicht Teil von V8.4:
  - kein Chatverlauf
  - kein Streaming
  - kein weiterer Design-Umbau

### V8.5 Text-KI im Basispfad ruhiger und brauchbarer machen
- der sichtbare Text-KI-Pfad nutzt jetzt denselben echten lokalen Runner, aber mit engeren Defaults und kleinen Guardrails gegen Wiederholungs- und Ausufermuster
- real umgesetzt:
  - Bildprompt-Hilfe wird kuerzer und fokussierter beantwortet
  - kurze Umformulierungen und kurze Einzelantworten bleiben deutlich kompakter
  - offensichtlicher Wiederholungsmuell wird nicht mehr einfach roh in den Basispfad durchgereicht
- ehrliche Restgrenze:
  - der Basispfad ist jetzt brauchbarer, aber das aktuelle kleine lokale Modell bleibt bei Wissensthemen und feiner Sprachqualitaet sichtbar begrenzt
  - der Basismodus verkauft das nicht als grosse Chat-KI, sondern bleibt bei einer knappen lokalen Text-Hilfe

### V8.6 Text-KI auf genau ein staerkeres lokales Modell ziehen
- der sichtbare Text-KI-Pfad laeuft jetzt weiter ueber denselben lokalen Dienst, aber auf genau einem staerkeren Modell:
  - `Qwen2.5-7B-Instruct GGUF`
- real umgesetzt:
  - kein Mehrmodellbetrieb im sichtbaren Produktpfad
  - der Basispfad nutzt weiter denselben einfachen Einzelprompt-Weg
  - Antworten fallen sichtbar brauchbarer aus als mit dem alten 0.5B-Modell
- bewusst weiterhin nicht Teil des sichtbaren Textpfads:
  - kein Chatverlauf
  - kein Streaming
  - keine Modellwahl im UI

### V12.4 Spracheingabe und klarere Bildfehler
- relevante Prompt-Felder im sichtbaren Nutzerpfad koennen jetzt direkt per Spracheingabe befuellt werden
- real umgesetzt:
  - pro sichtbarem Prompt-Feld gibt es einen kleinen ruhigen Startpunkt fuer Spracheingabe
  - das Diktat landet nur im gerade gewaehlten Feld und bleibt damit feldsauber
  - Bildfehler zeigen fuer normale Nutzer jetzt kurze Ursachen wie fehlendes Bild, fehlende Maske oder nicht erreichbare Bild-Engine statt nur einer generischen Blockmeldung

### V10.1 V6.1 als gefuehrten Basispfad hochziehen
- `Dieselbe Person neu erzeugen` endet im Basismodus nicht mehr nur im Experten-Hinweis, sondern fuehrt direkt ueber denselben stabilen V6.1-Pfad
- real umgesetzt:
  - Basismodus zeigt fuer diese Aufgabe nur noch Referenzbild, kurze Schrittfuehrung, Prompt, klaren Startpunkt und direktes Ergebnis
  - derselbe V6.1-Readiness- und Generate-Endpunkt bleibt im Hintergrund aktiv; es gibt keine zweite Pipeline
  - der Expertenbereich behaelt den technischen V6.1-Zugang unveraendert
  - technische Hinweise, Metadaten und Testsprache bleiben aus dem sichtbaren Normalnutzerpfad heraus
- bewusst noch nicht Teil von V10.1:
  - kein V6.2- oder V6.3-Hochziehen in den Basismodus
  - kein weiterer Expertenabbau

### V10.2 V6.2 als gefuehrten Basismodus-Pfad hochziehen
- `Mehrere Referenzbilder nutzen` fuehrt im Basismodus jetzt direkt ueber denselben stabilen V6.2-Pfad statt nur in den Expertenbereich
- real umgesetzt:
  - Basismodus zeigt fuer diese Aufgabe nur noch bis zu drei Referenzbilder, ruhige Slot-Hinweise, Prompt, klaren Startpunkt und das Ergebnis
  - derselbe V6.2-Store, dieselbe Readiness und derselbe Generate-Endpunkt bleiben im Hintergrund aktiv; es gibt keine zweite Pipeline
  - der Expertenbereich behaelt den technischen V6.2-Zugang unveraendert
  - gleiche Funktion, zwei Bedienebenen: Basismodus gefuehrt, Expertenmodus direkt
- bewusst noch nicht Teil von V10.2:
  - kein V6.3-Hochziehen in den Basismodus
  - kein weiterer Expertenabbau ausserhalb des klaren V6.2-Nutzerpfads

### V10.3 V6.3 als gefuehrten Basismodus-Pfad hochziehen
- `Kopf/Gesicht auf Zielbild uebertragen` fuehrt im Basismodus jetzt direkt ueber denselben stabilen V6.3-Pfad statt nur in den Expertenbereich
- real umgesetzt:
  - Basismodus zeigt fuer diese Aufgabe nur noch Kopf-Referenzbild, Zielbild, kurze Schrittfuehrung, Prompt, klaren Startpunkt und das Ergebnis
  - optionale Rollen `Pose-Referenz` und `Transfer-Maske` bleiben sichtbar, aber klar als Zusatzmaterial und nicht als Pflicht
  - derselbe V6.3-Rollenstore, dieselbe Readiness und derselbe Generate-Endpunkt bleiben im Hintergrund aktiv; es gibt keine zweite Pipeline
  - der Expertenbereich behaelt den technischen V6.3-Zugang unveraendert
  - gleiche Funktion, zwei Bedienebenen: Basismodus gefuehrt, Expertenmodus direkt
- bewusst noch nicht Teil von V10.3:
  - keine neue Transfer-Logik
  - keine staerkere Aktivnutzung optionaler Rollen im stabilen Basispfad

### V10.4 Basismodus-Vollstaendigkeit und Produkt-Stopp vorbereiten
- der sichtbare Basismodus wurde einmal komplett gegen alle sieben Hauptaufgaben geprueft:
  - `Text schreiben / Text-KI nutzen`
  - `Neues Bild erstellen`
  - `Bild veraendern`
  - `Bereich im Bild aendern`
  - `Dieselbe Person neu erzeugen`
  - `Mehrere Referenzbilder nutzen`
  - `Kopf/Gesicht auf Zielbild uebertragen`
- realer Audit-Stand:
  - alle sieben Aufgaben haben jetzt im Basismodus klaren Einstieg, passende Eingaben, klaren Startpunkt und eine sichtbare Ergebnisbindung
  - fuer V6.1, V6.2 und V6.3 bleibt der Expertenbereich nur noch die technische Zusatzebene, nicht mehr der notwendige Bedienweg
  - eine kleine Restkante im V6.1-Pending-Zustand wurde geglaettet, damit `Funktion wird geprueft...` nicht als falsches `nicht verfuegbar` erscheint
- bewusst nach V10.4 kein neuer Produktblock:
  - Expertenbereich bleibt fuer technische Direktnutzung erhalten
  - spaetere Arbeit ist jetzt eher Wunsch-/Qualitaetsausbau als fehlende Hauptnutzbarkeit

### V11.5 Einfache Bildwelt-Wahl fuer normale Nutzer
- normale Nutzer koennen im Basismodus fuer die allgemeinen Bildaufgaben jetzt einfach zwischen zwei Bildwelten waehlen:
  - `Foto`
  - `Anime`
- real umgesetzt:
  - der sichtbare Schalter erscheint nur bei `Neues Bild erstellen`, `Bild veraendern` und `Bereich im Bild aendern`
  - normale Nutzer sehen keine Checkpointnamen, sondern nur die einfache Wahl der Bildwelt
  - intern nutzt der Basismodus nur die zwei festen Standards `photo_standard` und `anime_standard`
- bewusst weiterhin nicht Teil von V11.5:
  - kein Modellschalter fuer `V6.1`, `V6.2` oder `V6.3`
  - kein freier Experten- oder Checkpoint-Schalter im Basismodus

### V11.6 Begrenzung des Bildwelt-Schalters
- die sichtbare Bildwelt-Wahl bleibt fuer normale Nutzer bewusst eng und ruhig.
- real festgezogen:
  - `Neues Bild erstellen`, `Bild veraendern` und `Bereich im Bild aendern` behalten den einfachen Schalter `Foto | Anime`
  - `Dieselbe Person neu erzeugen` bleibt der einzige fortgeschrittene Pfad, fuer den spaeter ein ebenso enger Schalter sinnvoll sein kann
  - `Mehrere Referenzbilder nutzen` und `Kopf/Gesicht auf Zielbild uebertragen` bleiben bewusst bei festen Foto-Defaults
- Grundlinie:
  - Basismodus nur dort mit Bildwelt-Wahl erweitern, wo der Nutzwert den zusaetzlichen Komplexitaetspreis klar rechtfertigt

### V11.7 V6.1 Mit Vereinfachter Bildwelt-Wahl
- `Dieselbe Person neu erzeugen` hat im Basismodus jetzt einen kleinen Schalter `Foto | Anime`
- reale Umsetzung:
  - keine Checkpointnamen im sichtbaren Nutzerpfad
  - intern nutzt der Basispfad nur `photo_standard` oder `anime_standard`
  - der Expertenpfad bleibt technisch separat
- die sichtbaren Bildwelt-Texte wurden danach noch einmal fuer normale Nutzer nachgezogen:
  - `Foto` klarer fuer realistische Bilder und natuerliche Gesichter
  - `Anime` klarer fuer stilisierte Figuren und Anime-Look
- bewusst weiterhin nicht Teil von V11.7:
  - kein Bildwelt-Schalter fuer `V6.2`
  - kein Bildwelt-Schalter fuer `V6.3`

### V8.7 Text-KI Antwortqualitaet Nachgeschaerft
- der sichtbare Text-KI-Basispfad bleibt optisch ruhig, antwortet aber im aktuellen 7B-Stand jetzt knapper und klarer
- realer Fokus:
  - brauchbarere Bildprompt-Hilfe
  - rundere kurze Umformulierungen
  - weniger Abschweifen bei kurzen Antworten
- bewusst weiter ehrlich:
  - bei kurzen Wissensfragen bleibt die Modellqualitaet sichtbar begrenzt

### V12.2 Konsistente Upload-Vorschauen
- ueberall dort, wo im sichtbaren Produkt Bilder geladen werden, erscheint jetzt eine kleine Vorschau des aktuell aktiven Bildes direkt an der passenden Upload-Stelle
- real umgesetzt:
  - Basismodus und Expertenbereich nutzen dieselbe ruhige Preview-Logik
  - Eingabebild, Maske, V6.1-Referenzbild, V6.2-Slots und V6.3-Rollen zeigen das aktive Bild sichtbar an
  - im V6.3-Pfad bleibt die Vorschau zwischen Rollenbereich und technischem Testbereich synchron
  - beim Ersetzen springt die Vorschau auf das neue Bild, beim Reset verschwindet sie sauber
- bewusst kein Ausbau in V12.2:
  - keine neue Bildpipeline
  - keine neue Produktlogik, nur sichtbare Bestaetigung des aktiven Upload-Zustands
