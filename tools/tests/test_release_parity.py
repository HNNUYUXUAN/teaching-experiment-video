import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location("parity", Path(__file__).resolve().parents[1] / "verify_release_parity.py")
parity = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parity)


class ParityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        self.root.mkdir()
        self.original = {"SKILL.md": b'---\nname: example\nversion: 1.1.0\n---\nBody\n',
                         "scripts/main.py": b'print("hello")\r\n',
                         "assets/config.txt": b'KEY=\n', "references/start.md": b'# Start\n'}
        self.baseline = {"version": "1.1.0", "files": []}
        for name, raw in self.original.items():
            value = parity.adapted_skill(raw, "1.1.0") if name == "SKILL.md" else parity.normalize(raw)
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(value)
            self.baseline["files"].append({"path": name, "lenovo_sha256": parity.digest(raw), "github_lf_sha256": parity.digest(value)})
        self.archive = Path(self.temp.name) / "original.zip"
        with zipfile.ZipFile(self.archive, "w") as package:
            for name, raw in self.original.items():
                package.writestr(name, raw)
        raw = self.archive.read_bytes()
        self.baseline["lenovo_archive"] = {"sha256": parity.digest(raw), "bytes": len(raw)}

    def kinds(self):
        return {e["kind"] for e in parity.verify(self.root, self.baseline)["errors"]}

    def test_valid_sources_and_exact_archive(self):
        self.assertTrue(parity.verify(self.root, self.baseline, self.archive)["ok"])
        path = self.root / "scripts/main.py"
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        self.assertTrue(parity.verify(self.root, self.baseline)["ok"])

    def test_changed_runtime_is_rejected(self):
        (self.root / "scripts/main.py").write_text('print("changed")\n', encoding="utf-8")
        self.assertIn("content_drift", self.kinds())

    def test_missing_source_is_rejected(self):
        (self.root / "references/start.md").unlink()
        self.assertIn("missing", self.kinds())

    def test_extra_runtime_source_is_rejected(self):
        (self.root / "scripts/additional.py").write_text("pass\n", encoding="utf-8")
        self.assertIn("unexpected_source", self.kinds())

    def test_repacked_archive_is_rejected(self):
        with zipfile.ZipFile(self.archive, "a") as package:
            package.writestr("extra.txt", "extra")
        kinds = {e["kind"] for e in parity.verify(self.root, self.baseline, self.archive)["errors"]}
        self.assertIn("archive_sha256", kinds)
        self.assertIn("archive_inventory", kinds)

    def test_unrelated_skill_edit_is_rejected(self):
        path = self.root / "SKILL.md"
        path.write_bytes(path.read_bytes().replace(b"Body", b"Different body"))
        self.assertIn("content_drift", self.kinds())


if __name__ == "__main__":
    unittest.main()
