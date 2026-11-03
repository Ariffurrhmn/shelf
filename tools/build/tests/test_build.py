"""Tests for the build script. Run: python -m unittest discover -s tools/build/tests"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
import build  # noqa: E402
import pwa  # noqa: E402

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


class TestPwa(unittest.TestCase):
    def built(self, d: str, meta_extra: str = ',"install":true'):
        root, out = Path(d) / "artifacts", Path(d) / "site"
        artifact(root, "app-one", meta_extra)
        rc = build.main(["--artifacts-dir", str(root), "--out", str(out), "--skip-gallery", "--no-thumbnails"])
        return rc, root, out

    def test_installable_artifact_gets_pwa_files_and_source_is_untouched(self):
        with tempfile.TemporaryDirectory() as d:
            before = None
            root = Path(d) / "artifacts"
            artifact(root, "app-one", ',"install":true,"color":"#336699"')
            before = (root / "app-one" / "index.html").read_text()
            out = Path(d) / "site"
            self.assertEqual(build.main(["--artifacts-dir", str(root), "--out", str(out), "--skip-gallery", "--no-thumbnails"]), 0)
            self.assertEqual((root / "app-one" / "index.html").read_text(), before)
            dest = out / "artifacts" / "app-one"
            for name in ("manifest.webmanifest", "sw.js", "icon-192.png", "icon-512.png"):
                self.assertTrue((dest / name).is_file(), name)
            html = (dest / "index.html").read_text()
            self.assertIn('rel="manifest"', html)
            self.assertLess(html.index('rel="manifest"'), html.index("</head>"))
            self.assertIn("#336699", html)
            man = json.loads((dest / "manifest.webmanifest").read_text())
            self.assertEqual((man["scope"], man["start_url"], man["theme_color"]), ("./", "./", "#336699"))
            self.assertNotIn("id", man)
            self.assertTrue((dest / "icon-512.png").read_bytes().startswith(b"\x89PNG"))
            sw = (dest / "sw.js").read_text()
            self.assertIn('"index.html"', sw)
            self.assertIn('"manifest.webmanifest"', sw)
            self.assertNotIn('"sw.js"', sw)
            data = json.loads((out / "artifacts.json").read_text())["artifacts"][0]
            self.assertEqual((data["install"], data["icon"], data["color"]), (True, "artifacts/app-one/icon-192.png", "#336699"))

    def test_non_installable_artifact_is_served_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            rc, root, out = self.built(d, "")
            self.assertEqual(rc, 0)
            dest = out / "artifacts" / "app-one"
            self.assertEqual((dest / "index.html").read_text(), (root / "app-one" / "index.html").read_text())
            self.assertEqual(sorted(p.name for p in dest.iterdir()), ["index.html"])
            data = json.loads((out / "artifacts.json").read_text())["artifacts"][0]
            self.assertEqual((data["install"], data["icon"], data["color"]), (False, None, None))

    def test_version_changes_with_content(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d)
            (f / "index.html").write_text("a")
            v1 = pwa.version_of(f)
            (f / "index.html").write_text("b")
            self.assertNotEqual(v1, pwa.version_of(f))
            (f / "sw.js").write_text("ignored")
            (f / "index.html").write_text("a")
            self.assertEqual(v1, pwa.version_of(f))

    def test_head_end_ignores_look_alikes_in_scripts_and_comments(self):
        html = '<html><head><script>var s="</head>";</script><!-- </head> --><title>x</title></head><body></body></html>'
        at = pwa.head_end_offset(html)
        self.assertEqual(html[at:at + 7], "</head>")
        self.assertEqual(at, html.rindex("</head>"))
        multi = "<html>\n<head>\n<title>x</title>\n</head>\n<body></body></html>"
        self.assertEqual(multi[pwa.head_end_offset(multi):][:7], "</head>")

    def test_inject_refuses_existing_manifest_and_double_injection(self):
        base = "<html><head>%s<title>x</title></head><body></body></html>"
        with self.assertRaises(pwa.PwaError):
            pwa.inject(base % '<link rel="manifest" href="m.json">', "#112233")
        once = pwa.inject(base % "", "#112233")
        with self.assertRaises(pwa.PwaError):
            pwa.inject(once, "#112233")
        self.assertEqual(once.count("<script>"), 1)

    def test_existing_theme_color_is_kept(self):
        out = pwa.inject('<html><head><meta name="theme-color" content="#000000"></head></html>', "#112233")
        self.assertEqual(out.count("theme-color"), 1)

    def test_icons_are_deterministic_valid_png(self):
        a = pwa.icon_png(192, "slug", "#336699")
        self.assertEqual(a, pwa.icon_png(192, "slug", "#336699"))
        self.assertNotEqual(a, pwa.icon_png(192, "other", "#336699"))
        self.assertTrue(a.startswith(b"\x89PNG\r\n\x1a\n") and a.endswith(b"IEND\xaeB`\x82"))
        self.assertRegex(pwa.default_color("x"), r"^#[0-9a-f]{6}$")


if __name__ == "__main__":
    unittest.main()
