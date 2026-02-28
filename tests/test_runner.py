"""Tests fuer llmauto.core.runner -- ClaudeRunner."""
import pytest

from llmauto.core.runner import ClaudeRunner


class TestClaudeRunnerInit:
    def test_default_model(self):
        runner = ClaudeRunner()
        assert "claude-sonnet-4-6" in runner.model

    def test_custom_model(self):
        runner = ClaudeRunner(model="claude-opus-4-6")
        assert runner.model == "claude-opus-4-6"

    def test_default_tools(self):
        runner = ClaudeRunner()
        assert "Read" in runner.allowed_tools
        assert "Bash" in runner.allowed_tools

    def test_custom_tools(self):
        tools = ["Read", "Write"]
        runner = ClaudeRunner(allowed_tools=tools)
        assert runner.allowed_tools == tools

    def test_timeout(self):
        runner = ClaudeRunner(timeout=3600)
        assert runner.timeout == 3600


class TestBuildCmd:
    def test_basic_command(self):
        runner = ClaudeRunner(model="claude-sonnet-4-6")
        cmd = runner._build_cmd("Hallo Welt")
        assert "claude" in cmd
        assert "--model" in cmd
        assert "claude-sonnet-4-6" in cmd
        assert "-p" in cmd
        assert "Hallo Welt" in cmd

    def test_continue_flag(self):
        runner = ClaudeRunner()
        cmd = runner._build_cmd("Test", continue_conversation=True)
        assert "--continue" in cmd

    def test_no_continue_by_default(self):
        runner = ClaudeRunner()
        cmd = runner._build_cmd("Test")
        assert "--continue" not in cmd

    def test_fallback_model(self):
        runner = ClaudeRunner(fallback_model="claude-sonnet-4-6")
        cmd = runner._build_cmd("Test")
        assert "--fallback-model" in cmd

    def test_permission_mode(self):
        runner = ClaudeRunner(permission_mode="dontAsk")
        cmd = runner._build_cmd("Test")
        assert "--permission-mode" in cmd
        assert "dontAsk" in cmd


class TestBuildEnv:
    def test_removes_claudecode(self):
        import os
        os.environ["CLAUDECODE"] = "test"
        try:
            runner = ClaudeRunner()
            env = runner._build_env()
            assert "CLAUDECODE" not in env
        finally:
            os.environ.pop("CLAUDECODE", None)

    def test_sets_encoding(self):
        runner = ClaudeRunner()
        env = runner._build_env()
        assert env.get("PYTHONIOENCODING") == "utf-8"
