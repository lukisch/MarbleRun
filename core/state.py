"""
llmauto.core.state -- State-Management
========================================
Verwaltet Laufzeit-State pro aktiver Kette: Runden, Handoff, Shutdown.
"""
import json
from pathlib import Path
from datetime import datetime


class ChainState:
    """State-Manager fuer eine laufende Kette."""

    def __init__(self, chain_name, base_dir=None):
        self.chain_name = chain_name
        if base_dir is None:
            base_dir = Path(__file__).parent.parent
        self.state_dir = base_dir / "state" / chain_name
        self.state_dir.mkdir(parents=True, exist_ok=True)

    @property
    def status_file(self):
        return self.state_dir / "status.txt"

    @property
    def round_file(self):
        return self.state_dir / "round_counter.txt"

    @property
    def start_time_file(self):
        return self.state_dir / "start_time.txt"

    @property
    def handoff_file(self):
        return self.state_dir / "handoff.md"

    @property
    def stop_file(self):
        return self.state_dir / "STOP"

    # --- Status ---

    def get_status(self):
        if self.status_file.exists():
            return self.status_file.read_text(encoding="utf-8").strip()
        return "UNKNOWN"

    def set_status(self, status):
        self.status_file.write_text(status, encoding="utf-8")

    # --- Runden ---

    def get_round(self):
        if self.round_file.exists():
            return int(self.round_file.read_text(encoding="utf-8").strip())
        return 0

    def increment_round(self):
        current = self.get_round() + 1
        self.round_file.write_text(str(current), encoding="utf-8")
        return current

    # --- Laufzeit ---

    def record_start(self):
        self.start_time_file.write_text(datetime.now().isoformat(), encoding="utf-8")

    def get_runtime_hours(self):
        if not self.start_time_file.exists():
            return 0.0
        start = datetime.fromisoformat(self.start_time_file.read_text(encoding="utf-8").strip())
        return (datetime.now() - start).total_seconds() / 3600

    # --- Handoff ---

    def get_handoff(self):
        if self.handoff_file.exists():
            return self.handoff_file.read_text(encoding="utf-8")
        return ""

    def write_handoff(self, content):
        self.handoff_file.write_text(content, encoding="utf-8")

    def get_link_handoff_file(self, link_name):
        """Gibt den Pfad zur per-Link Handoff-Datei zurueck."""
        return self.state_dir / f"handoff_{link_name}.md"

    def save_link_handoff(self, link_name):
        """Speichert den aktuellen Handoff-Inhalt als per-Link Kopie.

        Schuetzt gegen den Skip-Pattern-Overwrite-Bug: Wenn ein Worker
        nur 'SKIPPED' schreibt, wird stattdessen nur die per-Link Datei
        aktualisiert und der Haupt-Handoff bleibt erhalten.
        """
        current = self.get_handoff()
        link_file = self.get_link_handoff_file(link_name)
        link_file.write_text(current, encoding="utf-8")
        return current

    def protect_handoff_from_skip(self, link_name, handoff_before):
        """Stellt den Handoff wieder her wenn ein Worker ihn mit SKIP ueberschrieben hat.

        Erkennt ob der aktuelle Handoff nur eine Skip-Nachricht ist
        (kurz + enthaelt SKIP/SKIPPED). Falls ja: Handoff auf den
        Zustand VOR dem Link zuruecksetzen, Skip nur in per-Link Datei speichern.

        Returns: True wenn Handoff wiederhergestellt wurde, False sonst.
        """
        current = self.get_handoff()
        # Skip-Erkennung: Handoff ist deutlich kuerzer und enthaelt Skip-Marker
        is_skip = (
            len(current.strip()) < 500
            and "SKIP" in current.upper()
            and len(current) < len(handoff_before) * 0.5
        )
        if is_skip and handoff_before.strip():
            # Per-Link Datei bekommt den Skip-Inhalt
            link_file = self.get_link_handoff_file(link_name)
            link_file.write_text(current, encoding="utf-8")
            # Haupt-Handoff wiederherstellen
            self.write_handoff(handoff_before)
            return True
        # Kein Skip: Per-Link Datei bekommt den echten Inhalt
        self.save_link_handoff(link_name)
        return False

    # --- Shutdown ---

    def request_stop(self, reason="Manuell gestoppt"):
        self.stop_file.write_text(reason, encoding="utf-8")

    def is_stop_requested(self):
        return self.stop_file.exists()

    def get_stop_reason(self):
        if self.stop_file.exists():
            return self.stop_file.read_text(encoding="utf-8").strip()
        return None

    # --- Shutdown-Checks ---

    def check_shutdown(self, config):
        """Prueft alle Shutdown-Bedingungen. Gibt (stop, grund) zurueck."""
        if self.is_stop_requested():
            return True, f"MANUAL_STOP: {self.get_stop_reason()}"

        if self.get_status() == "ALL_DONE":
            return True, "ALL_TASKS_DONE"

        deadline = config.get("deadline", "")
        if deadline and datetime.now().date() > datetime.fromisoformat(deadline).date():
            return True, f"DEADLINE_REACHED: {deadline}"

        runtime_hours = config.get("runtime_hours", 0)
        if runtime_hours > 0 and self.get_runtime_hours() >= runtime_hours:
            return True, f"RUNTIME_EXCEEDED: {self.get_runtime_hours():.1f}h / {runtime_hours}h"

        max_rounds = config.get("max_rounds", 0)
        if max_rounds > 0 and self.get_round() >= max_rounds:
            return True, f"MAX_ROUNDS: {self.get_round()}/{max_rounds}"

        max_blocks = config.get("max_consecutive_blocks", 5)
        handoff = self.get_handoff()
        if handoff:
            block_count = 0
            for line in reversed(handoff.strip().split("\n")):
                if "BLOCKED" in line.upper():
                    block_count += 1
                elif line.strip():
                    break
            if block_count >= max_blocks:
                return True, f"MAX_BLOCKS: {block_count}"

        return False, ""

    # --- Reset ---

    def reset(self):
        self.set_status("READY")
        self.round_file.write_text("0", encoding="utf-8")
        for f in [self.start_time_file, self.stop_file]:
            if f.exists():
                f.unlink()
        self.write_handoff(
            f"# Handoff - Runde 0\n"
            f"## Datum: {datetime.now().strftime('%Y-%m-%d')}\n"
            f"## Rolle: INITIAL (Reset)\n"
            f"## Task: Keiner\n"
            f"## Status: READY\n"
        )
