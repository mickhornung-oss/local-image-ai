# V9 Visuelle Qualitaets-/Layout-Architektur

## Ist-Zustand
- Die Produktstruktur ist bereits sauber getrennt:
  - `Basismodus`
  - `Experten-/Testbereich`
  - `Aktuelles Ergebnis`
  - `Letzte Ergebnisse`
- Die Seite nutzt heute schon Karten und Abschnittsrahmen, wirkt aber noch wie ein technischer Arbeitsstand.
- Der Basismodus fuehrt inhaltlich besser als frueher, visuell ist die Hierarchie aber noch nicht ruhig genug.
- Der Expertenbereich ist funktional getrennt, wirkt aber noch zu stark wie mehrere lose Technikblöcke statt wie ein klar gegliederter Arbeitsbereich.

## Reale UI-Schwaechen
- Zu viele gleich starke Flaechen konkurrieren noch sichtbar miteinander.
- Karten, Hinweiszonen und Aktionen haben noch nicht ueberall dieselbe visuelle Rangordnung.
- Der Basismodus wirkt strukturell klarer als frueher, aber noch nicht hochwertig genug verdichtet.
- Der Expertenbereich ist technisch praezise, aber visuell noch zu flach gegliedert.
- Status und Hinweise sitzen noch nicht ueberall an genau derselben logischen Stelle.
- Abstaende, Innenabstaende und Button-Gewichte sind noch nicht konsequent genug abgestuft.

## Gepruefte Varianten

### A. Leichte optische Bereinigung auf bestehender Struktur
- Vorteil:
  - kleinster Eingriff
  - geringstes CSS-Risiko
- Nachteil:
  - sichtbare Grundruhe verbessert sich nur begrenzt
  - bestehende Kartenhierarchie bleibt zu schwach
  - Expertenbereich wuerde weiter wie ein Technikstapel wirken
- Urteil:
  - zu klein fuer den naechsten echten Qualitaetssprung

### B. Klar card-basierte Layoutsprache mit ruhiger Sektionierung
- Vorteil:
  - passt auf den bestehenden Basismodus und Expertenbereich
  - schafft klare Haupt- und Unterhierarchien ohne neuen Navigationsumbau
  - Ergebnisse, Hinweise und Aktionen lassen sich sauber in definierte Kartenrollen bringen
  - spaeter gut skalierbar fuer weitere Pfade
- Nachteil:
  - braucht disziplinierte visuelle Regeln statt punktueller Einzelfixes
- Urteil:
  - beste Richtung fuer dieses Repo

### C. Staerker dashboard-artige Struktur mit vielen parallelen Zonen
- Vorteil:
  - viele Infos gleichzeitig sichtbar
  - fuer Power-User auf den ersten Blick dicht
- Nachteil:
  - zu viel Parallelitaet fuer normale Nutzer
  - hohes Risiko eines neuen Cockpit-Gefuehls
  - wuerde Basismodus und Expertenlogik visuell wieder zu nah zusammenziehen
- Urteil:
  - fuer dieses Produkt derzeit die falsche Richtung

## Empfohlene visuelle Richtung
- V9 soll Variante B nutzen:
  - ruhige card-basierte Layoutsprache
  - klare Sektionierung
  - sichtbare Primär-/Sekundärhierarchie
  - klare Trennung zwischen Basismodus und Experten-/Testbereich

## Zielbild

### Basismodus
- Eine klare Hauptspur:
  - Aufgabenkopf
  - gefuehrte Eingabekarte
  - aktuelles Ergebnis
  - kompakter Verlauf
- Nur eine primaere Arbeitskarte soll optisch dominieren.
- Hinweise und Status stehen direkt an der Arbeitskarte, nicht verteilt.
- Sekundaere Informationen treten sichtbar zurueck.

### Experten-/Testbereich
- Eigene technische Arbeitsflaeche mit klar getrennten Pfadkarten.
- Jede Expertenkarte hat dieselbe innere Ordnung:
  - Titel
  - Kurzbeschreibung
  - Eingaben
  - Readiness/Status
  - Startaktion
  - Ergebnis/Fehler
- Technisch praezise, aber visuell sauber gruppiert statt wie lose Panels.

### Ergebnisdarstellung
- `Aktuelles Ergebnis` bleibt die visuell staerkste Rueckmeldung nach einem Lauf.
- `Letzte Ergebnisse` bleibt kompakter und ruhiger als Verlauf.
- Vorschau und Metadaten werden klar getrennt:
  - Bild zuerst
  - knappe Zusatzinfos danach

## Gestaltungsregeln

### Kartenhierarchie
- `Level 1`:
  - Basismodus-Kopf
  - aktive Arbeitskarte
  - aktuelles Ergebnis
- `Level 2`:
  - Eingabekarten
  - Expertenpfadkarten
  - Verlaufskarten
- `Level 3`:
  - Status-/Hinweiszonen
  - Metadaten
  - Hilfstexte

### Abschnittstitel
- kurze klare Titel
- ein kurzer Unterhinweis pro Abschnitt
- kein Titelgewitter innerhalb einer einzelnen Karte

### Abstaende und Innenabstaende
- zwischen Hauptsektionen sichtbar mehr Luft als zwischen Elementen innerhalb einer Karte
- Karten innen kompakt, aber nicht gedrungen
- Status und Aktionen sollen an festen, wiederkehrenden Positionen sitzen

### Button-Hierarchie
- genau eine primaere Aktion pro Karte
- sekundaere Aktionen sichtbar rueckgenommen
- Reset/Loeschen nie gleich stark wie Start/Generieren

### Status-/Hinweisplatzierung
- genau eine primaere Hinweiszeile pro aktiver Arbeitskarte
- zusaetzliche Hinweise kleiner und visuell nachgeordnet
- kein separater Statusstapel mit gleich gewichteten Meldungen

### Vorschau-/Ergebnisbloecke
- Bildflaechen gross genug fuer klares Lesen
- Ergebnisbild klarer als Metadaten
- Verlaufskarten kompakter als das aktuelle Ergebnis

## Sichtbar ruhig, bewusst zurueckgenommen
- ruhig und prominent:
  - aktive Aufgabe
  - relevante Eingabe
  - primaerer Startbutton
  - aktuelles Ergebnis
- bewusst zurueckgenommen:
  - technische Readiness-Details
  - Nebenzustaende
  - Sekundaeraktionen
  - Expertenpfade im Basismodus

## No-Gos
- Kein UI-Gewimmel mit gleich starken Karten.
- Kein halb offenes Technikpanel im Basismodus.
- Keine unklaren Startpunkte.
- Keine widerspruechlichen Statuszonen.
- Keine visuell gleichwertigen Primaer- und Sekundaeraktionen.
- Keine Vermischung von Normalnutzung und Testlogik in derselben optischen Ebene.
- Kein Dashboard mit dauerhaft gleichzeitigen Parallelzonen fuer alles.

## Enger Ausbaupfad

### V9.2 Basismodus visuell auf die Layoutsprache ziehen
- aktive Arbeitskarte visuell staerken
- Nebenkarten ruhiger machen
- Ergebnis- und Verlaufskarten sauber abstufen
- real umgesetzt:
  - Basismodus nutzt jetzt sichtbare `basic-surface`-Karten fuer Einstieg, aktive Aufgabe, Arbeitsflaechen, aktuelles Ergebnis und Verlauf
  - Aufgabenwahl, Leithinweise, Eingabekarten und Ergebnisbereiche folgen jetzt einer ruhigeren Card-Hierarchie mit konsistenteren Abstaenden
  - primaere Aktionen wie `Generieren` und `Antwort holen` sind sichtbar staerker als sekundaere Upload-/Reset-Aktionen
  - Status- und Hinweiszonen sitzen ruhiger in den Arbeitskarten statt wie lose Technikzeilen
  - der Experten-/Testbereich wurde in diesem Schritt bewusst nicht auf dieselbe Layoutsprache umgezogen

### V9.3 Experten-/Testbereich visuell harmonisieren
- einheitliche Expertenpfadkarten
- konsistente Status- und Aktionszonen
- technische Dichte erhalten, aber sauberer gliedern
- real umgesetzt:
  - Experten-/Testbereich nutzt jetzt dieselbe ruhige Card-Sprache wie der Basismodus, aber in einer technischeren Farbfassung
  - `Text-Service-Test`, `V6.1`, `V6.2` und `V6.3` sind visuell als eigene Pfadkarten mit klaren Status-, Eingabe-, Start- und Ergebniszonen getrennt
  - primaere Startbuttons sind pro Expertenpfad sichtbar priorisiert, Upload- und Reset-Aktionen bleiben nachrangig
  - der Basismodus wurde dabei bewusst nicht wieder technischer gezogen

### V9.4 Ergebnis- und Verlaufssprache angleichen
- aktuelles Ergebnis visuell fuehren
- Verlauf kompakt halten
- Download und Zusatzinfos ruhiger einordnen
- real umgesetzt:
  - `Text schreiben / Text-KI nutzen` steht im Basismodus jetzt bewusst an erster Stelle und ist auch der logische Default-Einstieg
  - sichtbare Benennungen wurden auf eine ruhigere, konsistentere Begriffswelt gezogen, besonders bei `Text`, `Referenzbild`, `Zielbild`, `Maske` und `Ergebnis`
  - Basis- und Expertenbereich folgen jetzt derselben Karten-, Button- und Statuslogik, ohne visuell miteinander zu verschwimmen
  - kleine Restbrueche wie gemischte Titelsprachen und einzelne technische Altbegriffe wurden bereinigt

### V9.5 Expertenmodus nachschaerfen und Oberfläche heller ziehen
- Expertenkarten intern klarer ordnen
- Helligkeit und Lesbarkeit moderat anheben
- keine Funktionsaenderung
- real umgesetzt:
  - Basis- und Expertenbereich wurden sichtbar, aber kontrolliert heller gezogen, ohne die dunkle Produktanmutung zu verlieren
  - Kartenkanten, Eingabeflaechen, Sekundaertexte und Hinweiszonen sind lesbarer und ruhiger getrennt
  - der Expertenbereich nutzt jetzt staerker getrennte Input-/Run-/Output-Karten innerhalb der bestehenden technischen Pfade
  - Primaer-Startpunkte pro Expertenpfad bleiben sofort erkennbar, waehrend Upload-/Reset-Aktionen bewusst nachrangig bleiben

### V9.6 Letzter Mikro-Feinschliff
- nur kleine Restbrueche glatten
- keine Funktionsaenderung
- real umgesetzt:
  - Einstieg, Arbeitskarten, Ergebnisbereich und Verlauf folgen jetzt im Basismodus noch konsequenter derselben ruhigen Innenabstands- und Hinweislogik
  - der Expertenbereich ist intern etwas klarer auf Eingabe, Status und Ergebnis ausgerichtet, ohne neue Struktur oder neue Logik
  - sichtbare Restbrueche bei Statusboxen, Ergebniskarten und Kartenunterordnung wurden nur noch fein geglaettet

### V9.7 Oberflaeche heller und freundlicher ziehen
- nur Helligkeit, Lesbarkeit und Feinwirkung nachziehen
- keine Funktionsaenderung
- real umgesetzt:
  - Seitenhintergruende, Kartenflaechen und Eingabebereiche wurden kontrolliert heller gezogen, ohne die dunkle Grundwelt zu verlassen
  - Kartenränder, Trenner und Sekundaertexte sind jetzt etwas klarer lesbar und wirken weniger bunkerartig
  - Basismodus bleibt ruhig und freundlich, waehrend der Expertenbereich dieselbe Lesbarkeitsverbesserung in einer weiter technischen Warmton-Fassung nutzt
