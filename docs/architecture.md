# Historisches Dokument - Code KI V1 (Veraltet)

## System Design - Local Image AI (Aktuell)

```mermaid
graph TB
    subgraph Win["Windows App UI"]
        UI1["Text Mode<br/>Chat Interface"]
        UI2["Image Gen Mode<br/>Prompt Builder"]
    end
    
    subgraph Backend["Python Backend<br/>Flask/FastAPI"]
        TEXT["Text KI Engine<br/>Ollama/OpenAI"]
        IMG["Image Gen<br/>Stable Diffusion"]
        PROC["Image Processor<br/>PIL/OpenCV"]
    end
    
    subgraph Storage["Local Storage"]
        DB["Chat DB<br/>SQLite"]
        CACHE["Image Cache<br/>Output Folder"]
    end
    
    subgraph External["External APIs"]
        OAI["OpenAI<br/>GPT-4"]
        SD["Stable Diffusion<br/>v1.5+"]
    end
    
    UI1 -->|prompt| TEXT
    UI2 -->|description| IMG
    TEXT --> OAI
    TEXT --> DB
    IMG --> SD
    IMG --> PROC
    PROC --> CACHE
    CACHE -->|display| UI2
    DB -->|history| UI1
    
    style Win fill:#3498db,color:#fff
    style Backend fill:#2ecc71,color:#fff
    style Storage fill:#e74c3c,color:#fff
    style External fill:#f39c12,color:#fff
```

## Active Product Core (MP-01)

Für den aktiven Produktkern siehe:
- `README.md`
- `docs/product_core_mp01.md`
- `docs/technical_closeout_mp04.md`

### Produktive Features (MP-01)
- Text KI Chat + Persistierung
- Image Generation (mit Stable Diffusion)
- Image Refinement & Inpainting
- Gallery + Download/Export
- V6 Identity Engine (Research)

### Performance (RTX 4090)
- Image Gen: ~3-5s pro 1024x1024
- Memory: ~8GB VRAM + 4GB RAM
- Cache: 100 Bilder In-Memory

---

# Dieses Dokument - Code KI V1 (Historisch)

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
