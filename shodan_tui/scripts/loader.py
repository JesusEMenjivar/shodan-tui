"""
Dynamic script loader.
Discovers ShodanScript subclasses from:
  1. shodan_tui/scripts/builtin/   (built-in scripts, always available)
  2. ~/.config/shodan-tui/scripts/ (user scripts, added/removed at runtime)
  3. ./user_scripts/               (project-local scripts)
"""

from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path

from shodan_tui.scripts.base import ShodanScript


class ScriptLoader:
    def __init__(self, user_scripts_dir: Path) -> None:
        self._user_scripts_dir = user_scripts_dir
        self._builtin_dir = Path(__file__).parent / "builtin"
        self._local_dir = Path.cwd() / "user_scripts"

    def load_all(self) -> list[type[ShodanScript]]:
        """Return all discovered script classes (builtin + user)."""
        scripts: list[type[ShodanScript]] = []
        seen_names: set[str] = set()

        for directory, label in [
            (self._builtin_dir, "builtin"),
            (self._user_scripts_dir, "user"),
            (self._local_dir, "local"),
        ]:
            for cls in self._load_from_dir(directory, label):
                if cls.name not in seen_names:
                    scripts.append(cls)
                    seen_names.add(cls.name)

        return scripts

    def load_builtins(self) -> list[type[ShodanScript]]:
        return self._load_from_dir(self._builtin_dir, "builtin")

    def load_user_scripts(self) -> list[type[ShodanScript]]:
        results = []
        results.extend(self._load_from_dir(self._user_scripts_dir, "user"))
        results.extend(self._load_from_dir(self._local_dir, "local"))
        return results

    def _load_from_dir(self, directory: Path, label: str) -> list[type[ShodanScript]]:
        scripts: list[type[ShodanScript]] = []
        if not directory.exists():
            return scripts

        for py_file in sorted(directory.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            try:
                classes = self._load_file(py_file, label)
                scripts.extend(classes)
            except Exception as e:
                # Don't crash the app if a script has a syntax error
                print(f"[ScriptLoader] Failed to load {py_file.name}: {e}")

        return scripts

    def _load_file(self, path: Path, label: str) -> list[type[ShodanScript]]:
        module_name = f"shodan_tui_scripts_{label}_{path.stem}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            return []
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)  # type: ignore[attr-defined]

        classes = []
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, ShodanScript)
                and obj is not ShodanScript
                and obj.__module__ == module_name
            ):
                classes.append(obj)
        return classes

    def install_script(self, source_path: Path) -> bool:
        """Copy a script file into the user scripts directory."""
        if not source_path.exists() or source_path.suffix != ".py":
            return False
        dest = self._user_scripts_dir / source_path.name
        self._user_scripts_dir.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(source_path.read_bytes())
        return True

    def remove_script(self, script_name: str) -> bool:
        """Remove a user/local script file by its filename stem."""
        for directory in (self._user_scripts_dir, self._local_dir):
            for path in directory.glob("*.py"):
                if path.stem == script_name:
                    path.unlink()
                    return True
        return False

    def list_user_script_files(self) -> list[Path]:
        return sorted(self._user_scripts_dir.glob("*.py"))
