# Marble-Run: Projektneutrales Chain-Config Schema
# Entwurf 2026-02-17

## Konzept
Jede Kette (Chain) besteht aus N Gliedern (Links).
Jedes Glied hat: Modell, Prompt, Aufgabenpool, Rolle.
Ketten koennen offen (einmalig) oder geschlossen (Loop) sein.
Fertige Ketten werden als wiederverwendbare Patterns gespeichert.

---

## Config-Struktur (JSON)

```json
{
    "chain_name": "bach-masterplan",
    "description": "BACH MASTERPLAN Abarbeitung mit Worker/Reviewer Zyklus",
    "version": "1.0",

    "mode": "loop",
    "max_rounds": 200,
    "runtime_hours": 6,
    "deadline": "2026-03-31",

    "defaults": {
        "model": "claude-sonnet-4-6",
        "permission_mode": "dontAsk",
        "allowed_tools": ["Read", "Edit", "Write", "Bash", "Glob", "Grep"],
        "timeout_seconds": 1800,
        "fallback_model": null
    },

    "links": [
        {
            "name": "opus-worker",
            "role": "worker",
            "model": "claude-opus-4-6",
            "fallback_model": "claude-sonnet-4-6",
            "prompt": "worker_opus",
            "task_pool": "masterplan",
            "description": "Opus arbeitet an einer Aufgabe"
        },
        {
            "name": "sonnet-reviewer",
            "role": "reviewer",
            "model": "claude-sonnet-4-6",
            "prompt": "reviewer_sonnet",
            "task_pool": "masterplan",
            "description": "Sonnet reviewed die Aenderung"
        },
        {
            "name": "sonnet-worker",
            "role": "worker",
            "prompt": "worker_sonnet",
            "task_pool": "masterplan",
            "description": "Sonnet arbeitet an naechster Aufgabe"
        },
        {
            "name": "opus-reviewer",
            "role": "reviewer",
            "model": "claude-opus-4-6",
            "fallback_model": "claude-sonnet-4-6",
            "prompt": "reviewer_opus",
            "task_pool": "masterplan",
            "telegram_update": true,
            "description": "Opus reviewed (Architektur-Blick)"
        }
    ],

    "prompts": {
        "worker_opus": {
            "type": "file",
            "path": "prompts/worker_opus.txt"
        },
        "reviewer_sonnet": {
            "type": "file",
            "path": "prompts/reviewer_sonnet.txt"
        },
        "worker_sonnet": {
            "type": "file",
            "path": "prompts/worker_sonnet.txt"
        },
        "reviewer_opus": {
            "type": "file",
            "path": "prompts/reviewer_opus.txt"
        },
        "generic_worker": {
            "type": "template",
            "template": "Lies {{task_file}} und bearbeite die naechste offene Aufgabe. Aktualisiere {{handoff_file}} nach Abschluss."
        }
    },

    "task_pools": {
        "masterplan": {
            "type": "file",
            "path": "C:\\Users\\User\\OneDrive\\KI&AI\\BACH_Dev\\MASTERPLAN.txt",
            "description": "BACH MASTERPLAN Aufgaben"
        },
        "research": {
            "type": "directory",
            "path": "C:\\Users\\User\\OneDrive\\Forschung\\tasks\\",
            "pattern": "*.md",
            "description": "Forschungs-Aufgaben"
        },
        "software": {
            "type": "github_issues",
            "repo": "lukisch/bach",
            "labels": ["todo"],
            "description": "GitHub Issues als Aufgabenpool"
        }
    },

    "telegram": {
        "enabled": false,
        "bot_token_env": "BACH_TELEGRAM_BOT_TOKEN",
        "chat_id": "595767047",
        "update_every_n_links": 4
    },

    "shutdown": {
        "max_consecutive_blocks": 5,
        "stop_file": "state/STOP"
    }
}
```

---

## Ketten-Typen (mode)

### "loop" (geschlossen)
- Nach dem letzten Glied -> zurueck zum ersten
- Laeuft bis: Zeitlimit, Max-Runden, STOP-Datei, Alle Tasks done
- Usecase: MASTERPLAN abarbeiten, Forschungs-Pipeline

### "once" (offen)
- Jedes Glied einmal, dann fertig
- Usecase: Paper schreiben (Recherche -> Outline -> Draft -> Review)

### "conditional" (bedingt)
- Nach jedem Glied: Pruefen ob Bedingung erfuellt
- Weiter oder zurueck je nach Status
- Usecase: Worker -> Reviewer -> wenn NEEDS_FIX zurueck zu Worker

---

## Verschiedene Aufgabenpools pro Glied

Usecase: Cross-Domain Kette
```json
{
    "links": [
        {"name": "researcher",  "task_pool": "research",  "prompt": "research_worker"},
        {"name": "developer",   "task_pool": "software",  "prompt": "dev_worker"},
        {"name": "bach-admin",  "task_pool": "masterplan", "prompt": "bach_worker"},
        {"name": "reviewer",    "task_pool": "all",        "prompt": "cross_reviewer"}
    ]
}
```

---

## CLI-Befehle (Entwurf)

```
python marble.py start [chain]         Startet eine gespeicherte Kette
python marble.py start --bg [chain]    Im Hintergrund
python marble.py status                Aktueller Status
python marble.py stop [grund]          Stoppt nach aktuellem Glied
python marble.py log [N]               Letzte N Log-Eintraege
python marble.py reset                 State zuruecksetzen

python marble.py chain list            Alle gespeicherten Ketten anzeigen
python marble.py chain create          Interaktiv neue Kette erstellen
python marble.py chain edit [name]     Kette bearbeiten
python marble.py chain copy [src] [dst] Kette kopieren/anpassen
python marble.py chain delete [name]   Kette loeschen
python marble.py chain show [name]     Kette im Detail anzeigen

python marble.py link add [chain]      Glied zur Kette hinzufuegen
python marble.py link remove [chain] [N] Glied entfernen
python marble.py link set [chain] [N] [key] [value]  Glied-Eigenschaft setzen

python marble.py prompt list           Alle Prompts anzeigen
python marble.py prompt add [name]     Neuen Prompt erstellen
python marble.py prompt edit [name]    Prompt bearbeiten

python marble.py pool list             Alle Aufgabenpools anzeigen
python marble.py pool add [name]       Neuen Pool hinzufuegen
```

---

## Patterns (vorgefertigte Ketten)

### "worker-reviewer-loop" (Standard)
2 Glieder: Worker -> Reviewer -> Loop
Einfachste produktive Kette.

### "quad-cycle" (aktuell fuer BACH)
4 Glieder: Opus Worker -> Sonnet Review -> Sonnet Worker -> Opus Review -> Loop

### "research-pipeline" (offen)
4 Glieder: Recherche -> Zusammenfassung -> Analyse -> Bericht -> Ende

### "cross-domain-loop"
N Glieder mit verschiedenen Pools: Forschung -> Entwicklung -> BACH -> Review -> Loop

---

## Speicherort
```
marble_run/
  chains/
    bach-masterplan.json    (aktuelle BACH-Kette)
    research-pipeline.json  (Forschungs-Kette)
    ...
  prompts/
    worker_opus.txt
    reviewer_sonnet.txt
    ...
  templates/
    worker.txt.template     (Vorlagen-Prompts)
    reviewer.txt.template
```
