"""
llmauto.core.chain_creator -- Interaktiver Dialog zum Erstellen neuer Ketten.
==============================================================================
Wird aufgerufen ueber: python -m llmauto chain create
"""
import json
import sys
from pathlib import Path
from datetime import datetime

from llmauto.core.config import BASE_DIR

CHAINS_DIR = BASE_DIR / "chains"
PROMPTS_DIR = BASE_DIR / "prompts"
TEMPLATES_DIR = PROMPTS_DIR / "templates"

MODELS = {
    "1": ("claude-sonnet-4-6", "Sonnet (schnell, guenstig)"),
    "2": ("claude-opus-4-6", "Opus (stark, teurer)"),
    "3": ("claude-haiku-4-5-20251001", "Haiku (am schnellsten)"),
}

ROLES = ["worker", "reviewer", "controller"]


def ask(prompt: str, default: str = "") -> str:
    """Fragt den User mit optionalem Default."""
    suffix = f" [{default}]" if default else ""
    val = input(f"  {prompt}{suffix}: ").strip()
    return val if val else default


def ask_int(prompt: str, default: int = 0) -> int:
    """Fragt nach einer Zahl."""
    val = ask(prompt, str(default))
    try:
        return int(val)
    except ValueError:
        return default


def ask_yn(prompt: str, default: bool = True) -> bool:
    """Ja/Nein Frage."""
    d = "J/n" if default else "j/N"
    val = input(f"  {prompt} ({d}): ").strip().lower()
    if not val:
        return default
    return val in ("j", "ja", "y", "yes")


def ask_choice(prompt: str, options: dict) -> str:
    """Auswahl aus Optionen."""
    print(f"\n  {prompt}")
    for key, (_, label) in options.items():
        print(f"    [{key}] {label}")
    val = input("  Auswahl: ").strip()
    return val if val in options else list(options.keys())[0]


def ask_multiline(prompt: str) -> str:
    """Mehrzeiligen Text eingeben (leere Zeile = Ende)."""
    print(f"  {prompt}")
    print("  (Leere Zeile = Ende)")
    lines = []
    while True:
        line = input("  > ")
        if line == "":
            break
        lines.append(line)
    return "\n".join(lines)


def list_saved_prompts() -> list:
    """Listet gespeicherte Prompt-Vorlagen."""
    templates = []
    for d in [PROMPTS_DIR, TEMPLATES_DIR]:
        if d.exists():
            for f in sorted(d.glob("*.txt")):
                templates.append(f)
    return templates


def save_prompt_template(name: str, content: str) -> Path:
    """Speichert Prompt als Vorlage."""
    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = name.replace(" ", "_").lower()
    path = TEMPLATES_DIR / f"{safe_name}.txt"
    path.write_text(content, encoding="utf-8")
    return path


def create_chain():
    """Hauptdialog zum Erstellen einer Kette."""
    print()
    print("  ===================================================")
    print("   llmauto Chain Creator")
    print("  ===================================================")
    print()

    # --- Grunddaten ---
    chain_name = ask("Ketten-Name (z.B. mein-projekt)", "neue-kette")
    description = ask("Beschreibung", "")

    # --- Modus ---
    print()
    print("  --- Modus ---")
    print("    [1] Einmalig (once) -- Jedes Glied laeuft einmal")
    print("    [2] Loop -- Glieder wiederholen sich bis Zeitlimit/Rundenlimit")
    mode_choice = ask("Modus", "2")
    is_loop = mode_choice != "1"
    mode = "loop" if is_loop else "once"

    # --- Loop-Parameter ---
    max_rounds = 1
    runtime_hours = 1
    max_consecutive_blocks = 3
    stop_criterion = ""
    if is_loop:
        print()
        print("  --- Loop-Parameter ---")
        max_rounds = ask_int("Max Runden (0 = unbegrenzt)", 20)
        runtime_hours = ask_int("Laufzeit in Stunden", 3)
        max_consecutive_blocks = ask_int("Max aufeinanderfolgende BLOCKs vor Abbruch", 3)

        print()
        print("  --- Abbruch-Kriterium ---")
        print("    [1] Nur Zeit/Runden (Standard)")
        print("    [2] Wenn 'ALL_DONE' in state/status.txt")
        print("    [3] Eigenes Kriterium (Text in handoff.md)")
        stop_choice = ask("Abbruch-Kriterium", "1")
        if stop_choice == "2":
            stop_criterion = "ALL_DONE"
        elif stop_choice == "3":
            stop_criterion = ask("Abbruch-Text (wird in handoff.md gesucht)", "FINISHED")
    else:
        runtime_hours = ask_int("Max Laufzeit in Stunden", 2)

    # --- Prompt-Modus ---
    print()
    print("  --- Prompts ---")
    print("    [1] Ein Prompt fuer ALLE Glieder (gleiche Aufgabe)")
    print("    [2] Eigener Prompt pro Glied (verschiedene Aufgaben)")
    prompt_mode = ask("Prompt-Modus", "1")
    shared_prompt = prompt_mode == "1"

    shared_prompt_text = ""
    shared_prompt_name = ""
    if shared_prompt:
        print()
        templates = list_saved_prompts()
        if templates:
            print("  Gespeicherte Vorlagen:")
            for i, t in enumerate(templates, 1):
                print(f"    [{i}] {t.stem}")
            print(f"    [0] Neuen Prompt eingeben")
            tpl_choice = ask("Vorlage waehlen oder 0 fuer neu", "0")
            if tpl_choice != "0":
                try:
                    idx = int(tpl_choice) - 1
                    shared_prompt_text = templates[idx].read_text(encoding="utf-8")
                    shared_prompt_name = templates[idx].stem
                    print(f"  Vorlage geladen: {shared_prompt_name}")
                except (ValueError, IndexError):
                    pass

        if not shared_prompt_text:
            print()
            shared_prompt_text = ask_multiline("Prompt eingeben:")
            shared_prompt_name = ask("Prompt-Name (fuer Referenz)", chain_name + "_prompt")

            if shared_prompt_text and ask_yn("Prompt als Vorlage speichern?", True):
                saved = save_prompt_template(shared_prompt_name, shared_prompt_text)
                print(f"  Gespeichert: {saved}")

    # --- Glieder ---
    print()
    print("  --- Glieder (Links) ---")
    num_links = ask_int("Anzahl Glieder", 2)

    links = []
    prompts_dict = {}

    for i in range(1, num_links + 1):
        print(f"\n  --- Glied {i}/{num_links} ---")
        link_name = ask(f"  Name", f"link-{i}")

        print(f"  Rolle:")
        print(f"    [1] worker    [2] reviewer    [3] controller")
        role_choice = ask("  Rolle", "1")
        role_map = {"1": "worker", "2": "reviewer", "3": "controller"}
        role = role_map.get(role_choice, "worker")

        model_choice = ask_choice("Modell:", MODELS)
        model_id = MODELS[model_choice][0]

        link = {
            "name": link_name,
            "role": role,
            "model": model_id,
            "description": ask(f"  Beschreibung (kurz)", f"{role} Glied {i}"),
        }

        if role == "worker":
            link["until_full"] = True

        # Prompt
        if shared_prompt:
            prompt_key = shared_prompt_name
            if prompt_key not in prompts_dict:
                prompts_dict[prompt_key] = shared_prompt_text
            link["prompt"] = prompt_key
        else:
            print()
            templates = list_saved_prompts()
            use_template = False
            if templates:
                print(f"  Prompt fuer '{link_name}':")
                print(f"    [0] Neuen Prompt eingeben")
                for j, t in enumerate(templates, 1):
                    print(f"    [{j}] Vorlage: {t.stem}")
                tpl_choice = ask("  Auswahl", "0")
                if tpl_choice != "0":
                    try:
                        idx = int(tpl_choice) - 1
                        prompt_text = templates[idx].read_text(encoding="utf-8")
                        prompt_key = templates[idx].stem
                        use_template = True
                        print(f"  Vorlage geladen: {prompt_key}")
                    except (ValueError, IndexError):
                        pass

            if not use_template:
                prompt_text = ask_multiline(f"Prompt fuer '{link_name}':")
                prompt_key = f"{chain_name}_{link_name}"

                if prompt_text and ask_yn("Prompt als Vorlage speichern?", False):
                    saved = save_prompt_template(prompt_key, prompt_text)
                    print(f"  Gespeichert: {saved}")

            prompts_dict[prompt_key] = prompt_text
            link["prompt"] = prompt_key

        links.append(link)

    # --- After-Agent ---
    after_agent = None
    if is_loop:
        print()
        if ask_yn("After-Agent nach Loop-Ende? (eigene Aufgabe nach Abschluss)", False):
            print()
            print("  --- After-Agent ---")
            aa_name = ask("Name", "after-agent")
            aa_model_choice = ask_choice("Modell:", MODELS)
            aa_model = MODELS[aa_model_choice][0]

            print()
            print("  --- Trigger-Event ---")
            print("    [1] Nach normalem Loop-Ende (Zeit/Runden)")
            print("    [2] Nach ALL_DONE")
            print("    [3] Nach jedem Abbruch (auch BLOCKED)")
            trigger_choice = ask("Trigger", "1")
            trigger_map = {
                "1": "loop_complete",
                "2": "all_done",
                "3": "any_end",
            }
            trigger = trigger_map.get(trigger_choice, "loop_complete")

            aa_prompt_text = ask_multiline("Prompt fuer After-Agent:")
            aa_prompt_key = f"{chain_name}_after"

            if aa_prompt_text and ask_yn("Prompt als Vorlage speichern?", False):
                save_prompt_template(aa_prompt_key, aa_prompt_text)

            prompts_dict[aa_prompt_key] = aa_prompt_text

            after_agent = {
                "name": aa_name,
                "role": "worker",
                "model": aa_model,
                "prompt": aa_prompt_key,
                "trigger": trigger,
                "description": ask("Beschreibung", "Laeuft nach Loop-Ende"),
            }

    # --- JSON zusammenbauen ---
    chain = {
        "chain_name": chain_name,
        "description": description,
        "mode": mode,
        "max_rounds": max_rounds,
        "runtime_hours": runtime_hours,
    }

    if is_loop:
        chain["max_consecutive_blocks"] = max_consecutive_blocks
        if stop_criterion:
            chain["stop_criterion"] = stop_criterion

    chain["links"] = links

    if after_agent:
        chain["after_agent"] = after_agent

    # Prompts-Sektion: Referenz auf Dateien oder Inline
    chain["prompts"] = {}
    for key, text in prompts_dict.items():
        prompt_file = PROMPTS_DIR / f"{key}.txt"
        if not prompt_file.exists() and text:
            prompt_file.parent.mkdir(parents=True, exist_ok=True)
            prompt_file.write_text(text, encoding="utf-8")
        chain["prompts"][key] = {"type": "file", "path": f"prompts/{key}.txt"}

    chain["_created"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    chain["_creator"] = "chain_creator"

    # --- Vorschau ---
    print()
    print("  ===================================================")
    print("   Vorschau")
    print("  ===================================================")
    print()
    print(json.dumps(chain, indent=4, ensure_ascii=False))
    print()

    if not ask_yn("Kette speichern?", True):
        print("  Abgebrochen.")
        return None

    # --- Speichern ---
    CHAINS_DIR.mkdir(parents=True, exist_ok=True)
    chain_file = CHAINS_DIR / f"{chain_name}.json"
    if chain_file.exists():
        if not ask_yn(f"  '{chain_name}' existiert bereits. Ueberschreiben?", False):
            print("  Abgebrochen.")
            return None

    chain_file.write_text(
        json.dumps(chain, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )
    print(f"\n  Gespeichert: {chain_file}")
    print(f"  Starten mit: python -m llmauto chain start {chain_name}")

    return chain


def list_templates():
    """Zeigt alle gespeicherten Prompt-Vorlagen."""
    print()
    print("  Gespeicherte Prompt-Vorlagen:")
    print()
    templates = list_saved_prompts()
    if not templates:
        print("  (keine)")
        return
    for t in templates:
        size = t.stat().st_size
        preview = t.read_text(encoding="utf-8")[:80].replace("\n", " ")
        print(f"  {t.stem:30s}  {size:>5} Bytes  {preview}...")
