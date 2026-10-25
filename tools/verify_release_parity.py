"""Verify the runtime source against the submitted Lenovo release baseline."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile


SOURCE_ROOTS = ("assets", "references", "scripts")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize(data: bytes) -> bytes:
    """Only CRLF -> LF is permitted; no whitespace or content rewriting."""
    return data.replace(b"\r\n", b"\n")


def adapted_skill(data: bytes, version: str) -> bytes:
    value = normalize(data)
    parts = value.split(b"---\n", 2)
    if len(parts) != 3 or parts[0]:
        raise ValueError("SKILL.md must start with YAML front matter")
    old = f"version: {version}\n".encode()
    if parts[1].splitlines(keepends=True).count(old) != 1:
        raise ValueError("Expected exactly one top-level upstream version field")
    parts[1] = parts[1].replace(old, f'metadata:\n  version: "{version}"\n'.encode(), 1)
    return b"---\n".join(parts)


def source_files(root: Path) -> set[str]:
    paths = {"SKILL.md"} if (root / "SKILL.md").is_file() else set()
    for directory in SOURCE_ROOTS:
        parent = root / directory
        if parent.exists():
            paths.update(p.relative_to(root).as_posix() for p in parent.rglob("*") if p.is_file())
    return paths


def verify(root: Path, baseline: dict, archive: Path | None = None) -> dict:
    errors = []
    expected = {item["path"]: item for item in baseline["files"]}
    actual = source_files(root)
    for name in sorted(set(expected) - actual):
        errors.append({"kind": "missing", "path": name})
    for name in sorted(actual - set(expected)):
        errors.append({"kind": "unexpected_source", "path": name})
    for name in sorted(actual & set(expected)):
        path = root / name
        if path.is_symlink() or root.resolve() not in path.resolve().parents:
            errors.append({"kind": "source_path", "path": name})
            continue
        if digest(normalize(path.read_bytes())) != expected[name]["github_lf_sha256"]:
            errors.append({"kind": "content_drift", "path": name})
    if archive is not None:
        raw = archive.read_bytes()
        if digest(raw) != baseline["lenovo_archive"]["sha256"]:
            errors.append({"kind": "archive_sha256"})
        if len(raw) != baseline["lenovo_archive"]["bytes"]:
            errors.append({"kind": "archive_size"})
        try:
            with zipfile.ZipFile(archive) as package:
                names = [i.filename for i in package.infolist() if not i.is_dir()]
                if len(names) != len(set(names)) or set(names) != set(expected):
                    errors.append({"kind": "archive_inventory"})
                for name in sorted(set(names) & set(expected)):
                    upstream = package.read(name)
                    if digest(upstream) != expected[name]["lenovo_sha256"]:
                        errors.append({"kind": "archive_content", "path": name})
                    adapted = adapted_skill(upstream, baseline["version"]) if name == "SKILL.md" else normalize(upstream)
                    if digest(adapted) != expected[name]["github_lf_sha256"]:
                        errors.append({"kind": "adaptation_mismatch", "path": name})
        except (zipfile.BadZipFile, ValueError) as exc:
            errors.append({"kind": "archive_format", "detail": str(exc)})
    return {"ok": not errors, "version": baseline["version"], "checked_source_files": len(expected),
            "archive_checked": archive is not None, "errors": errors}


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=repo)
    parser.add_argument("--baseline", type=Path, default=repo / "docs/release-baseline.json")
    parser.add_argument("--archive", type=Path, help="Original Lenovo ZIP, copied without repacking")
    args = parser.parse_args()
    try:
        result = verify(args.root, json.loads(args.baseline.read_text(encoding="utf-8")), args.archive)
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        result = {"ok": False, "errors": [{"kind": "input_error", "detail": str(exc)}]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
