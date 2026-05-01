# llmauto — User-Dokumentation
# MarbleRun Pipeline fuer autonome LLM-Ketten
# Stand: 2026-03-14

---

## 1. Was ist llmauto?

llmauto ist ein Automatisierungsframework, das Claude-Instanzen in einer Kette (MarbleRun)
orchestriert. Wie bei einer Murmelbahn rollt der Kontext (Handoff) von Link zu Link:

```
Runde 1:
  Controller → Sonnet Worker → Opus Worker → Opus Deep → Controller
                                                            ↓
Runde 2:
  Controller → Sonnet Worker → Opus Worker → Opus Deep → Controller
                                                            ↓
  ... (bis Timeout, max_rounds oder ALL_DONE)
```

Jeder Link ist eine eigenstaendige Claude-Session mit eigenem Prompt und Modell.
Die Kommunikation erfolgt ueber eine `handoff.md`-Datei.

---

## 2. Schnellstart

```bash
cd "/c/Users/lukas/OneDrive/.AI/MODULES/llmauto"

# Chain starten (Vordergrund)
python -m llmauto chain start forschung-todos

# Chain starten (Hintergrund, neues Fenster)
python -m llmauto chain start forschung-todos --bg

# Status abfragen
python -m llmauto chain status forschung-todos

# Stoppen (nach aktuellem Link)
python -m llmauto chain stop forschung-todos "Grund"

# Zuruecksetzen auf Runde 0
python -m llmauto chain reset forschung-todos

# Logs anzeigen
python -m llmauto chain log forschung-todos
```

---

## 3. Verfuegbare Chains

### 3.1 forschung-todos (Forschungspipeline)

**Zweck:** Wissenschaftliche TODOs aus `.RESEARCH/` systematisch abarbeiten.

**Aufgabenquellen:**
- `SCIENTIFIC_WORK_NOTES.md` — Zentrale Sammlung inhaltlicher Aufgaben (~186 Tasks)
- `AUFGABEN.txt` — Projektuebergreifende TODOs (Disclosure, Zenodo, Cross-Refs)
- `Plan.txt` / `AKTIONSPLAN.md` — Projekt-spezifische TODOs

**4 Links pro Runde:**

| Link | Modell | Aufwand | Tasks/Runde | Wofuer |
|------|--------|---------|-------------|--------|
| **Controller** | Opus (continue) | Planung | — | Plant, priorisiert, prueft, verteilt |
| **Sonnet Worker** | Sonnet | Niedrig | 8-10 | Mechanisch: LaTeX, Disclosure, DOIs, Metadaten |
| **Opus Worker** | Opus | Mittel | 3-5 | Inhaltlich: LIT-Issues, Formalisierungen, Abschnitte |
| **Opus Deep** | Opus | Hoch | 1-2 Projekte | Ganze Projekte/Serien, komplexe Revisionen |

**Einstellbare Parameter:**

| Parameter | Datei | Standard | Beschreibung |
|-----------|-------|----------|-------------|
| `runtime_hours` | `chains/forschung-todos.json` | 4 | Max. Laufzeit in Stunden |
| `max_rounds` | `chains/forschung-todos.json` | 50 | Max. Anzahl Runden |
| `opus_deep_limit` | `chains/forschung-todos.json` | 1 | Max. Opus-Deep-Einsaetze pro Lauf |
| `timeout_seconds` | `chains/forschung-todos.json` | 3600 | Timeout pro einzelnem Link (1h) |
| `max_consecutive_blocks` | `chains/forschung-todos.json` | 3 | Shutdown nach N aufeinanderfolgenden BLOCKs |
| Natur&Technik-Ausschluss | Prompts | aktiv | Ordner wird komplett ignoriert |

**Beispiel: 8h Lauf mit 3 Deep-Einsaetzen:**
```json
{
    "runtime_hours": 8,
    "opus_deep_limit": 3
}
```
Zusaetzlich im Controller-Prompt (`prompts/research_opus_controller.txt`) den Wert
bei "Max. X Einsaetze" anpassen (wird nicht automatisch aus JSON gelesen).

### 3.2 software-entwicklung (Software-Pipeline)

**Zweck:** ATI-Tasks und AUFGABEN.txt aus `.SOFTWARE/` abarbeiten.

**2 Links pro Runde:**

| Link | Modell | Tasks/Runde | Wofuer |
|------|--------|-------------|--------|
| **Controller** | Opus (continue) | — | ATI-Tasks lesen, priorisieren, zuweisen |
| **Sonnet Worker** | Sonnet (until_full) | 10 | Bug-Fixes, Docstrings, Tests, Cleanup |

**Einstellbare Parameter:**

| Parameter | Standard | Beschreibung |
|-----------|----------|-------------|
| `runtime_hours` | 6 | Max. Laufzeit |
| `max_rounds` | 50 | Max. Runden |

---

## 4. Chain-Konfiguration (JSON Schema)

Chains liegen in `chains/<name>.json`. Vollstaendiges Schema:

```json
{
    "chain_name": "meine-chain",
    "description": "Beschreibung",
    "mode": "loop",
    "max_rounds": 50,
    "runtime_hours": 4,
    "max_consecutive_blocks": 3,

    "defaults": {
        "permission_mode": "dontAsk",
        "allowed_tools": ["Read", "Edit", "Write", "Bash", "Glob", "Grep"],
        "timeout_seconds": 3600
    },

    "links": [
        {
            "name": "link-name",
            "role": "controller|worker|reviewer",
            "model": "claude-opus-4-6|claude-sonnet-4-6",
            "prompt": "prompt_key",
            "continue": false,
            "until_full": false,
            "fallback_model": null,
            "telegram_update": false,
            "description": "Beschreibung"
        }
    ],

    "prompts": {
        "prompt_key": {"type": "file", "path": "prompts/datei.txt"}
    }
}
```

### 4.1 Top-Level Parameter

| Parameter | Typ | Beschreibung |
|-----------|-----|-------------|
| `chain_name` | string | Eindeutige ID |
| `mode` | string | `"loop"` (wiederholt), `"once"` (einmalig) |
| `max_rounds` | int | Max. Runden (0 = unbegrenzt) |
| `runtime_hours` | float | Max. Laufzeit in Stunden (0 = unbegrenzt) |
| `deadline` | string | ISO-Datum fuer Abbruch (z.B. `"2026-04-01"`) |
| `max_consecutive_blocks` | int | Shutdown nach N aufeinanderfolgenden BLOCKs |

### 4.2 Link-Parameter

| Parameter | Typ | Standard | Beschreibung |
|-----------|-----|----------|-------------|
| `name` | string | — | Eindeutige Link-ID |
| `role` | string | — | `"controller"`, `"worker"`, `"reviewer"` |
| `model` | string | global default | Claude-Modell-ID |
| `prompt` | string | — | Prompt-Key oder Dateipfad |
| `continue` | bool | false | Persistente Session ueber Runden (Controller!) |
| `until_full` | bool | false | Arbeitet bis Kontextfenster voll |
| `fallback_model` | string | null | Fallback wenn primaeres Modell nicht verfuegbar |
| `telegram_update` | bool | false | Telegram-Nachricht nach diesem Link |

### 4.3 Prompt-Aufloesung

Prompts werden in dieser Reihenfolge gesucht:
1. `prompts`-Sektion in der JSON (type: file oder inline)
2. `prompts/<key>` als Datei
3. `prompts/<key>.txt`
4. Direkter Dateipfad
5. Fallback: Key selbst als Prompt-Text

Template-Variablen in Prompts:
- `{HOME}` → `C:\Users\lukas` (Windows-Pfad)
- `{BASH_HOME}` → `/c/Users/lukas` (Unix-Pfad)

### 4.4 Benutzerdefinierte Parameter

Die JSON unterstuetzt beliebige eigene Felder (z.B. `opus_deep_limit`).
Diese werden NICHT automatisch in Prompts substituiert — der Wert muss
manuell im Prompt-Text eingetragen werden.

---

## 5. Shutdown-Bedingungen

Die Chain stoppt automatisch wenn EINE dieser Bedingungen zutrifft:

| Bedingung | Beschreibung |
|-----------|-------------|
| **Runtime** | `runtime_hours` ueberschritten |
| **Max Rounds** | `max_rounds` erreicht |
| **Deadline** | `deadline`-Datum ueberschritten |
| **ALL_DONE** | Worker schreibt "ALL_DONE" ins Handoff |
| **STOP** | Manuell via `llmauto chain stop <name>` |
| **Max Blocks** | N aufeinanderfolgende BLOCKs im Handoff |

---

## 6. State & Logs

### State-Verzeichnis: `state/<chain-name>/`

| Datei | Inhalt |
|-------|--------|
| `status.txt` | RUNNING, READY, STOPPED, COMPLETED, ALL_DONE |
| `round_counter.txt` | Aktuelle Rundennummer |
| `start_time.txt` | Startzeit des Laufs |
| `handoff.md` | Kontext zwischen Links |
| `STOP` | Vorhanden = Stop-Signal (mit Grund) |
| `<link>-workspace/` | Workspace fuer continue-Mode Links |

### Logs: `logs/`

| Datei | Inhalt |
|-------|--------|
| `<chain>.log` | Runden-Protokoll |
| `<chain>_<link>.log` | Stdout/Stderr jedes Link-Aufrufs |

---

## 7. Worker-Stufen (Forschungspipeline)

Die Forschungspipeline nutzt 3 Worker-Stufen mit steigendem Aufwand.
Der Opus-Controller entscheidet pro Runde, welche Stufe welche Tasks bekommt.

### 7.1 Sonnet Worker (niedrig)

**Prompt:** `prompts/research_sonnet_worker.txt`
**Kapazitaet:** 8-10 Tasks pro Runde
**Einsatz:** Unbegrenzt

Typische Aufgaben:
- LaTeX-Korrekturen, Formatierung
- KI-Disclosure einfuegen/pruefen
- DOIs eintragen, Cross-Referenzen aktualisieren
- Bibliographie-Korrekturen
- Plan.txt / AUFGABEN.txt aktualisieren
- Zenodo-Metadaten vorbereiten
- Einfache LIT-Issues (mit klarer Anleitung vom Controller)

### 7.2 Opus Worker (mittel)

**Prompt:** `prompts/research_opus_worker.txt`
**Kapazitaet:** 3-5 Tasks pro Runde
**Einsatz:** Unbegrenzt

Typische Aufgaben:
- Anspruchsvolle Literatur-Integration (LIT-Issues)
- Formalisierungen (Gleichungen, Variablen, Modelle)
- Neue Abschnitte schreiben (Limitationen, Diskussion)
- Argumentationen vertiefen, Gegenargumente adressieren
- Konsistenz zwischen DE/EN-Versionen pruefen

### 7.3 Opus Deep (hoch)

**Prompt:** `prompts/research_opus_deep.txt`
**Kapazitaet:** 1-2 Projekte pro Runde
**Einsatz:** Limitiert (siehe `opus_deep_limit` in der Chain-Config)

Typische Aufgaben:
- Ganzes Projekt ueberarbeiten (alle LIT-Issues auf einmal)
- Paper nach Reviewer-Feedback grundlegend revidieren
- Projektserie-Konsistenz (z.B. 3 Pali-Psycho Artikel)
- Komplexe Formalisierungen (Spieltheorie, dynamische Systeme, Beweise)
- Paper kuerzen ohne Substanz zu verlieren

**Limit anpassen:**
1. `chains/forschung-todos.json` → `"opus_deep_limit": N`
2. `prompts/research_opus_controller.txt` → Wert bei "Max. N Einsaetze" aendern

---

## 8. Forschungspipeline — Gesamtuebersicht

### 8.1 Ordnerstruktur

```
.RESEARCH/
  CLAUDE.md                     ← Projektanweisungen (Session-Start)
  PUBLIKATIONSVERFAHREN.md      ← Konventionen, Workflow, Templates
  STATUS_UEBERSICHT.md          ← Dashboard aller Projekte
  AUFGABEN.txt                  ← Projektuebergreifende TODOs
  SCIENTIFIC_WORK_NOTES.md      ← Inhaltliche/wissenschaftliche Tasks (NEU)
  LEGENDE.txt                   ← Status-Praefixe
  LATEX_PDF_CHECKLISTE.md       ← Kompilierungs-Checkliste

  _templates/                   ← LaTeX-Templates, Disclosure-Snippets, Workflows
  _prompts/                     ← Review-Prompts (Antigravity, Gemini, Opus)
  _tools/                       ← paper_publisher.py (Zenodo-Upload)

  LLM/                          ← KI/LLM-Forschung
  Psychologie/                  ← Psychologische Forschung
  Sozialwissenschaft/           ← Politikwiss., Soziologie, Recht
  Natur&Technik/                ← Physik, Kosmologie, Bioinformatik
  Methoden/                     ← Forschungsmethoden
  Theologie/                    ← Religionswissenschaft
```

### 8.2 Projekt-Lifecycle

```
DRAFT → REV → PP-READY → PP → PP-LI → PP-FULL → SUB-[J] → ACC-[J] → PUB-[J]
                                                      ↓
                                                  REJ-[J] → zurueck zu PP
```

Prioritaetsmarker: `!!!` (Urgent) > `!!` (Fast Track) > `!` (High Priority)

### 8.3 Aufgabenquellen (Hierarchie)

```
1. SCIENTIFIC_WORK_NOTES.md     ← Inhaltliche Aufgaben (LIT-Issues, Formalisierungen)
       ↑ wird von Chain aktualisiert
2. AUFGABEN.txt (Root)          ← Projektuebergreifend (Disclosure, Zenodo, Cross-Refs)
       ↑ wird von Chain aktualisiert
3. Plan.txt / AKTIONSPLAN.md    ← Pro Projekt (Review-TODOs, Versionsarbeit)
       ↑ wird von Chain aktualisiert
4. STATUS_UEBERSICHT.md         ← Projektstatus (wird bei Aenderungen aktualisiert)
```

### 8.4 Was die Chain NICHT tut

- Journal-Einreichungen durchfuehren
- Ordner umbenennen (Statusaenderungen)
- Git push ausfuehren
- Zenodo-Uploads (braucht API-Token + User-Freigabe)
- Fakten erfinden oder unsichere Quellen als gesichert darstellen

### 8.5 Typischer Ablauf eines Chain-Laufs

```
Runde 1:
  Controller: Liest SCIENTIFIC_WORK_NOTES.md, STATUS_UEBERSICHT.md, AUFGABEN.txt
              Priorisiert: !!!-Projekte zuerst
              Weist zu: 10 Sonnet-Tasks, 4 Opus-Tasks, 1 Deep-Projekt

  Sonnet:     Arbeitet 10 mechanische Tasks ab (Disclosure, DOIs, BibTeX)
  Opus:       Arbeitet 4 LIT-Issues ab (Textpassagen, Formeln)
  Deep:       Ueberarbeitet ein ganzes Projekt (z.B. Frieden nach JPR-Ablehnung)

Runde 2:
  Controller: Prueft Ergebnisse, aktualisiert SCIENTIFIC_WORK_NOTES.md
              Weist neue Tasks zu (Deep-Budget aufgebraucht → nur Sonnet + Opus)
  ...

Runde N:
  Controller: Keine abarbeitbaren Tasks mehr → ALL_DONE
  (oder: Runtime-Limit erreicht → automatischer Stop)
```

---

## 9. Neue Chain erstellen

### 9.1 Minimales Beispiel

```json
{
    "chain_name": "mein-projekt",
    "description": "Beschreibung",
    "mode": "loop",
    "max_rounds": 20,
    "runtime_hours": 2,
    "defaults": {
        "permission_mode": "dontAsk",
        "allowed_tools": ["Read", "Edit", "Write", "Bash", "Glob", "Grep"],
        "timeout_seconds": 3600
    },
    "links": [
        {
            "name": "worker",
            "role": "worker",
            "model": "claude-sonnet-4-6",
            "prompt": "prompts/mein_worker.txt",
            "until_full": true
        }
    ]
}
```

### 9.2 Template

Ein Template liegt in `templates/worker-reviewer-loop.json`.

### 9.3 Prompt schreiben

Jeder Prompt sollte enthalten:
1. **Rolle:** Was der Agent tut
2. **Regeln:** Was er NICHT tun darf
3. **System-Kontext:** Pfade, Tools, Konventionen
4. **State Files:** Wo Handoff/Status liegen
5. **Workflow:** Schritt-fuer-Schritt Anleitung
6. **Handoff Format:** Wie das Handoff aussehen soll

---

## 10. Tipps & Troubleshooting

### Haeufige Probleme

| Problem | Loesung |
|---------|---------|
| Chain stoppt zu frueh (ALL_DONE) | `until_full: true` im Worker, explizite Anweisung "ALLE Tasks abarbeiten" im Prompt |
| Worker ueberschreibt Handoff mit "SKIPPED" | Skip-Schutz ist eingebaut, aber Prompt sollte klar machen was zu tun ist |
| Controller schreibt "COMPLETED" in status.txt | Status-Schutz setzt automatisch auf "RUNNING" zurueck |
| Opus-Deep wird zu oft eingesetzt | `opus_deep_limit` in Config UND Prompt anpassen |
| OneDrive-Lock auf State-Dateien | Retry hilft, oder OneDrive kurz pausieren |

### Performance-Tipps

- **Sonnet fuer Bulk:** Mechanische Tasks immer an Sonnet (schneller, guenstiger)
- **Opus fuer Qualitaet:** Inhaltliche Tasks an Opus (besseres Verstaendnis)
- **Deep sparsam:** Opus Deep nur fuer die wichtigsten Projekte (teuer, aber gruendlich)
- **Continue-Mode:** Nur fuer Controller (behaelt Kontext ueber Runden)
- **Until-Full:** Fuer alle Worker (maximale Ausnutzung des Kontextfensters)
- **Runtime planen:** 4-6h fuer normale Laeufe, 8h+ fuer grosse Backlogs

### Monitoring

```bash
# Status
python -m llmauto chain status forschung-todos

# Live-Log (letzte 50 Zeilen)
python -m llmauto chain log forschung-todos 50

# Handoff lesen (was wurde zuletzt gemacht?)
cat state/forschung-todos/handoff.md

# Alle Chains auflisten
python -m llmauto chain list
```

---

## 11. Dateiuebersicht

```
llmauto/
├── llmauto.py                          # CLI Entry Point
├── config.json                         # Globale Defaults
├── USER-DOCU.md                        # Diese Datei
├── core/
│   ├── runner.py                       # ClaudeRunner (subprocess)
│   ├── config.py                       # Config-Loader
│   ├── state.py                        # State-Management
│   └── chain_creator.py                # Interaktive Chain-Erstellung
├── modes/
│   └── chain.py                        # MarbleRun-Engine
├── chains/
│   ├── forschung-todos.json            # Forschungspipeline
│   ├── software-entwicklung.json       # Software-Pipeline
│   ├── controller-worker-loop.json     # Generischer Loop
│   ├── review-chain.json               # Einmaliges Review
│   └── _private/                       # Projektspezifische Chains
├── prompts/
│   ├── research_opus_controller.txt    # Forschung: Controller
│   ├── research_sonnet_worker.txt      # Forschung: Sonnet Worker
│   ├── research_opus_worker.txt        # Forschung: Opus Worker (mittel)
│   ├── research_opus_deep.txt          # Forschung: Opus Deep (hoch)
│   ├── software_opus_controller.txt    # Software: Controller
│   ├── software_sonnet_worker.txt      # Software: Sonnet Worker
│   ├── example_*.txt                   # Beispiel-Prompts
│   └── _private/                       # Projektspezifische Prompts
├── templates/
│   └── worker-reviewer-loop.json       # Chain-Template
├── state/                              # Runtime-State (nicht committed)
│   └── <chain-name>/
│       ├── status.txt
│       ├── round_counter.txt
│       ├── handoff.md
│       └── ...
└── logs/                               # Logs (nicht committed)
    ├── <chain>.log
    └── <chain>_<link>.log
```

---

*Erstellt: 2026-03-14 | Autor: Lukas Geiger + Claude Opus 4.6*
