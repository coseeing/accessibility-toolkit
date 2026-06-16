from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _apps_keys_for_spec(path: Path) -> set[str]:
    module = ast.parse(path.read_text(encoding="utf-8"))
    for node in module.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "APPS":
                if not isinstance(node.value, ast.Dict):
                    raise AssertionError(f"{path} APPS is not a dict literal")
                keys: set[str] = set()
                for key in node.value.keys:
                    if not isinstance(key, ast.Constant) or not isinstance(key.value, str):
                        raise AssertionError(f"{path} APPS contains a non-string key")
                    keys.add(key.value)
                return keys
    raise AssertionError(f"{path} does not define APPS")


def test_windows_packaging_spec_includes_access8graph() -> None:
    spec_path = ROOT / "packaging" / "windows_apps.spec"

    assert "access8graph" in _apps_keys_for_spec(spec_path)


def test_macos_packaging_spec_includes_access8graph() -> None:
    spec_path = ROOT / "packaging" / "macos_apps.spec"

    assert "access8graph" in _apps_keys_for_spec(spec_path)
