# llmauto Chain-Uebersicht

**Stand:** 2026-02-21 | **Engine:** Marble-Run (sequentielle Agentenketten)

---

## Architektur-Prinzip

Jede Chain besteht aus **Links** (Glieder), die sequentiell durchlaufen werden. Pro Runde laeuft jeder Link einmal. Die Kommunikation erfolgt ueber `handoff.md` Dateien.

### Schluessel-Mechanismen

| Mechanismus | Beschreibung |
|---|---|
| `continue: true` | Gleiche Claude-Session ueber alle Runden (akkumuliert Kontext) |
| `continue: false` | Neue Claude-Session pro Runde (frischer Kontext) |
| `until_full` | Agent arbeitet bis Kontextfenster voll, dann sauberes Handoff |
| `fallback_model` | Fallback wenn primaeres Modell nicht verfuegbar |
| `task_pool` | Aufgaben-Queue aus externer Datei (z.B. MASTERPLAN.txt) |
| `mode: once` | Genau 1 Durchlauf, dann COMPLETED |
| `mode: loop` | Wiederholte Durchlaeufe bis Abbruchkriterium |

### Shutdown-Bedingungen (automatisch)

1. Manuelle STOP-Datei (`state/<chain>/STOP`)
2. Status ALL_DONE (Worker meldet Fertigstellung)
3. Deadline ueberschritten
4. Laufzeit-Limit erreicht
5. Max-Runden erreicht
6. Zu viele aufeinanderfolgende BLOCKs im Handoff

---

## Alle Chains im Ueberblick

### 1. forschung-review (Forschungs-Review-Zyklus)

**Zweck:** Iteratives Review + Verbesserung aller 9 Forschungsprojekte

| Eigenschaft | Wert |
|---|---|
| Modus | loop |
| Max. Runden | 3 |
| Laufzeit | 12h |
| Projekte | 9 |

**Links:**

| # | Name | Modell | Rolle | continue | until_full |
|---|---|---|---|---|---|
| 1 | opus-reviewer | Opus 4.6 | Reviewer | **false** | - |
| 2 | sonnet-worker | Sonnet 4.5 | Worker | true | ja |

**Ablauf pro Runde:**
1. **Frischer Opus** reviewt alle 9 Projekte streng (kein Kontext von vorherigen Runden)
2. **Sonnet Worker** arbeitet die Verbesserungen ein (akkumuliert Kontext)

**Designentscheidung:** Opus bekommt pro Runde einen frischen Blick (`continue: false`), damit kein Bias aus vorherigen Reviews die Bewertung beeinflusst. Der Sonnet Worker hingegen behaelt Kontext (`continue: true`), um zu wissen was er schon korrigiert hat.

**Nachfolge-Chain:** `review-only` als isolierter Kontroll-Review

---

### 2. review-only (Isolierter Kontroll-Review)

**Zweck:** Finale Qualitaetskontrolle -- jedes Projekt bekommt seinen eigenen Opus-Reviewer

| Eigenschaft | Wert |
|---|---|
| Modus | once |
| Max. Runden | 1 |
| Laufzeit | 6h |
| Projekte | 9 |

**Links:**

| # | Name | Modell | Rolle | continue | until_full |
|---|---|---|---|---|---|
| 1 | review-coordinator | Opus 4.6 | Coordinator | false | ja |

**Ablauf:**
1. Opus-Koordinator startet **9 isolierte Opus-Subagenten** (je 1 pro Projekt)
2. Kein Reviewer kennt die Ergebnisse der anderen (kein Cross-Bias)
3. Koordinator aggregiert und erstellt Gesamtbericht

**Einsatz:** Als letzter Kontrolllauf NACH `forschung-review`

---

### 3. forschung-publish (Publikations-Pipeline)

**Zweck:** Automatisierte Veroeffentlichung (Zenodo, LinkedIn, Updates)

| Eigenschaft | Wert |
|---|---|
| Modus | loop |
| Max. Runden | 15 |
| Laufzeit | 4h |
| Modi | review / zenodo / linkedin / update |

**Links:**

| # | Name | Modell | Rolle | continue | until_full |
|---|---|---|---|---|---|
| 1 | opus-controller | Opus 4.6 | Controller | true | - |
| 2 | opus-worker | Opus 4.6 | Worker | - | ja |
| 3 | sonnet-worker | Sonnet 4.5 | Worker | - | ja |

**Ablauf:** Controller weist Aufgaben zu (Opus fuer komplexe, Sonnet fuer einfache). Skip-Pattern: Nicht zugewiesener Worker bricht sofort ab.

---

### 4. einzelaufgaben (Einzel-Task-Queue)

**Zweck:** Gemischte Aufgaben aus MODULAR_AGENTS abarbeiten

| Eigenschaft | Wert |
|---|---|
| Modus | loop |
| Max. Runden | 10 |
| Laufzeit | 5h |

**Links:**

| # | Name | Modell | Rolle | continue | until_full |
|---|---|---|---|---|---|
| 1 | opus-controller | Opus 4.6 | Controller | true | - |
| 2 | opus-worker | Opus 4.6 | Worker | - | ja |
| 3 | sonnet-worker | Sonnet 4.5 | Worker | - | ja |

**Ablauf:** Skip-Pattern wie bei forschung-publish. Controller entscheidet pro Aufgabe ob Opus oder Sonnet.

---

### 5. masterplan-v2 (BACH MASTERPLAN -- 3 Sonnet + 1 Opus)

**Zweck:** BACH-Entwicklungsaufgaben aus MASTERPLAN.txt abarbeiten

| Eigenschaft | Wert |
|---|---|
| Modus | loop |
| Max. Runden | 50 |
| Laufzeit | 6h |
| Deadline | 2026-03-31 |
| Task-Pool | MASTERPLAN.txt |

**Links:**

| # | Name | Modell | Rolle | continue | until_full |
|---|---|---|---|---|---|
| 1 | sonnet-worker-1 | Sonnet 4.5 | Worker | - | ja |
| 2 | sonnet-worker-2 | Sonnet 4.5 | Worker | - | ja |
| 3 | sonnet-worker-3 | Sonnet 4.5 | Worker | - | ja |
| 4 | opus-controller | Opus 4.6 | Controller | true | - |

**Ablauf:** 3 Sonnet-Worker arbeiten je 10 Tasks ab, dann prueft Opus alles und weist neue zu. Telegram-Updates.

---

### 6. masterplan-3s1o (BACH MASTERPLAN -- Variante)

**Zweck:** Identisch zu masterplan-v2, andere Prompts

| Eigenschaft | Wert |
|---|---|
| Modus | loop |
| Max. Runden | 50 |
| Laufzeit | 6h |
| Deadline | 2026-03-31 |
| Task-Pool | MASTERPLAN.txt |

**Links:** Identisch zu masterplan-v2 (3x Sonnet Worker + 1x Opus Controller)

**Unterschied:** Nutzt `worker_sonnet_10.txt` und `reviewer_opus_control.txt` statt `masterplan_v2_*` Prompts.

---

### 7. ati-software (ATI Software-Entwicklung)

**Zweck:** Software-Entwicklungsaufgaben fuer ATI (BACH-Erweiterungen)

| Eigenschaft | Wert |
|---|---|
| Modus | loop |
| Max. Runden | 20 |
| Laufzeit | 3h |

**Links:**

| # | Name | Modell | Rolle | continue | until_full |
|---|---|---|---|---|---|
| 1 | sonnet-worker-1 | Sonnet 4.5 | Worker | - | ja |
| 2 | sonnet-worker-2 | Sonnet 4.5 | Worker | - | ja |
| 3 | sonnet-worker-3 | Sonnet 4.5 | Worker | - | ja |
| 4 | opus-controller | Opus 4.6 | Controller | true | - |

**Ablauf:** Wie masterplan-v2, aber mit ATI-spezifischen Prompts.

---

### 8. bach-masterplan (BACH MASTERPLAN -- Original)

**Zweck:** Aelteste Chain-Variante mit abwechselndem Worker/Reviewer-Muster

| Eigenschaft | Wert |
|---|---|
| Modus | loop |
| Max. Runden | 200 |
| Laufzeit | 6h |
| Deadline | 2026-03-31 |
| Task-Pool | MASTERPLAN.txt |

**Links:**

| # | Name | Modell | Rolle | continue | until_full |
|---|---|---|---|---|---|
| 1 | opus-worker | Opus 4.6 | Worker | - | ja |
| 2 | sonnet-reviewer | Sonnet 4.5 | Reviewer | - | - |
| 3 | sonnet-worker | Sonnet 4.5 | Worker | - | ja |
| 4 | opus-reviewer | Opus 4.6 | Reviewer | - | - |

**Ablauf:** Opus Work -> Sonnet Review -> Sonnet Work -> Opus Review. Kein `continue` bei keinem Link.

---

## Vergleichstabelle

| Chain | Modus | Links | Runden | Laufzeit | Opus-Links | Sonnet-Links | continue | Fallback |
|---|---|---|---|---|---|---|---|---|
| **forschung-review** | loop | 2 | 3 | 12h | 1 (reviewer) | 1 (worker) | Sonnet only | - |
| **review-only** | once | 1 | 1 | 6h | 1 (coordinator) | 0 | - | Sonnet |
| **forschung-publish** | loop | 3 | 15 | 4h | 2 (ctrl+worker) | 1 (worker) | Controller | - |
| **einzelaufgaben** | loop | 3 | 10 | 5h | 2 (ctrl+worker) | 1 (worker) | Controller | - |
| **masterplan-v2** | loop | 4 | 50 | 6h | 1 (controller) | 3 (worker) | Controller | Opus->Sonnet |
| **masterplan-3s1o** | loop | 4 | 50 | 6h | 1 (controller) | 3 (worker) | Controller | Opus->Sonnet |
| **ati-software** | loop | 4 | 20 | 3h | 1 (controller) | 3 (worker) | Controller | Opus->Sonnet |
| **bach-masterplan** | loop | 4 | 200 | 6h | 2 (work+review) | 2 (work+review) | - | Opus->Sonnet |

---

## Empfohlener Workflow: Forschungs-Review

```
Phase 1: forschung-review (3 Runden)
  Runde 1: Opus (frisch) reviewt -> Sonnet fixt
  Runde 2: Opus (frisch) reviewt -> Sonnet fixt (kennt vorherige Fixes)
  Runde 3: Opus (frisch) reviewt -> Sonnet fixt

Phase 2: review-only (Kontrolle)
  1 Koordinator -> 9 isolierte Opus-Reviewer (kein Cross-Bias)
  Jedes Projekt bekommt seinen eigenen Opus
```

---

## Globale Konfiguration (config.json)

| Einstellung | Wert |
|---|---|
| Default-Modell | claude-sonnet-4-5-20250929 |
| Permission-Mode | dontAsk |
| Timeout pro Link | 7200s (2h) |
| Telegram | deaktiviert |
| Pfad-Normalisierung | automatisch (Laptop/Workstation) |

---

*Generiert: 2026-02-21 | llmauto Chain-Dokumentation*
