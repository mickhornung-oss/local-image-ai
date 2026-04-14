# V4 Lokale Text-KI Architektur

## Ist-Zustand
- `python/app_server.py` ist der lokale Einstiegspunkt auf `127.0.0.1:8090`.
- Der App-Server serviert UI, Health, Uploads, Ergebnisse und orchestriert Bild-Generierung.
- Die Bild-Engine ist bereits sauber ausgelagert: ComfyUI laeuft separat auf `127.0.0.1:8188`.
- `python/render_text2img.py` und `python/comfy_client.py` kapseln die Bild-Workflows und die ComfyUI-API-Grenze.
- `web/index.html` arbeitet gegen eine kompakte lokale HTTP-API und kennt bereits getrennte Health-, Request- und Ergebniszustaende.

## Ziel Fuer V5
- Eine lokale Text-KI ergaenzen, ohne den bestehenden Bild-Pfad technisch oder operativ zu vermischen.
- Die Browser-App bleibt ein gemeinsamer Einstiegspunkt.
- Bild-KI und Text-KI bleiben getrennte Laufzeitbausteine.

## Gepruefte Varianten

### A. Text-KI direkt im bestehenden App-Prozess
- Vorteil: wenig neue Startlogik.
- Nachteil: schlechteste Fehlerisolierung.
- Nachteil: gemeinsamer Python-Prozess fuer UI-Backend, Uploads, Ergebnisse, Bild-Orchestrierung und spaeter Text-Inferenz.
- Nachteil: hohes Konfliktrisiko bei Speicher, Blocking, Modellruntime und spaeteren Windows-spezifischen Dependencies.
- Urteil: fuer dieses Projekt unpassend.

### B. Text-KI als separater lokaler Nebenprozess mit klarer API-Grenze
- Vorteil: beste technische Trennung.
- Vorteil: Fehler in der Text-KI ziehen die Bild-KI nicht mit.
- Vorteil: eigener Runtime-/Venv-/Modellpfad spaeter moeglich.
- Vorteil: passt zum bereits bewaehrten Muster `App-Server -> ComfyUI`.
- Vorteil: spaeter einfach optional aktivierbar, ohne normale Nutzer mit mehreren manuellen Schritten zu ueberfordern.
- Nachteil: zusaetzlicher lokaler Prozess und eigener Health-Status.
- Urteil: beste Zielarchitektur.

### C. Text-KI als optionales Modul/Adapter im bestehenden Backend-Pfad
- Vorteil: sauberer als Variante A auf Codeebene.
- Nachteil: operativ weiter derselbe Fehlerraum wie Variante A.
- Nachteil: trennt Code, aber nicht Speicher, Startlogik oder Dependency-Risiken.
- Urteil: nur fuer sehr kleine CPU-Spielpfade sinnvoll, hier aktuell schlechter als B.

## Empfohlene Zielarchitektur
- V5 soll Variante B nutzen: eine separate lokale Text-KI-Engine als loopback-only Nebenprozess mit klarer HTTP-Grenze.
- `python/app_server.py` bleibt der einzige Browser-Einstiegspunkt.
- Die Text-KI wird spaeter als eigener interner Dienst behandelt, analog zur heutigen ComfyUI-Kopplung.
- Bild-KI und Text-KI behalten getrennte:
  - Laufzeit
  - Health-Zustaende
  - Modellverzeichnisse
  - Fehlerpfade
- Die App darf spaeter beide Engines im Health sichtbar machen, aber Text-Probleme duerfen den Bild-Pfad nicht global blockieren.

## Warum Die Anderen Varianten Schlechter Passen
- A vermischt den heute stabilen App-Server direkt mit spaeter schwerer lokaler Inferenz.
- A erhoeht das Risiko, dass ein Text-Modell den Bild-Flow oder die UI-Responsiveness zerlegt.
- C verbessert nur die Codeordnung, nicht die Betriebsgrenze.
- Das bestehende Projekt hat mit dem separaten ComfyUI-Service bereits ein funktionierendes Trennungsmuster; B wiederverwendet genau dieses Muster.

## No-Gos
- Kein Text-Modell im bestehenden App-Prozess.
- Kein Text-Modell in `vendor/ComfyUI/venv` oder in denselben Modellordnern wie die Bild-KI.
- Keine gemeinsame Sammel-Health, die Text- und Bild-Fehler ununterscheidbar macht.
- Kein frueher Chat-/History-/Session-Ballast im ersten V5-Schnitt.
- Kein Startzwang: Bild-KI muss weiter ohne Text-KI normal laufen koennen.

## Sauberer V5-Einstiegsschnitt
- Neuer separater Text-Dienst, spaeter mit eigenem Startskript und eigener lokaler Konfiguration.
- Minimaler interner API-Schnitt fuer V5:
  - `GET /health`
  - `POST /complete`
- `python/app_server.py` bindet die Text-KI spaeter nur als optionale Engine an, nicht als Kernabhaengigkeit.
- Eigener Modellpfad ausserhalb von `vendor/ComfyUI/models/`.
- Eigene Logs und eigener Statuspfad, analog zur heutigen Runner-Logik.

## V5 Block 1 Umgesetzt
- `python/text_service.py` ist als separater loopback-only Dienst angelegt.
- `config/text_service.json` setzt den engen Startzustand:
  - `enabled`
  - `host`
  - `port`
  - `service_name`
  - `model_status`
- `scripts/run_text_service.ps1` startet den Dienst optional und getrennt von Bild-App und ComfyUI.
- Der Dienst stellt nur diese Endpunkte bereit:
  - `GET /health`
  - `GET /info`
- Es gibt noch keine Inferenz, kein Modell und keine Kopplung in die Haupt-UI.

## V5 Block 2 Umgesetzt
- Der Text-Dienst stellt jetzt zusaetzlich `POST /prompt` bereit.
- `POST /prompt` validiert nur einen engen JSON-Request mit `prompt`.
- Leere, ungueltige oder zu lange Prompts werden strukturiert als `400 invalid_request` abgelehnt.
- Erfolgreiche Antworten bleiben klar als Stub markiert:
  - `stub=true`
  - `model_status=not_configured`
  - deterministische Antwort ohne Modellinferenz
- `/info` markiert jetzt:
  - `prompt_endpoint_available=true`
  - `inference_available=false`
  - `stub_mode=true`
- Weiter bewusst nicht umgesetzt:
  - kein Modell
  - kein `/chat`
  - kein Streaming
  - keine Haupt-App-UI

## V5 Block 3 Umgesetzt
- Die Haupt-App prueft den Text-Dienst jetzt read-only ueber dessen `GET /health` und `GET /info`.
- Die Kopplung bleibt optional:
  - faellt der Text-Dienst aus, bleibt die Bild-App voll nutzbar
  - es gibt keine harte Abhaengigkeit und keinen Auto-Start
- Die Haupt-App uebernimmt nur einen kleinen Statussatz:
  - konfiguriert ja/nein
  - erreichbar ja/nein
  - `service_name`
  - `stub_mode`
  - `inference_available`
  - `model_status`
- Die UI zeigt nur eine knappe read-only Zeile zum Text-Dienst.
- Weiter bewusst nicht umgesetzt:
  - keine Texteingabe
  - kein `/prompt` aus der Haupt-App
  - keine Produktlogik auf Basis des Text-Diensts

## V26 Text-KI-Fundament
- Die produktive Text-KI in `web/index.html` arbeitet jetzt mit genau 5 festen Chat-Slots.
- Die Slot- und Verlaufsdaten werden lokal in `data/text_chats.sqlite3` gehalten.
- Der aktive Slot wird serverseitig mitgefuehrt; nur dieser Chat liefert Kontext fuer neue Textanfragen.
- Kontextaufbau im App-Server:
  - aktuelle Eingabe
  - rollende Kurz-Zusammenfassung aelterer Nachrichten
  - letzte Nachrichten des aktiven Chats
- Inaktive Slots bleiben gespeichert, werden aber nicht in den Live-Kontext gegeben.
- Metadaten pro Slot:
  - Titel
  - letztes Aenderungsdatum
  - Sprache
  - Modell
  - Kurz-Zusammenfassung
- Bestehende Produktfunktionen bleiben erhalten:
  - Antwortbereich
  - Copy
  - Spracheingabe
  - `Als Bildprompt verwenden`
- Weiter bewusst nicht umgesetzt:
  - kein Modellzoo
  - keine freie Modellimportstrecke
  - keine offene Endlos-Chatliste

## V27 Text-KI-Arbeitsmodi
- Das V26-Fundament bleibt erhalten; die Text-KI arbeitet weiter mit 5 festen lokalen Chat-Slots.
- Der aktive Textbereich hat jetzt genau 3 produktive Arbeitsmodi:
  - `Schreiben`
  - `Ueberarbeiten`
  - `Als Bildprompt umwandeln`
- Die Moduslogik wird bis in `python/text_service.py` durchgereicht:
  - `writing` fuer freies Schreiben, Stoffentwicklung und Fortsetzungen
  - `rewrite` fuer Ueberarbeitung, Umformulierung und stilistische Schaerfung
  - `image_prompt` fuer knappe, visuelle Prompt-Ausgabe
- Der aktive Modus wirkt nur auf die aktuelle Textanfrage und nicht auf die Bildarchitektur oder die Slot-Speicherung.
- Bestehende Hauptfunktionen bleiben im Textbereich erhalten:
  - Copy
  - Spracheingabe
  - `Als Bildprompt verwenden`
- Weiter bewusst nicht umgesetzt:
  - keine kuratierten Modell-Slots
  - kein Modellzoo
  - keine Autoren-Suite mit Figuren-, Plot- oder Kapitelverwaltung

## V27.1 Browser-Validierung Und Kleine UX-Nacharbeit
- Die Text-KI wurde danach nochmals real im Browser durchgeklickt:
  - Slot-Umschalten
  - neuen Chat anlegen
  - Umbenennen
  - Leeren
  - Moduswechsel
  - Copy
  - `Als Bildprompt verwenden`
  - Reload-Persistenz
  - sichtbare Kurz-Zusammenfassung bei laengerem Verlauf
- Kleine echte UX-Korrektur:
  - nach `Als Bildprompt verwenden` erscheint jetzt auch im Ziel-Bildpfad ein sichtbarer Hinweis `Prompt uebernommen ...`
- Spracheingabe wurde nur soweit lokal real getestet, wie der Browser ohne erkannte Sprache reagierte (`Kein Text erkannt`).

## V28 Kuratierte Modell-Slots
- Das V26/V27-Fundament bleibt erhalten; die Text-KI bekommt keine freie Modellliste, sondern genau 3 kuratierte Modellprofile:
  - `Standard`
  - `Starkes Schreiben`
  - `Mehrsprachig`
- Die Produktsprache bleibt ruhig und nutzerorientiert:
  - `Standard` = Schnell / Allround
  - `Starkes Schreiben` = Langtext
  - `Mehrsprachig` = Reserve
- Technisch bleibt die Modellwahl an den Chat-Slot gebunden:
  - pro Chat werden Modellprofil, Sprache, Titel, Zusammenfassung und letzter Stand gespeichert
  - beim Slotwechsel geht das gespeicherte Profil mit
- Verfuegbarkeit bleibt bewusst ehrlich:
  - lokal produktiv aktiv ist aktuell nur das Standardprofil
  - `Starkes Schreiben` und `Mehrsprachig` sind als vorbereitete Slots sichtbar, aber nicht auswählbar, solange die Zielmodelle lokal nicht vorhanden sind
- Der aktuelle lokale Realstand:
  - aktiver Runner arbeitet weiter mit dem vorhandenen GGUF-Standardmodell
  - kein Modellzoo
  - kein Download-Center
  - keine freie Importstrecke im Hauptprodukt

## V29 Kontrollierter Runner-Wechsel
- Die kuratierten Modellprofile bleiben erhalten; neu ist die technische Wechselbasis im laufenden Text-Stack.
- Modellwechsel laeuft bewusst kontrolliert und nicht als stiller Fallback:
  - Chat speichert sein Modellprofil
  - beim aktiven Chat wird das passende Profil geprueft
  - wenn noetig, wird der Text-Runner kontrolliert neu initialisiert
- Statuslinie fuer den Produktzustand:
  - `Aktiv`
  - `Laedt`
  - `Vorbereitet`
  - `Fehler`
- Wichtige Realregel:
  - `Vorbereitet` bleibt fuer lokal noch nicht installierte Zielmodelle sichtbar, aber nicht lauffaehig
  - Requests mit solchen Profilen werden sauber abgewiesen statt heimlich auf etwas anderes zu fallen
- Der App-Server startet den Text-Runner fuer den Re-Init jetzt direkt und pollt den lokalen Runner-Port, statt eine freie Modellwelt oder einen Modellzoo aufzumachen.
- Der Text-Service liest seine Konfiguration fuer Health/Info/Prompt jetzt live nach, damit Modellpfad und Runner-Zustand nach einem Wechsel ehrlich sichtbar bleiben.

## V30 Starkes Schreiben Produktiv
- `Starkes Schreiben` ist jetzt als echter zweiter kuratierter Text-Slot produktiv verfuegbar.
- Reales Zielmodell:
  - `mistral-small-3.1-24b-instruct-2503-jackterated-hf.Q4_K_S.gguf`
- Ablage:
  - `vendor/text_models/mistral-small-3.1-24b-instruct-2503-jackterated-hf.Q4_K_S.gguf`
- Der bestehende kontrollierte Runner-Re-Init aus V29 zieht jetzt real zwischen:
  - `Standard` -> lokales Qwen-GGUF
  - `Starkes Schreiben` -> lokales Mistral Small 3.1 24B GGUF
- Wichtige Nachschaerfungen in `python/app_server.py`:
  - Profilauflosung trennt `Standard` und `Starkes Schreiben` sauber, auch wenn beide lokal installiert sind
  - die Text-Uebersicht synchronisiert den Runner wieder auf das Profil des aktiven Chats
  - nach einem echten Modellwechsel gibt es einen engen Einmal-Retry fuer den ersten Prompt, falls der frisch gestartete Runner kurz noch in einem `503`-Fenster haengt
- Real getestet:
  - echter Wechsel `Standard -> Starkes Schreiben`
  - echter Wechsel `Starkes Schreiben -> Standard`
  - Schreibtest, Ueberarbeiten und Bildprompt-Ausgabe auf `Starkes Schreiben`
  - chat-gebundene Profilpersistenz ueber Slotwechsel
  - sichtbarer Browser-Wechsel `Standard <-> Starkes Schreiben`
- Bewusst noch nicht umgesetzt:
  - `Mehrsprachig` bleibt weiter nur vorbereitet
  - kein Modellzoo
  - keine freie Quant-Auswahl fuer Nutzer

## V31 Mehrsprachig Produktiv
- `Mehrsprachig` ist jetzt als echter dritter kuratierter Text-Slot produktiv verfuegbar.
- Reales Zielmodell:
  - `google_gemma-3-12b-it-Q5_K_M.gguf`
- Ablage:
  - `vendor/text_models/google_gemma-3-12b-it-Q5_K_M.gguf`
- Der bestehende Runner-Re-Init traegt jetzt real alle drei kuratierten Slots:
  - `Standard`
  - `Starkes Schreiben`
  - `Mehrsprachig`
- Wichtige Nachschaerfungen:
  - Runner-Start-Timeout wurde fuer den schwereren Rueckwechsel auf `Starkes Schreiben` robuster gesetzt
  - der Gemma-Slot folgt jetzt fuer Schreib- und Rewrite-Aufgaben der Sprache der Eingabe statt pauschal auf Deutsch zu antworten
  - Bildprompt-Ausgabe bleibt auch im Mehrsprachig-Slot bewusst englisch
- Real getestet:
  - echter Wechsel `Standard -> Mehrsprachig -> Standard`
  - echter Wechsel `Starkes Schreiben -> Mehrsprachig -> Starkes Schreiben`
  - Schreibanfragen auf Deutsch, Englisch und Spanisch
  - Rewrite auf Franzoesisch
  - Bildprompt-Ausgabe aus englischer Eingabe
  - sichtbare Browser-Aktivierung und Statuswechsel fuer `Mehrsprachig`
- Produktgrenze:
  - der sichtbare Selenium-Sendelauf blieb browserseitig nicht stabil bis zur fertigen Antwort belegbar, obwohl dieselben Pfade API-seitig real gruen liefen

## V5 Block 4 Umgesetzt
- Die Haupt-App kann jetzt einen einzelnen manuellen Prompt-Test gegen den Stub-Endpunkt des Text-Diensts ausloesen.
- Der neue Schnitt laeuft kontrolliert ueber die Haupt-App und nicht direkt aus dem Browser auf Port `8091`.
- Der Test bleibt eng:
  - ein Prompt
  - ein Button
  - eine kompakte Antwortanzeige
- Weiter bewusst nicht umgesetzt:
  - kein Chat
  - kein Verlauf
  - kein Streaming
  - keine echte Inferenz

## V8.1 Echte Runner-Richtung Festgezogen
- Bevorzugte Richtung fuer den ersten echten Modellblock:
  - eigener `llama.cpp`-artiger Loopback-Runner hinter dem bestehenden Text-Service
- Minimaler echter Schnitt fuer den naechsten Modellblock:
  - `runner_type=llama_cpp_server`
  - `model_format=gguf`
  - eigener Modellpfad ausserhalb der Bild-KI
  - eigener lokaler Runner-Port getrennt von `8090` und `8188`
  - weiterhin genau ein einfacher Prompt-Request ohne Chat, Streaming oder Verlauf
- Warum nicht Ollama als primaere Richtung:
  - zusaetzlicher externer Produkt-Layer statt direkter Kontrolle im bestehenden lokalen Service-Schnitt
  - fuer dieses Repo unnoetige Verdopplung von Servicegrenzen
- Warum nicht Python-direkt als primaere Richtung:
  - hoehere Dependency- und Runtime-Last im Text-Service selbst
  - schlechtere Trennung von Modellruntime und leichtgewichtigem API-Dienst

## V8.1 Vorbereiteter Service-Zustand
- Der Text-Service kennt jetzt sauber drei Zielzustaende:
  - `stub`
  - `real_model_not_ready`
  - `real_model_ready`
- Im aktuellen Stand bleibt der Default bewusst:
  - `service_mode=stub`
  - `runner_type=llama_cpp_server`
  - `model_format=gguf`
  - `model_configured=false`
  - `model_present=false`
  - `inference_available=false`
- Wenn spaeter nur ein Modellpfad konfiguriert ist, aber noch kein echter Runner angeschlossen wurde, kann der Dienst sauber `real_model_not_ready` melden, statt weiter Stub-Erfolg vorzutäuschen.

## V8.1 Bewusst Noch Nicht Umgesetzt
- kein Modell-Download
- kein Modell-Load
- kein echter Runner-Start
- kein Streaming
- kein Chatverlauf
- kein Mehrmodellbetrieb

## V8.2 Minimaler Runner-Pfad
- Der Text-Service kann jetzt ehrlich zwischen diesen lokalen Zustaenden unterscheiden:
  - `stub`
  - `real_model_not_ready`
  - `real_model_ready`
- Der bevorzugte echte Pfad bleibt:
  - `runner_type=llama_cpp_server`
  - `model_format=gguf`
  - ein externer loopback-only Runner auf dem konfigurierten Runner-Port
- `/health` und `/info` zeigen jetzt zusaetzlich:
  - `runner_present`
  - `runner_reachable`
  - `runner_startable`
  - `runner_binary_path`
- `/prompt` nutzt jetzt genau dann einen echten lokalen Runner-Call, wenn der Runner real erreichbar ist und das konfigurierte GGUF-Modell lokal vorhanden ist.
- Der aktuelle reale Minimal-Stack ist jetzt lokal bereitgestellt:
  - `llama-server.exe` aus `llama.cpp` Release `b8292`
  - genau ein GGUF-Modell: `Qwen2.5-0.5B-Instruct q4_0`
  - lokaler Runner-Port: `127.0.0.1:8092`
  - lokaler Runner-Start ueber `scripts/run_text_runner.ps1`
- Der Text-Service laeuft damit jetzt real auf:
  - `service_mode=real_model_ready`
  - `runner_present=true`
  - `runner_reachable=true`
  - `model_present=true`
  - `inference_available=true`
- Der erste echte Prompt-Lauf ueber `/prompt` und ueber die Haupt-App ist damit gruen.
- Weiter bewusst nicht umgesetzt:
  - kein Modell-Download
  - kein Chatverlauf
  - kein Streaming
  - kein Modellwechsel

## V8.5 Guardrails und engere Defaults
- Der bestehende Runner-Pfad wurde nicht umgebaut, aber die Anfragefuehrung fuer den aktuellen Einzelprompt wurde enger gezogen.
- Der Text-Service nutzt jetzt einen kleinen festen Qualitaetsblock:
  - kuerzere Antworten
  - staerkere Wiederholungsbremse
  - einfache Aufgabenfuehrung fuer
    - Bildprompt-Hilfe
    - kurze Umformulierungen
    - kurze Sachantworten
- Der Service nutzt dafuer:
  - engere Runner-Defaults fuer Laenge und Sampling
  - genau einen kleinen Retry bei klar unbrauchbarer Erstantwort
  - defensiven Guardrail gegen offensichtlichen Wiederholmuell und unbrauchbare Fremdsprachenausgaben
- Reale Wirkung im aktuellen Stand:
  - deutlich weniger ausufernde Schleifen
  - kuerzere, kontrolliertere Antworten
  - Bildprompt-Hilfe liefert jetzt kurze Prompt-Fragmente statt langer Wiederholungsblöcke
- Ehrliche Restgrenze des aktuell aktiven Modells `Qwen2.5-0.5B-Instruct q4_0`:
  - die Antworten sind ruhiger, aber sachlich und sprachlich weiter begrenzt
  - besonders bei vagen Bildwünschen oder kleinen Wissensfragen bleibt die Modellqualitaet sichtbar schwach
  - V8.5 loest also vor allem Wiederholung und Ausufern, nicht die Grundstaerke des Modells
- Weiter bewusst nicht umgesetzt:
  - kein Modellwechsel
  - kein Chatverlauf
  - kein Streaming
  - kein Mehrmodellbetrieb

## V8.6 Genau ein staerkeres GGUF als neuer Standard
- Es wurde genau ein Upgrade-Kandidat real geprueft und als neuer Standard gesetzt:
  - `Qwen2.5-7B-Instruct GGUF`
  - konkret lokal: `vendor/text_models/qwen2.5-7b-instruct-q4_k_m.gguf`
- Der bestehende `llama.cpp`-Runner blieb unveraendert; der Text-Service nutzt weiter denselben echten Minimalpfad:
  - `runner_type=llama_cpp_server`
  - `service_mode=real_model_ready`
  - `stub_mode=false`
  - `inference_available=true`
- Der bisherige 0.5B-Stand wurde damit bewusst ersetzt; es bleibt genau ein aktives lokales GGUF-Modell im Text-Stack.
- Reale Wirkung gegen den bisherigen 0.5B-Stand:
  - Bildprompt-Hilfe ist sichtbar brauchbarer und nicht mehr auf Ein-Wort-Niveau
  - Umformulierungen sind ruhiger und sprachlich sauberer
  - kurze Wissensantworten sind deutlich plausibler
  - die Laufzeit ist spuerbar hoeher, aber im aktuellen lokalen Stand noch akzeptabel
- Bestehende Guardrails und engen Defaults aus V8.5 bleiben aktiv; zusaetzlich wurde nur der Prompt-Proxy der Haupt-App auf den langsameren 7B-Lauf angepasst.
- Weiter bewusst nicht umgesetzt:
  - kein Chatverlauf
  - kein Streaming
  - kein Mehrmodellbetrieb
  - kein Modellwechsel im Produkt

## V8.7 Qualitaetsnachschaerfung auf dem bestehenden 7B
- Der aktive 7B-Stack blieb unveraendert:
  - gleiches Modell
  - gleicher `llama.cpp`-Runner
  - kein Chatmodus
  - kein Streaming
- Nachgeschaerft wurde nur der bestehende Einzelprompt-Pfad:
  - engere Sampling-Defaults fuer kuerzere, ruhigere Antworten
  - klarere interne Aufgabenfuehrung fuer
    - Bildprompt-Hilfe
    - Umformulieren
    - kurze direkte Antwort
  - kleine defensive Retry-/Qualitaetschecks gegen
    - zu duenne Bildprompts
    - Wiederholung
    - kaputte Mischantworten
- Reale Wirkung im aktuellen Stand:
  - Bildprompt-Hilfe ist konkreter und bildtauglicher als zuvor
  - Umformulierungen klingen natuerlicher und knapper
  - kurze Antworten schweifen weniger ab
- Ehrliche Restgrenze:
  - das 7B-Modell ist fuer alltaegliche Kurzaufgaben jetzt brauchbarer
  - bei kurzen Wissensfragen bleibt die sprachliche und fachliche Praezision aber sichtbar schwankend
  - V8.7 hebt damit klar den Nutzwert, macht das Modell aber noch nicht zum perfekten Wissensmodell

## V8.8 Produktentscheidung Zum 7B-Standard
- Entscheidung:
  - `Qwen2.5-7B-Instruct GGUF` bleibt der produktive Textstandard
  - ein spaeterer letzter Modellschritt ist nur optional, nicht aktuell noetig

### Produktiv Gut Genug Fuer
- Bildprompt-Hilfe:
  - klar brauchbar und jetzt einer der staerksten sichtbaren Nutzfaelle
- Umformulieren:
  - klar brauchbar fuer kurze, natuerliche Umformulierungen
- kurze Alltagsantworten:
  - gut genug fuer direkte, knappe Hilfsantworten ohne Chatlogik

### Ehrliche Restgrenze
- kurze Wissensfragen bleiben der sichtbar schwaechste Bereich
- die Antworten sind oft noch brauchbar, aber fachlich und sprachlich nicht stabil genug, um das Modell als starken Wissensassistenten zu verkaufen
- der Produktpfad sollte deshalb weiter ehrlich so gelesen werden:
  - stark fuer Bildprompts
  - stark fuer Umformulierungen
  - gut fuer kurze Alltagsantworten
  - nur eingeschraenkt fuer Wissensfragen

### Spaeterer Letzter Modellschritt Nur Bei Echtem Bedarf
- Falls spaeter ueberhaupt noch ein letzter Modellschritt sinnvoll wird, dann nur mit engem Zielbild:
  - besser bei kurzen Wissensantworten
  - weiter lokal betreibbar
  - kein Chatmonster, kein Mehrmodellbetrieb
- Stand V8.8:
  - kein akuter Integrationsbedarf
  - nur optionale Reserve fuer spaeteren Qualitaetswunsch

## V8.10 Schreibauftraege, Wortziel und Tonfuehrung
- Der bestehende 7B-Stack blieb technisch derselbe:
  - gleiches Modell
  - gleicher lokaler Runner
  - kein Chat
  - kein Streaming
- Nachgeschaerft wurde nur der bestehende Einzelprompt-Pfad:
  - klarere interne Trennung zwischen
    - Bildprompt-Hilfe
    - Umformulieren
    - kurzer Direktantwort
    - Infotext
    - kreativem Schreibauftrag
  - robustere Erkennung von Brief-, Kartentext- und allgemeinen Schreibauftraegen
  - engere Wortziel-Fuehrung mit genau einem zweiten Anlauf bei klarer Unterlaenge
  - bessere Ton- und Formhinweise fuer
    - liebevoll
    - freundlich
    - klassisch
    - sachlich
  - laengere Antwortfenster und groesserer Prompt-Proxy-Timeout fuer echte Schreibauftraege
- Reale Wirkung im aktuellen Stand:
  - ein 100-Wort-Brief kommt jetzt deutlich naeher ans Ziel und bleibt ueber die Haupt-App nutzbar
  - ein 300-Wort-Infotext wird jetzt grob in Zielnaehe geliefert statt als Mini-Antwort
  - kurze Schreibauftraege fuer Karten oder stimmige Szenentexte sind sichtbar brauchbarer als vorher
- Ehrliche Restgrenze:
  - kreative Kurztexte mit Wortziel unter oder um 120 Woerter bleiben die sichtbar schwankendste Schreibklasse
  - das aktive 7B-Modell trifft solche Zielmengen jetzt besser, aber noch nicht jedes Mal sauber
  - V8.10 macht den Schreibpfad damit klar brauchbarer, aber noch nicht perfekt laengentreu

## V20 Text-KI-Modellstrategie (ohne Rollout)

### Aktueller Produktstand
- aktiver Standard bleibt:
  - `Qwen2.5-7B-Instruct GGUF`
- aktuell zuverlaessig fuer:
  - Bildprompt-Hilfe
  - Umformulieren
  - kurze Alltagsantworten
  - einfache Schreibauftraege
- ehrliche Restgrenze:
  - kurze Wissensfragen und hohe fachliche Praezision schwanken weiter

### Gepruefte Ausbaurichtung
- kein Mehrmodellbetrieb im sichtbaren Produktpfad
- kein sofortiger Modellwechsel
- bevorzugter spaeterer Ausbau:
  - genau ein kontrollierter Upgrade-Pfad auf ein staerkeres lokales Modell
  - gleiche Servicegrenzen (`app_server` -> `text_service` -> `llama-server`)
  - gleiche Bedienlogik im Basismodus

### Empfohlene spaetere Upgrade-Policy
- weiterhin genau ein aktives Produktmodell zur Laufzeit
- optionaler Upgrade-Schritt nur, wenn:
  - Wissensantworten produktseitig wirklich wichtiger werden
  - Laufzeit und lokaler Speicherrahmen stabil bleiben
- kein offener Modellschalter fuer normale Nutzer in diesem Schritt

### V20 bewusst nicht umgesetzt
- kein Modellwechsel
- kein zusaetzlicher Modellrunner
- kein neuer Chat-/Promptmodus

## V20.1 Text-KI Im Produktschnitt 2.0

### Produktfluss Nachgezogen
- Text-KI bleibt vorne als Hauptaufgabe sichtbar.
- Die Aktion `Als Bildprompt verwenden` arbeitet jetzt zielgerichtet fuer die allgemeinen Bildpfade:
  - `Neues Bild erstellen`
  - `Bild anpassen`
  - `Bereich im Bild aendern`
- Damit bleibt der Weg von Textantwort zu Bildstart ein klarer Ein-Klick-Flow ohne neue Prompt-Engine.

### bewusst nicht Teil von V20.1
- keine neue Textpipeline
- keine Modellumschaltung in der UI
- kein Mehrmodellbetrieb

## V32 Chat-Modulgruppe Nachgezogene Ist-Architektur

- Die produktive Text-KI bleibt im sichtbaren Produkt unveraendert:
  - gleicher Browser-Pfad
  - gleiche 5 Chat-Slots
  - gleiche Modellprofile
  - gleicher App-Server als Einstiegspunkt
- Intern ist der Chat-Bereich in `python/` jetzt als kleine Modulgruppe sichtbar entkoppelt.

### Heutige Modulgrenzen im Chat-Bereich

- `python/text_chat_store.py`
  - lokale Persistenz fuer Slots, Nachrichten und aktiven Slot
  - SQLite-Initialisierung und Metadatenpflege
- `python/text_chat_payloads.py`
  - Overview-Payloads fuer Slot-Liste und aktive Chat-Uebersicht
- `python/text_chat_requests.py`
  - Request-Coercion, Slot-/Action-Aufloesung und Titelregeln fuer Chat-Requests
- `python/text_chat_responses.py`
  - finale Slot-Detail-Responses aus bereits vorbereiteten Slot- und Profilzustandsdaten
- `python/text_chat_service_orchestration.py`
  - chat-nahe Vorbereitung des Text-Service-Aufrufs
  - enger Retry nach Profilwechsel
  - Fehler-/Fallback-Mapping rund um den Chat-Request
  - kleine Nachbereitung von Antworttext, Titel und Summary

### Was in `python/app_server.py` bleibt

- der einzige Browser- und HTTP-Einstiegspunkt
- die eigentlichen Chat-Endpunkte und Handler
- die Ablaufkoordination zwischen:
  - Chat-Zustand
  - Modellprofilwechsel
  - Text-Service
  - finaler API-Antwort
- die produktweite Verknuepfung von Text-KI mit Bild-KI, Ergebniswelt und restlichen lokalen Diensten

### Delegationsrichtung im heutigen Stand

- Browser/UI
  -> `python/app_server.py`
  -> Chat-Teilmodule fuer Requests, Store, Payloads, Responses und Text-Service-Orchestrierung
  -> `python/text_service.py`
  -> lokaler Runner

### Bewusst noch nicht weiter gezogen

- keine vollstaendige Auslagerung der Chat-Handler aus `app_server.py`
- keine allgemeine Text-Service-Orchestrierung ausserhalb des Chat-Pfads
- keine Vermischung mit Bild-, Upload-, Result- oder Identity-Pfaden
- keine neue Produktarchitektur, sondern nur sichtbarer gemachte reale Modulgrenzen
## V33 App-Server Restkern und Teststand

Der verbleibende Kern in `python/app_server.py` ist aktuell bewusst als Koordinationsgrenze belassen:

- HTTP-Endpunkte und Routing
- Laufzeitverdrahtung zwischen Chat-, Upload-, Result-, Status- und Generate-Modulen
- Servicekopplung und servernahe Fehlerbehandlung

Die aggressive Zerlegung dieses Restkerns ist fuer die aktuelle Projektphase beendet. Weitere Eingriffe sind nur noch sinnvoll, wenn spaetere Tests oder echte Produktprobleme einen klaren neuen fachlichen Schnitt erzwingen.

Der Teststand umfasst inzwischen:

- Modul-Unittests fuer die ausgelagerten Chat-, Upload-, Result-, Status-, Pfad- und Generate-Helfer
- handlernahe Integrations-/Endpoint-Tests mit Mocks fuer repraesentative Endpunkte
- lokalen Smoke-Test fuer den Stack
- reale Live-Pruefung ueber `/health`, Text-Chat, Upload, `/generate`, Result-Export/Delete und Identity-Readiness

Der aktuell sichtbare `ComfyUI_ACE-Step`-/`torchaudio`-Konflikt ist fuer den heutigen Produktkern nur ein optionaler Nebenaspekt. Solange kein ACE-Step-basierter Produktpfad verdrahtet wird, blockiert er die aktiven Text-, Standard-Bild- und Identity-Flows nicht.
