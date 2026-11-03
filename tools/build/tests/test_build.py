"""Tests for the build script. Run: python -m unittest discover -s tools/build/tests"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
import build  # noqa: E402

REPO = HERE.parents[3]


def artifact(root: Path, slug: str, meta_extra: str = "", lang: str = ' lang="en"') -> None:
    d = root / slug
    d.mkdir(parents=True)
    (d / "index.html").write_text(
        f'<!doctype html><html{lang}><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1"><title>T</title>'
        '<script type="application/json" id="shelf-meta">'
        '{"title":"T %s","description":"d","created":"2026-01-02","tool":"x","kind":"app"%s}'
        "</script></head><body>hi</body></html>" % (slug, meta_extra),
        encoding="utf-8",
    )


class TestBuild(unittest.TestCase):
    def test_manifest_excludes_drafts_and_sorts_newest_first(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "artifacts"
            artifact(root, "aaa")
            artifact(root, "bbb", ',"draft":true')
            artifact(root, "ccc", ',"tags":["x"]')
            (root / "ccc" / "index.html").write_text(
                (root / "ccc" / "index.html").read_text().replace("2026-01-02", "2026-05-05"), encoding="utf-8"
            )
            results = build.sv.validate_all(root)
            m = build.build_manifest([r for r in results if not r.draft], {"aaa"}, "https://example.com/r")
            self.assertEqual([e["slug"] for e in m["artifacts"]], ["ccc", "aaa"])
            self.assertEqual(m["artifacts"][1]["thumbnail"], "thumbnails/aaa.jpg")
            self.assertIsNone(m["artifacts"][0]["thumbnail"])
            self.assertEqual(m["repo"], "https://example.com/r")

    def test_entry_defaults(self):
        e = build.make_entry("s", {"title": "t", "description": "d", "created": "2026-01-01", "tool": "x", "kind": "doc"}, False)
        self.assertEqual((e["storage"], e["network"], e["tags"], e["url"]), ("none", [], [], "artifacts/s/"))

    def test_data_only_build_writes_site(self):
        with tempfile.TemporaryDirectory() as d:
            root, out = Path(d) / "artifacts", Path(d) / "site"
            artifact(root, "one")
            artifact(root, "draft-one", ',"draft":true')
            rc = build.main(["--artifacts-dir", str(root), "--out", str(out), "--skip-gallery", "--no-thumbnails"])
            self.assertEqual(rc, 0)
            data = json.loads((out / "artifacts.json").read_text())
            self.assertEqual([a["slug"] for a in data["artifacts"]], ["one"])
            self.assertTrue((out / "artifacts" / "one" / "index.html").is_file())
            self.assertFalse((out / "artifacts" / "draft-one").exists())
            self.assertTrue((out / ".nojekyll").exists())

    def test_invalid_artifact_stops_build(self):
        with tempfile.TemporaryDirectory() as d:
            root, out = Path(d) / "artifacts", Path(d) / "site"
            artifact(root, "bad", lang="")
            rc = build.main(["--artifacts-dir", str(root), "--out", str(out), "--skip-gallery", "--no-thumbnails"])
            self.assertEqual(rc, 1)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
