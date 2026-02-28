"""Tests fuer llmauto.core.state -- ChainState Management."""
import tempfile
from pathlib import Path

import pytest

from llmauto.core.state import ChainState


@pytest.fixture
def state(tmp_path):
    """Erstellt einen ChainState in einem temporaeren Verzeichnis."""
    return ChainState("test-chain", tmp_path)


class TestStatus:
    def test_initial_status_unknown(self, state):
        assert state.get_status() == "UNKNOWN"

    def test_set_and_get_status(self, state):
        state.set_status("RUNNING")
        assert state.get_status() == "RUNNING"

    def test_overwrite_status(self, state):
        state.set_status("RUNNING")
        state.set_status("STOPPED")
        assert state.get_status() == "STOPPED"


class TestRounds:
    def test_initial_round_zero(self, state):
        assert state.get_round() == 0

    def test_increment_round(self, state):
        r = state.increment_round()
        assert r == 1
        assert state.get_round() == 1

    def test_multiple_increments(self, state):
        for i in range(5):
            state.increment_round()
        assert state.get_round() == 5


class TestRuntime:
    def test_no_start_returns_zero(self, state):
        assert state.get_runtime_hours() == 0.0

    def test_record_start(self, state):
        state.record_start()
        hours = state.get_runtime_hours()
        assert 0.0 <= hours < 0.01  # Weniger als 36 Sekunden


class TestHandoff:
    def test_empty_handoff(self, state):
        assert state.get_handoff() == ""

    def test_write_and_read(self, state):
        state.write_handoff("# Handoff Runde 1\nInhalt hier.")
        assert "Handoff Runde 1" in state.get_handoff()

    def test_overwrite_handoff(self, state):
        state.write_handoff("Alt")
        state.write_handoff("Neu")
        assert state.get_handoff() == "Neu"


class TestPerLinkHandoff:
    def test_link_handoff_file_path(self, state):
        f = state.get_link_handoff_file("opus-worker")
        assert f.name == "handoff_opus-worker.md"

    def test_save_link_handoff(self, state):
        state.write_handoff("Worker-Report mit viel Inhalt")
        state.save_link_handoff("opus-worker")
        link_file = state.get_link_handoff_file("opus-worker")
        assert link_file.exists()
        assert "Worker-Report" in link_file.read_text(encoding="utf-8")


class TestSkipProtection:
    """Tests fuer den Skip-Pattern-Overwrite-Bug Fix."""

    def test_skip_detected_and_restored(self, state):
        real_report = (
            "# Handoff - Runde 3 - OPUS_WORKER\n"
            "## Rolle: OPUS_WORKER\n"
            "### Ergebnis:\n"
            "SharedMemoryClient v0.3.0 mit bach_api Integration.\n"
            "55+ Tests, SQL Migration, Handler 929 Zeilen.\n"
            "### Status: COMPLETED\n"
        )
        state.write_handoff(real_report)
        handoff_before = state.get_handoff()

        # Worker schreibt nur SKIP
        state.write_handoff("SKIPPED - Nicht zugewiesen.")

        restored = state.protect_handoff_from_skip("sonnet-worker", handoff_before)
        assert restored is True
        assert "OPUS_WORKER" in state.get_handoff()
        # Per-Link Datei hat den Skip
        link_file = state.get_link_handoff_file("sonnet-worker")
        assert "SKIPPED" in link_file.read_text(encoding="utf-8")

    def test_real_handoff_not_detected_as_skip(self, state):
        old = "# Alte Runde\nViel Text hier der wichtig ist.\n" * 5
        state.write_handoff(old)
        handoff_before = state.get_handoff()

        new = "# Neue Runde\nNoch mehr wichtiger Text.\n" * 5
        state.write_handoff(new)

        restored = state.protect_handoff_from_skip("opus-worker", handoff_before)
        assert restored is False
        assert "Neue Runde" in state.get_handoff()

    def test_empty_before_not_restored(self, state):
        """Wenn vorher nichts da war, soll auch nichts restored werden."""
        handoff_before = ""
        state.write_handoff("SKIPPED")

        restored = state.protect_handoff_from_skip("worker", handoff_before)
        assert restored is False


class TestShutdown:
    def test_no_stop_initially(self, state):
        assert not state.is_stop_requested()

    def test_request_stop(self, state):
        state.request_stop("Test-Stopp")
        assert state.is_stop_requested()
        assert state.get_stop_reason() == "Test-Stopp"

    def test_check_shutdown_manual_stop(self, state):
        state.request_stop("Manuell")
        stop, reason = state.check_shutdown({})
        assert stop is True
        assert "MANUAL_STOP" in reason

    def test_check_shutdown_all_done(self, state):
        state.set_status("ALL_DONE")
        stop, reason = state.check_shutdown({})
        assert stop is True
        assert "ALL_TASKS_DONE" in reason

    def test_check_shutdown_max_rounds(self, state):
        for _ in range(5):
            state.increment_round()
        stop, reason = state.check_shutdown({"max_rounds": 5})
        assert stop is True
        assert "MAX_ROUNDS" in reason

    def test_check_shutdown_not_triggered(self, state):
        state.set_status("RUNNING")
        stop, reason = state.check_shutdown({"max_rounds": 100})
        assert stop is False


class TestReset:
    def test_reset_clears_state(self, state):
        state.set_status("RUNNING")
        state.record_start()
        state.increment_round()
        state.request_stop("Test")

        state.reset()

        assert state.get_status() == "READY"
        assert state.get_round() == 0
        assert not state.is_stop_requested()
        assert "INITIAL (Reset)" in state.get_handoff()
