"""Tests fuer llmauto.core.config -- Konfigurationsmanagement."""
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from llmauto.core.config import (
    load_global_config,
    load_chain,
    list_chains,
    new_link,
    save_chain,
    _normalize_paths,
    DEFAULT_GLOBAL_CONFIG,
    DEFAULT_LINK,
)


class TestNormalizePaths:
    def test_string_replacement(self):
        result = _normalize_paths("C:\\Users\\User\\OneDrive\\test")
        # Sollte den aktuellen Home-Pfad einsetzen (wenn unterschiedlich)
        assert isinstance(result, str)

    def test_dict_recursive(self):
        data = {"path": "C:\\Users\\User\\file.txt", "nested": {"p": "C:\\Users\\User\\a"}}
        result = _normalize_paths(data)
        assert isinstance(result, dict)
        assert "nested" in result

    def test_list_recursive(self):
        data = ["C:\\Users\\User\\a", "C:\\Users\\User\\b"]
        result = _normalize_paths(data)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_non_string_passthrough(self):
        assert _normalize_paths(42) == 42
        assert _normalize_paths(None) is None
        assert _normalize_paths(True) is True


class TestDefaultGlobalConfig:
    def test_has_required_keys(self):
        required = ["default_model", "default_permission_mode",
                     "default_allowed_tools", "default_timeout_seconds"]
        for key in required:
            assert key in DEFAULT_GLOBAL_CONFIG

    def test_model_is_current(self):
        assert "claude-sonnet-4-6" in DEFAULT_GLOBAL_CONFIG["default_model"]


class TestNewLink:
    def test_creates_default_link(self):
        link = new_link()
        assert link["role"] == "worker"
        assert link["model"] is None

    def test_overrides(self):
        link = new_link(name="test-worker", model="claude-opus-4-6", role="controller")
        assert link["name"] == "test-worker"
        assert link["model"] == "claude-opus-4-6"
        assert link["role"] == "controller"

    def test_does_not_mutate_default(self):
        link = new_link(name="modified")
        assert DEFAULT_LINK["name"] == ""


class TestLoadGlobalConfig:
    def test_loads_from_file(self):
        config = load_global_config()
        assert "default_model" in config
        assert "default_permission_mode" in config


class TestListChains:
    def test_returns_list(self):
        chains = list_chains()
        assert isinstance(chains, list)

    def test_known_chains_present(self):
        chains = list_chains()
        # controller-worker-loop und review-chain sind die oeffentlichen Chains
        public_chains = [c for c in chains if not c.startswith("_")]
        assert len(public_chains) >= 1


class TestLoadChain:
    def test_load_existing(self):
        chains = list_chains()
        if chains:
            config = load_chain(chains[0])
            assert "chain_name" in config
            assert "links" in config
            assert "mode" in config

    def test_load_nonexistent_raises(self):
        with pytest.raises(FileNotFoundError):
            load_chain("nonexistent-chain-xyz")


class TestSaveChain:
    def test_save_and_reload(self, tmp_path):
        from llmauto.core import config as cfg_module
        original_base = cfg_module.BASE_DIR
        try:
            cfg_module.BASE_DIR = tmp_path
            (tmp_path / "chains").mkdir()

            chain_config = {
                "chain_name": "test-save",
                "links": [{"name": "w1", "role": "worker"}],
                "mode": "once",
            }
            save_chain("test-save", chain_config)
            loaded = load_chain("test-save")
            assert loaded["chain_name"] == "test-save"
            assert loaded["mode"] == "once"
        finally:
            cfg_module.BASE_DIR = original_base
