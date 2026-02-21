# Automatisierung in Claude Code

> Referenz-Dokument | Erstellt: 2026-02-20 | Autor: Lukas Geiger

---

## 1. Automatisierung ohne staendige Bestaetigungen

Claude Code bietet mehrere Stufen, um die Anzahl der Permission-Prompts zu reduzieren.

### 1.1 Permission Modes

Gesetzt via `settings.json` (`defaultMode`) oder CLI-Flag `--permission-mode`:

| Mode | Verhalten |
|------|-----------|
| `default` | Fragt bei jedem Tool um Bestaetigung |
| `acceptEdits` | Akzeptiert Datei-Edits (Read/Edit/Write) automatisch, fragt nur bei Bash |
| `plan` | Claude darf NUR lesen und planen, keine Aenderungen |
| `dontAsk` | Verweigert nicht vorgenehmigte Tools automatisch (kein Prompt) |
| `bypassPermissions` | Ueberspringt ALLE Permission-Checks (nur fuer Sandbox-Umgebungen!) |

### 1.2 Granulare Permission Rules

In `settings.json` koennen exakte Allow/Deny-Regeln definiert werden:

```json
{
  "permissions": {
    "allow": [
      "Bash(npm run *)",
      "Bash(git commit *)",
      "Read",
      "Edit(/src/**)",
      "WebFetch(domain:github.com)"
    ],
    "deny": [
      "Bash(rm -rf *)",
      "Bash(git push *)"
    ]
  }
}
```

**Prioritaet:** `deny` > `ask` > `allow` (First Match Wins)

### 1.3 CLI Flags

```bash
# Alles erlauben (gefaehrlich -- nur in Sandbox!)
claude --dangerously-skip-permissions "Mein Task"

# Bestimmte Tools vorab genehmigen
claude -p "Task" --allowedTools "Bash(npm *),Read,Edit"

# Permission Mode beim Start setzen
claude --permission-mode acceptEdits "Task"
```

### 1.4 PreToolUse Hooks

Shell-Scripts die vor jeder Tool-Ausfuehrung laufen und automatisch genehmigen oder blockieren:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "jq -r '.tool_input.command' | grep -q 'npm' && exit 0 || exit 2"
          }
        ]
      }
    ]
  }
}
```

- **Exit 0** = Tool erlaubt
- **Exit 2** = Tool blockiert

### 1.5 Headless Mode (-p Flag)

Fuer non-interactive, automatisierte Ausfuehrung:

```bash
claude -p "Mein Task" --allowedTools "Bash,Read,Edit" --output-format json
```

Claude arbeitet komplett automatisch ohne Prompts, wenn die Tools vorab genehmigt sind.

---

## 2. Desktop Cowork vs. Agent Teams

### 2.1 Desktop Cowork

- Funktion der **Claude Desktop App**, nicht des CLI
- **Single-Session**: Wechsel einer Konversation zwischen Desktop-App und CLI
- `/desktop` im CLI uebergibt die Session an die Desktop-App
- Umgekehrt kann Desktop eine CLI-Session starten
- **1 Claude-Instanz, 1 Konversation**, nur anderes Interface

**Use Case:** Wenn man zwischen grafischer Oberflaeche und Terminal wechseln will, ohne den Kontext zu verlieren.

### 2.2 Agent Teams (Experimental)

- **Mehrere Claude Code Instanzen** arbeiten parallel und autonom
- Jeder Teammate ist eine **eigene, unabhaengige Claude-Session**
- Kommunikation ueber **Shared Task List** und **SendMessage**
- Team Lead koordiniert, Teammates arbeiten autonom
- Aktivierung: `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in Settings

**Architektur:**

```
Team Lead (Haupt-Session)
├── Teammate 1 (eigene Session)
├── Teammate 2 (eigene Session)
└── Teammate 3 (eigene Session)
    └── Shared Task List (~/.claude/tasks/{team-name}/)
```

### 2.3 Vergleich

| Aspekt | Desktop Cowork | Agent Teams |
|--------|---------------|-------------|
| **Instanzen** | 1 | N (beliebig viele) |
| **Parallelitaet** | Keine | Voll parallel |
| **Kommunikation** | UI-Wechsel | Messages + Task List |
| **Kosten** | Normal | N x Normal |
| **Kontext** | Geteilt (gleiche Session) | Getrennt (je eigenes Window) |
| **Status** | Stabil | Experimental |
| **Use Case** | UI-Wechsel | Komplexe parallele Arbeit |

---

## 3. Endless Mode / Unendliches Arbeiten

**Es gibt keinen nativen Endless Mode in Claude Code.** Aber es gibt mehrere Workarounds:

### 3.1 Stop Hooks (eleganteste Loesung)

Ein Stop Hook wird ausgeloest wenn Claude aufhoeren will. Man kann Claude zwingen weiterzumachen:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "prompt",
            "prompt": "Sind alle Tasks abgeschlossen? Wenn nein: {\"ok\": false, \"reason\": \"was noch zu tun ist\"}"
          }
        ]
      }
    ]
  }
}
```

Wenn Claude antwortet "nicht fertig", arbeitet es automatisch weiter.

### 3.2 CLI-Schleife (Headless)

```bash
while true; do
  result=$(claude -p "Pruefe ob Tasks fertig. Wenn nicht, weiterarbeiten." \
    --continue \
    --allowedTools "Bash,Read,Edit" \
    --output-format json)

  echo "$result" | grep -q "FERTIG" && break
  sleep 5
done
```

### 3.3 Remote Sessions

```bash
claude --environment remote "Langwieriger Task"
```

- Laeuft in der **Cloud** weiter, auch wenn die App geschlossen wird
- Spaeter mit `--resume` fortsetzen
- Keine lokalen Token-Limits pro Sitzung

### 3.4 Agent Teams mit Selbstzuweisung

Teammates koennen sich selbst neue Tasks aus der Shared Task List laden:

```
Starte ein Agent Team. Der Teammate soll:
1. TaskList pruefen
2. Naechsten offenen Task bearbeiten
3. Task als completed markieren
4. Zurueck zu Schritt 1
```

### 3.5 Einschraenkungen

- **Context Window** ist begrenzt (wird bei Vollauslastung kompaktifiziert)
- **API-Kosten** laufen weiter -- kein kostenloses Endlos-Arbeiten
- **Kompaktifizierung** kann Kontext verlieren -- bei langen Sessions regelmaessig pruefen

---

## Zusammenfassung / Quick Reference

| Ziel | Loesung |
|------|---------|
| Weniger Bestaetigungen | `acceptEdits` Mode + Permission Rules |
| Gar keine Bestaetigungen | `--dangerously-skip-permissions` (nur Sandbox!) |
| Bestimmte Tools freigeben | `--allowedTools` oder `allow`-Rules in settings.json |
| Automatische Entscheidungen | PreToolUse Hooks |
| UI-Wechsel Desktop/CLI | Desktop Cowork |
| Parallele Agenten-Arbeit | Agent Teams (experimental) |
| Endloses Arbeiten | Stop Hooks oder CLI-Schleifen |
| Hintergrund-Arbeit | Remote Sessions |

---

*Generiert mit Claude Code (Opus 4.6) am 2026-02-20*
