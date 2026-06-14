"""Tests for config.py."""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest import TestCase, main as ut_main

# Ensure the project root is on sys.path so we can import src.*
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import Config, load_config, save_config, CONFIG_FILE, DATA_DIR


class TestConfig(TestCase):

    def setUp(self):
        # Save original state
        self._orig_data_dir = DATA_DIR
        self._orig_config_file = CONFIG_FILE
        self._orig_env = os.environ.get("DEEPSEEK_API_KEY")

    def tearDown(self):
        # Restore original state
        import src.config as mod
        mod.DATA_DIR = self._orig_data_dir
        # CONFIG_FILE is derived from DATA_DIR so restore that too
        if "DEEPSEEK_API_KEY" in os.environ and self._orig_env is None:
            del os.environ["DEEPSEEK_API_KEY"]
        elif self._orig_env:
            os.environ["DEEPSEEK_API_KEY"] = self._orig_env

    def _patch_paths(self, tmp_dir: Path):
        """Redirect DATA_DIR to a temp directory."""
        import src.config as mod
        mod.DATA_DIR = tmp_dir
        # CONFIG_FILE is evaluated at module load from DATA_DIR, so we need
        # to update it too since load_config reads it.
        mod.CONFIG_FILE = tmp_dir / "config.json"

    def test_default_config(self):
        """Config returns sensible defaults when no file exists."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            self._patch_paths(tmp)
            cfg = load_config()
            self.assertEqual(cfg.api_key, "")
            self.assertEqual(cfg.refresh_interval, 60)
            self.assertEqual(cfg.language, "zh")
            self.assertTrue(cfg.minimize_to_tray)
            self.assertTrue(cfg.show_taskbar_widget)
            self.assertEqual(cfg.taskbar_widget_position, "right")
            self.assertIsNone(cfg.win_x)
            self.assertIsNone(cfg.win_y)

    def test_load_saved_config(self):
        """Config loads values from a JSON file."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            self._patch_paths(tmp)
            data = {
                "api_key": "sk-test-key",
                "refresh_interval": 120,
                "language": "en",
                "minimize_to_tray": False,
                "show_taskbar_widget": False,
                "taskbar_widget_position": "left",
                "win_x": 100,
                "win_y": 200,
            }
            (tmp / "config.json").write_text(json.dumps(data), encoding="utf-8")
            cfg = load_config()
            self.assertEqual(cfg.api_key, "sk-test-key")
            self.assertEqual(cfg.refresh_interval, 120)
            self.assertEqual(cfg.language, "en")
            self.assertFalse(cfg.minimize_to_tray)
            self.assertEqual(cfg.taskbar_widget_position, "left")
            self.assertEqual(cfg.win_x, 100)
            self.assertEqual(cfg.win_y, 200)

    def test_load_corrupt_config_falls_back_to_defaults(self):
        """Corrupt JSON should fall back to defaults (not crash)."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            self._patch_paths(tmp)
            (tmp / "config.json").write_text("not valid json {{{", encoding="utf-8")
            cfg = load_config()
            self.assertEqual(cfg.refresh_interval, 60)  # default

    def test_env_var_overrides_empty_key(self):
        """DEEPSEEK_API_KEY env var provides key when config has none."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            self._patch_paths(tmp)
            os.environ["DEEPSEEK_API_KEY"] = "sk-env-key"
            cfg = load_config()
            self.assertEqual(cfg.api_key, "sk-env-key")

    def test_env_var_does_not_override_existing_key(self):
        """Env var should not override a key already in config."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            self._patch_paths(tmp)
            (tmp / "config.json").write_text(
                json.dumps({"api_key": "sk-file-key"}), encoding="utf-8")
            os.environ["DEEPSEEK_API_KEY"] = "sk-env-key"
            cfg = load_config()
            self.assertEqual(cfg.api_key, "sk-file-key")

    def test_save_and_reload_roundtrip(self):
        """Saving a config and reloading it should preserve values."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            self._patch_paths(tmp)
            cfg = Config(api_key="sk-roundtrip", refresh_interval=300,
                         language="en", win_x=42, win_y=99)
            save_config(cfg)
            loaded = load_config()
            self.assertEqual(loaded.api_key, "sk-roundtrip")
            self.assertEqual(loaded.refresh_interval, 300)
            self.assertEqual(loaded.win_x, 42)
            self.assertEqual(loaded.win_y, 99)

    def test_extra_keys_in_config_are_ignored(self):
        """Unknown keys in the config JSON should be ignored."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            self._patch_paths(tmp)
            (tmp / "config.json").write_text(
                json.dumps({"api_key": "sk-ok", "bogus_field": "should_be_ignored"}),
                encoding="utf-8")
            cfg = load_config()
            self.assertEqual(cfg.api_key, "sk-ok")
            with self.assertRaises(AttributeError):
                _ = cfg.bogus_field


if __name__ == "__main__":
    ut_main()
