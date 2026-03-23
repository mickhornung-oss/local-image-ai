## V11.1 Bildmodell-Audit

### Ist-Stand
- Der aktuelle Produktivpfad nutzt einen einzelnen SDXL-Checkpoint:
  - `vendor/ComfyUI/models/checkpoints/sdxl-base.safetensors`
- Der bestehende lokale Stack ist real gruen fuer:
  - txt2img
  - img2img
  - Inpainting
  - V6.1 Identity Reference
  - V6.2 Multi-Reference
  - V6.3 Identity Transfer
- Der aktuelle Pfad ist robust, aber qualitativ sichtbar begrenzt:
  - gute allgemeine SDXL-Basis
  - keine Spezialisierung auf Photorealismus
  - keine Spezialisierung auf Anime
  - Gesichter und allgemeine Bildruhe bleiben unterhalb typischer spezialisierter Fine-Tunes

### Genau Zwei Kandidaten

#### Standard-/Foto-Kandidat
- `SG161222/RealVisXL_V5.0`
- Rolle im Projekt:
  - genau ein Fotopfad fuer realistischere Personen-, Portrait- und Alltagsszenen
- Warum genau dieser Kandidat:
  - explizit auf Photorealismus ausgerichtet
  - weiterhin SDXL
  - als einzelnes `.safetensors` realistisch in denselben ComfyUI-Checkpoint-Pfad integrierbar
  - kein neuer Engine- oder Node-Block noetig

#### Anime-Kandidat
- `cagliostrolab/animagine-xl-4.0`
- Rolle im Projekt:
  - genau ein Anime-Pfad fuer stilisierte Charaktere und saubere Anime-Kompositionen
- Warum genau dieser Kandidat:
  - explizit anime-spezifischer SDXL-Fine-Tune
  - laut Model Card direkt fuer ComfyUI nutzbar
  - als einzelnes `.safetensors` realistisch in denselben Checkpoint-Pfad integrierbar
  - kein neuer Engine- oder Node-Block noetig

### Warum Genau Diese Zwei
- Beide Kandidaten bleiben innerhalb derselben technischen Familie wie der aktuelle Produktivpfad:
  - SDXL-Checkpoint
  - ComfyUI `CheckpointLoaderSimple`
  - bestehende Render-, img2img-, Inpainting- und Identity-Pfade muessen dafuer nicht neu erfunden werden
- Beide Kandidaten vermeiden absichtlich einen groesseren Integrationskrieg:
  - kein FLUX-Pfad
  - kein SD3-/Pony-Sonderpfad
  - keine neuen Pflicht-Nodes
  - kein neuer Frontend-Modellschalter in diesem Schritt

### Integrationsrisiko

#### RealVisXL V5.0
- Stack-Fit:
  - hoch
- Lokale Realistik:
  - hoch, weil Dateigroesse und SDXL-Familie nahe am aktuellen Produktivmodell liegen
- Hauptrisiko:
  - spaetere Parameterfeinabstimmung fuer das beste Photorealismus-Ergebnis
- Audit-Entscheidung:
  - sauberer Standard-/Foto-Kandidat

#### Animagine XL 4.0
- Stack-Fit:
  - hoch
- Lokale Realistik:
  - hoch, weil ebenfalls SDXL-basiert und direkt fuer ComfyUI dokumentiert
- Hauptrisiko:
  - Prompting ist tag-orientierter als beim allgemeinen SDXL-Basispfad
- Audit-Entscheidung:
  - sauberer Anime-Kandidat

### Vergleichsplan Fuer Den Naechsten Block
- Baseline:
  - aktuelles `sdxl-base.safetensors`
- Vergleichskandidaten:
  - `RealVisXL_V5.0`
  - `animagine-xl-4.0`
- Pro Modell genau drei kurze Prompt-Kategorien:
  - Portrait / Gesicht
  - Ganzkoerper / Figur in Szene
  - Umgebung / Komposition
- Bewertungskriterien:
  - Prompttreue
  - Gesichter
  - allgemeine Bildruhe
  - Stilqualitaet
  - praktische Nutzbarkeit im Projekt
- Anime-Kandidat wird mit passenden anime-typischen Prompts bewertet, aber gegen dieselben Kriterien

### Bewusst Noch Nicht Teil Von V11.1
- kein Modellwechsel
- kein Download
- kein Frontend-Modellschalter
- keine neue Pipeline
- keine FLUX-Integration
- keine Modellfamilien-Orgie

## V11.2 RealVisXL gegen SDXL Base 1.0

### Lokal Bereitgestellt
- `RealVisXL_V5.0_fp16.safetensors` liegt jetzt lokal unter:
  - `vendor/ComfyUI/models/checkpoints/RealVisXL_V5.0_fp16.safetensors`
- Der bestehende Produktivpfad bleibt bewusst unangetastet:
  - `sdxl-base.safetensors` bleibt der automatisch selektierte Default-Checkpoint
  - `RealVisXL` ist in V11.2 nur der lokale Vergleichskandidat

### Realer Vergleichsaufbau
- Baseline:
  - `sdxl-base.safetensors`
- Kandidat:
  - `RealVisXL_V5.0_fp16.safetensors`
- Gleiche Parameter fuer beide:
  - `1024x1024`
  - `steps=20`
  - `cfg=6.5`
  - gleiche Seeds pro Motiv
- Vergleichsmotive:
  - `portrait`
  - `street`
  - `cafe`

### Beobachtungen

#### Portrait / Gesicht
- `SDXL Base 1.0`
  - gutes Grundbild
  - Gesicht wirkt aber glatter und modellhafter
  - weniger natuerliche Haut- und Kleidungswirkung
- `RealVisXL V5.0`
  - sichtbar natuerlichere Hautstruktur
  - glaubhaftere Kleidung und Lichtwirkung
  - insgesamt klar staerkerer Photorealismus

#### Allgemeine Photoreal-Szene
- `SDXL Base 1.0`
  - starke Stimmung und Reflexionen
  - Figur bleibt aber weiter entfernt und weniger greifbar
- `RealVisXL V5.0`
  - Motiv ist klarer als reale Person lesbar
  - Strasse, Kleidung und Regenwirkung wirken geerdeter
  - bessere praktische Nutzbarkeit fuer Foto-/Alltagsszenen

#### Innen-/Außenszene
- `SDXL Base 1.0`
  - warm und atmosphaerisch
  - sichtbar staerkerer Glow-/Dream-Look
- `RealVisXL V5.0`
  - ruhigere Komposition
  - glaubhafteres Cafe-Interior
  - weniger weichgezeichnete, mehr alltagstaugliche Photowirkung

### Kurzes Fazit
- Prompttreue:
  - `RealVisXL` leicht bis klar besser
- Gesichter:
  - `RealVisXL` klar besser
- Photorealismus:
  - `RealVisXL` klar besser
- Bildruhe:
  - `RealVisXL` besser, weil weniger modellhaftes oder weichgegluehtes SDXL-Basisbild
- Laufzeit:
  - leicht hoeher, aber lokal noch praktikabel

### Entscheidung
- `RealVisXL V5.0` ist im aktuellen lokalen Stack ein ueberzeugender Standard-/Foto-Kandidat.
- Entscheidung fuer V11.2:
  - `besser`
  - als naechster Standardkandidat empfohlen
- Bewusst noch nicht getan:
  - kein stiller Rollout als neuer Produktiv-Default in diesem Schritt
  - kein Frontend-Modellschalter
  - keine zweite Modellfamilie

### Empfehlung Fuer Den Naechsten Schritt
- `RealVisXL V5.0` nicht mehr nur als Audit-Kandidat, sondern als enger Produktiv-Favorit weiter pruefen.
- Danach separat und genauso eng:
  - genau ein Anime-Kandidat `Animagine XL 4.0`

## V11.3 Animagine XL 4.0 gegen SDXL Base 1.0

### Lokal Bereitgestellt
- `animagine-xl-4.0-opt.safetensors` liegt jetzt lokal unter:
  - `vendor/ComfyUI/models/checkpoints/animagine-xl-4.0-opt.safetensors`
- Der bestehende Produktivpfad bleibt bewusst unangetastet:
  - `sdxl-base.safetensors` bleibt der automatisch selektierte Default-Checkpoint
  - `Animagine XL 4.0` ist in V11.3 nur der lokale Vergleichskandidat

### Realer Vergleichsaufbau
- Baseline:
  - `sdxl-base.safetensors`
- Kandidat:
  - `animagine-xl-4.0-opt.safetensors`
- Gleiche Parameter fuer beide:
  - `1024x1024`
  - `steps=20`
  - `cfg=6.5`
  - gleiche Seeds pro Motiv
- Vergleichsmotive:
  - `anime_portrait`
  - `fullbody_pose`
  - `stylized_scene`

### Beobachtungen

#### Anime-Portrait / Gesicht
- `SDXL Base 1.0`
  - liefert ein schoenes, sauberes Bild
  - wirkt aber eher weich gemalt als klar anime-spezifisch
  - Augen und Haarfuehrung sind gut, aber weniger stilpraegnant
- `Animagine XL 4.0`
  - klar staerkere Anime-Stiltreue
  - deutlich praegnantere Augen, Linien und Farbtrennung
  - insgesamt der ueberzeugendere Anime-Gesichtspfad

#### Ganzkoerper / Pose
- `SDXL Base 1.0`
  - erfuellt die Szene solide
  - bleibt aber in Pose, Outfit und Linien eher allgemein illustriert als wirklich anime-spezifisch
- `Animagine XL 4.0`
  - deutlich dynamischere Pose und klarere Figurensilhouette
  - staerkere Anime-Linien und besser lesbares Charakterdesign
  - leichte Tendenz zu stilistischer Eigenwilligkeit gegenueber der exakten Prompt-Literalitaet

#### Stilisierte Szene / Hintergrund
- `SDXL Base 1.0`
  - starke Farben und Stimmung
  - wirkt aber eher painterly und weniger wie ein sauberer Anime-Hintergrund
- `Animagine XL 4.0`
  - klarere Linien, staerkere Neon-Farbtrennung und insgesamt ruhigere Anime-Bildsprache
  - bessere Nutzbarkeit fuer stilisierte Anime-Szenen
  - Hintergrund wirkt stiltreuer, auch wenn einzelne Promptdetails freier interpretiert werden

### Kurzes Fazit
- Stiltreue:
  - `Animagine XL 4.0` klar besser
- Gesichter:
  - `Animagine XL 4.0` klar besser fuer Anime
- Anime-Qualitaet:
  - `Animagine XL 4.0` klar besser
- Farben / Linien / Bildruhe:
  - `Animagine XL 4.0` besser, weil die Bilder klarer getrennt, sauberer und stilistisch geschlossener wirken
- Laufzeit:
  - praktisch gleichwertig bis leicht langsamer, lokal aber sauber nutzbar
- Restgrenze:
  - `Animagine XL 4.0` ist tag-orientierter als der Basispfad und kann Promptdetails freier umformen

### Entscheidung
- `Animagine XL 4.0` ist im aktuellen lokalen Stack ein ueberzeugender Anime-Kandidat.
- Entscheidung fuer V11.3:
  - `besser`
  - als fester Anime-Standardkandidat empfohlen
- Bewusst noch nicht getan:
  - keine aktive Default-Umschaltung
  - kein Frontend-Modellschalter
  - keine neue Pipeline

### Empfehlung Fuer Den Naechsten Schritt
- `Animagine XL 4.0` zusammen mit `RealVisXL V5.0` als zwei bewusste Bildstandards bewerten:
  - ein Standard-/Fotopfad
  - ein Anime-Pfad
- Danach erst entscheiden:
  - ob ein einfacher Modellschalter sinnvoll ist

## V11.4 Zwei Feste Bildstandards und spaetere Schalterlogik

### Entscheidung
- Die zwei festen Bildstandards sind jetzt bewusst festgezogen:
  - `photo_standard -> RealVisXL_V5.0_fp16.safetensors`
  - `anime_standard -> animagine-xl-4.0-opt.safetensors`
- `sdxl-base.safetensors` bleibt bewusst erhalten:
  - als Bestandsmodell
  - als Kompatibilitaets- und Fallback-Checkpoint
  - aber nicht mehr als bester Standard fuer Foto oder Anime

### Warum Kein Stiller Globaler Default-Switch In V11.4
- Ein globales Umschalten des einen automatischen Produktiv-Defaults wuerde nicht nur den Hauptpfad beruehren, sondern auch die bestehenden stabilen SDXL-basierten Pfade indirekt mitziehen.
- In V11.4 wurde deshalb bewusst nicht ueber Dateisortierung oder einen stillen globalen Default-Trick umgestellt.
- Stattdessen ist jetzt der spaetere saubere Wahlschnitt vorbereitet:
  - `photo_standard`
  - `anime_standard`

### Technische Vorbereitung Fuer Einen Spaeteren Einfachen Schalter
- Die interne Checkpoint-Aufloesung akzeptiert jetzt zwei feste Alias-Modi:
  - `photo_standard`
  - `anime_standard`
- Diese Modi zeigen stabil genau auf:
  - `RealVisXL_V5.0_fp16.safetensors`
  - `animagine-xl-4.0-opt.safetensors`
- Der spaetere einfache Nutzer-Schalter soll deshalb nur noch zwei klare Begriffe abbilden:
  - `Foto`
  - `Anime`
- Bewusst noch nicht getan:
  - kein Frontend-Modellschalter
  - keine freie Checkpoint-Liste fuer normale Nutzer
  - kein Modellzoo

### Empfehlung Fuer Den Naechsten Schritt
- Wenn ein sichtbarer Schalter sinnvoll wird, dann nur in dieser engen Form:
  - `Foto -> photo_standard`
  - `Anime -> anime_standard`
- Der bestehende `sdxl-base.safetensors`-Pfad bleibt als Fallback erhalten, aber nicht als neue Standardempfehlung.

## V11.5 Einfacher Bildwelt-Schalter im Basismodus

### Ausgerollter Nutzerschnitt
- Normale Nutzer koennen im Basismodus jetzt fuer die allgemeinen Bildaufgaben direkt zwischen zwei Bildwelten waehlen:
  - `Foto`
  - `Anime`
- Der Schalter bleibt bewusst eng:
  - keine Checkpointnamen
  - keine freie Modellliste
  - keine Modell-Orgie

### Interne Bindung
- Der sichtbare Schalter nutzt nur die bereits vorbereiteten festen Standardmodi:
  - `Foto -> photo_standard -> RealVisXL_V5.0_fp16.safetensors`
  - `Anime -> anime_standard -> animagine-xl-4.0-opt.safetensors`
- Die bestehende direkte Checkpoint-Logik bleibt erhalten.

### Sichtbarer Geltungsbereich
- Der Schalter gilt im Basismodus nur fuer die allgemeinen Bildaufgaben:
  - `Neues Bild erstellen`
  - `Bild veraendern`
  - `Bereich im Bild aendern`
- Bewusst nicht Teil von V11.5:
  - `V6.1`
  - `V6.2`
  - `V6.3`
  - Expertenbereich

### Realer Stand
- Echte Basismodus-Laeufe wurden mit beiden Bildwelten bestaetigt:
  - `Foto` nutzt im Ergebnisstore `checkpoint=photo_standard`
  - `Anime` nutzt im Ergebnisstore `checkpoint=anime_standard`
- Der Produktiv-Default bleibt weiterhin bewusst kontrolliert und wird nicht still ueber Dateisortierung umgelegt.

## V11.6 Bildwelt-Policy fuer fortgeschrittene Pfade

### Entscheidungslinie
- Die Bildwelt-Wahl bleibt fuer normale Nutzer bewusst eng.
- Fuer die drei fortgeschrittenen Pfade gilt jetzt diese verbindliche Linie:
  - `V6.1 Single-Reference`:
    - spaeterer vereinfachter Bildwelt-Schalter sinnvoll
  - `V6.2 Multi-Reference`:
    - fester Default besser
  - `V6.3 Transfer`:
    - fester Default besser

### V6.1 Single-Reference
- Entscheidung:
  - spaeterer vereinfachter Schalter `Foto | Anime` ist hier sinnvoll
- Warum:
  - der Nutzerpfad bleibt trotz Referenzbild noch relativ einfach
  - der kreative Nutzwert eines klaren Stilwechsels ist hier am hoechsten
  - die Komplexitaet steigt nur moderat, wenn der Schalter eng bleibt
- Enger Rahmen fuer spaeter:
  - `Foto -> photo_standard`
  - `Anime -> anime_standard`
- Bis zu einem eigenen Qualitaetsblock bleibt der aktuelle einfache Default ausreichend.

### V6.2 Multi-Reference
- Entscheidung:
  - fester Default besser
- Logischer Default:
  - `photo_standard`
- Warum:
  - der Pfad ist bereits durch mehrere Referenzbilder und Slot-Logik komplex genug
  - ein weiterer Stil-Schalter wuerde normale Nutzer schneller ueberladen
  - die Hauptaufgabe hier ist Identitaetskonsistenz, nicht Stilwechsel
  - Anime bleibt hier eher Spezialfall als breiter Normalnutzerbedarf

### V6.3 Transfer
- Entscheidung:
  - fester Default besser
- Logischer Default:
  - `photo_standard`
- Warum:
  - der Pfad ist technisch am staerksten an reale Kopf-/Zielbild-Konsistenz gebunden
  - ein sichtbarer Stil-Schalter wuerde leicht falsche Erwartungen an den Transferpfad erzeugen
  - Anime waere hier eher ein eigener spaeterer Spezialfall als ein sauberer Alltagsmodus

### Praktische Folgerung
- Fuer normale Nutzer bleibt die sichtbare Bildwelt-Wahl deshalb bewusst auf die drei allgemeinen Bildaufgaben begrenzt.
- Falls spaeter genau ein fortgeschrittener Pfad nachgezogen wird, dann zuerst:
  - `V6.1 Single-Reference`
- `V6.2` und `V6.3` bleiben bis auf Weiteres bewusst bei einem festen Foto-Default.

## V11.7 V6.1-Bildwelt-Schalter nicht sauber ausrollbar

### Gepruefter Kandidat
- Der naechste enge Ausbaupfad waere `V6.1 Single-Reference` mit einem vereinfachten Schalter:
  - `Foto -> photo_standard`
  - `Anime -> anime_standard`

### Echter Blocker
- Der Rollout wurde bewusst nicht ausgerollt.
- Grund:
  - der aktuelle V6.1-Renderpfad lieferte in der realen Pruefung mit einem sauberen Referenzbild keine ehrlich brauchbaren Ergebnisse
  - das galt nicht nur fuer `photo_standard` und `anime_standard`, sondern auch im Gegencheck fuer `sdxl-base.safetensors`
- Beobachtetes Muster:
  - technisch erfolgreiche Completion
  - aber visuell unbrauchbare, farbzerfallene Gesichter statt einer stabilen neuen Personenvariante

### Entscheidung Fuer V11.7
- Kein sichtbarer V6.1-Bildwelt-Schalter im Repo.
- Keine halbfertige UI-Freischaltung.
- Erst wenn der zugrunde liegende V6.1-Qualitaetsblock sauber geklaert ist, ist ein ehrlicher `Foto | Anime`-Rollout vertretbar.

## V11.8 V6.1-Qualitaetsblocker isoliert

### Reproduzierbarer Minimalfall
- Referenzbild:
  - `reference-20260315014724-066ae2c3`
- Prompt:
  - `same person, realistic portrait, natural window light, detailed eyes, calm expression`
- Fester Seed:
  - `123456789`
- Checkpoint fuer die Isolationspruefung:
  - `sdxl-base.safetensors`

### Hauptursache
- Der eigentliche Qualitaetskiller lag nicht primaer an Modellwahl oder Referenz-Staging, sondern an der im V6.1-Workflow hinterlegten Sampler-Kombination:
  - `sampler_name = ddpm`
  - `scheduler = karras`
- Diese Kombination erzeugte im reproduzierbaren Minimalfall bereits ohne wirksames Identity-Conditioning unbrauchbare Muster- und Farbzerfall-Bilder.

### Enge Isolationskette
- Baseline mit bestehendem V6.1-Workflow:
  - visuell kaputt
- Gegenprobe ohne `ApplyInstantID`, aber weiter mit `ddpm + karras`:
  - weiter visuell kaputt
- Gegenprobe ohne `ApplyInstantID`, aber mit `euler + normal`:
  - normales, brauchbares SDXL-Portrait
- Schluss:
  - Hauptursache sitzt im Sampler-/Scheduler-Paar, nicht in VAE, Referenz-Staging oder der reinen Checkpoint-Wahl

### Minimaler Fix
- Im echten V6.1-Workflow wurde genau ein enger Fix gesetzt:
  - `sampler_name: ddpm -> euler`
  - `scheduler: karras -> normal`
- Keine weitere Pipeline-Aenderung
- Keine UI-Aenderung

### Ergebnis
- Der reale V6.1-Produktlauf liefert jetzt wieder brauchbare Bilder statt farbzerfallener Muster:
  - `result-20260315041753-f4999b33`
- V11.7 ist damit nicht automatisch ausgerollt, aber der zugrunde liegende V6.1-Hauptblocker ist sauber behoben.

### Bewusst Nicht Teil Von V11.8
- kein V11.7-Rollout
- keine V6.2-/V6.3-Aenderung in diesem Schritt
- kein weiterer Parameter-Tuning-Block

## V11.7 Nach V11.8 Erneut Geprueft

### Ergebnis
- Der sichtbare V11.7-Rollout bleibt weiter bewusst gesperrt.
- Grund:
  - `Foto` ist auf dem reparierten V6.1-Pfad jetzt wieder brauchbar
  - `Anime` laeuft technisch bis Completion, liefert aber weiter visuell unbrauchbare Farbzerfall-Bilder

### Enge Isolationspruefung
- Mit `anime_standard` plus vollem V6.1-Pfad:
  - technisch `ok`
  - visuell kaputt
- Mit demselben `anime_standard` und derselben Promptfamilie, aber umgangenem `ApplyInstantID`:
  - der reine SDXL-/Anime-Render liefert ein plausibles Anime-Bild
- Damit bleibt als enger Hauptblocker nicht mehr der Samplerpfad, sondern der aktuelle V6.1-Identity-Conditioning-Block mit `ApplyInstantID` auf dem Anime-Checkpoint.

### Entscheidung
- Kein sichtbarer `Foto | Anime`-Schalter fuer V6.1 im Repo.
- Keine halbfertige Basismodus-Freigabe.
- Erst wenn der Anime-Zweig des V6.1-Identity-Conditioning sauber funktioniert, ist ein ehrlicher V11.7-Rollout vertretbar.

## V11.9 Anime-Blocker Im V6.1-Identity-Conditioning Isoliert

### Reproduzierbarer Minimalfall
- Referenzbild:
  - `reference-20260315014724-066ae2c3`
- Prompt:
  - `same person, anime portrait, cel shading, detailed eyes, calm expression`
- Fester Seed:
  - `123456789`
- Feste Parameter:
  - `steps=20`
  - `cfg=6.5`
  - `width=1024`
  - `height=1024`
  - `sampler=euler`
  - `scheduler=normal`

### Hauptursache
- Der verbleibende Anime-Killer lag nicht mehr am Samplerpfad und auch nicht am `Animagine`-Checkpoint selbst.
- Der eigentliche Kipp-Punkt war die im V6.1-Workflow hinterlegte volle `ApplyInstantID`-Staerke:
  - `weight = 0.8`
- Diese Staerke war fuer `Animagine XL 4.0` zu aggressiv und erzeugte im reproduzierbaren Fall Farbzerfall und visuell kaputte Gesichter.

### Enge Isolationskette
- `anime_standard` + voller V6.1-Pfad + `weight=0.8`:
  - technisch `ok`
  - visuell kaputt
- `anime_standard` ohne `ApplyInstantID`:
  - plausibles Anime-Bild
- derselbe volle V6.1-Pfad mit genau einem geaenderten Parameter:
  - `weight=0.35`
  - Anime-Bild wieder plausibel und nutzbar
- Gegencheck:
  - `photo_standard` bleibt mit `weight=0.35` ebenfalls brauchbar

### Minimaler Fix
- Im V6.1-Workflow wurde genau ein Parameter angepasst:
  - `ApplyInstantID.weight: 0.8 -> 0.35`

### Ergebnis
- Der V6.1-Anime-Zweig ist damit nicht mehr auf den zuvor reproduzierten Farbzerfall festgelegt.
- V11.7 ist damit noch nicht automatisch ausgerollt, kann aber jetzt wieder ehrlich neu angesetzt werden.

## V11.7 Nach V11.9 Sauber Ausgerollt

### Ergebnis
- `Dieselbe Person neu erzeugen` nutzt im Basismodus jetzt optional eine einfache Bildwelt-Wahl:
  - `Foto`
  - `Anime`
- Die sichtbare Nutzerwahl bleibt bewusst eng und basiert intern nur auf den zwei festen Standards:
  - `photo_standard`
  - `anime_standard`
- Keine Checkpointnamen im Basismodus.
- Kein Ausbau fuer `V6.2` oder `V6.3`.

### Warum Der Rollout Erst Jetzt Kam
- Der sichtbare V11.7-Rollout wurde erst nach den beiden engen Fixes freigegeben:
  - V11.8: Sampler-/Scheduler-Fehler im V6.1-Pfad behoben
  - V11.9: zu aggressive `ApplyInstantID`-Staerke im Anime-Zweig behoben
- Erst danach waren sowohl `Foto` als auch `Anime` auf demselben V6.1-Produktpfad ehrlich brauchbar.

### Bildwelt-Beschreibungen Fuer Normale Nutzer Nachgezogen
- Die sichtbaren Texte zu `Foto | Anime` wurden im Basismodus noch einmal beruhigt und praxisnaher gemacht.
- `Foto` wird jetzt klarer als realistische Wahl fuer natuerliche Gesichter und Szenen beschrieben.
- `Anime` wird jetzt klarer als stilisierte Wahl fuer Figuren und Anime-Look beschrieben.
- Keine Checkpointnamen und keine technische Modellsprache im sichtbaren Nutzerpfad.
