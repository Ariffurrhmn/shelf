"""Tests for the build script. Run: python -m unittest discover -s tools/build/tests"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
import build  # noqa: E402
import shortlinks as sl  # noqa: E402

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
            rc = build.main(["--artifacts-dir", str(root), "--out", str(out), "--skip-gallery", "--no-thumbnails", "--links", str(Path(d) / "none.json")])
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
            rc = build.main(["--artifacts-dir", str(root), "--out", str(out), "--skip-gallery", "--no-thumbnails", "--links", str(Path(d) / "none.json")])
            self.assertEqual(rc, 1)
            self.assertFalse(out.exists())


class TestShortLinks(unittest.TestCase):
    def test_auto_code_is_stable_short_and_unambiguous(self):
        code = sl.auto_code("pomodoro-timer")
        self.assertEqual(code, sl.auto_code("pomodoro-timer"))
        self.assertEqual(len(code), 4)
        self.assertTrue(set(code) <= set(sl.ALPHABET))
        self.assertFalse(set(code) & set("il01o"))
        self.assertNotEqual(code, sl.auto_code("snake-game"))

    def test_auto_code_pinned(self):
        # Printed links must never change. If this fails, the algorithm changed.
        self.assertEqual(sl.auto_code("pomodoro-timer"), "74ng")

    def test_explicit_short_wins_and_links_json_is_included(self):
        plan = sl.plan_links([("a-slide", {"short": "talk"}), ("b-app", {})], {"repo": "https://example.com/r"})
        self.assertEqual(plan.artifacts["a-slide"], "talk")
        self.assertEqual(plan.artifacts["b-app"], sl.auto_code("b-app"))
        self.assertEqual(plan.external, {"repo": "https://example.com/r"})

    def test_collisions_fail_with_both_owners_named(self):
        with self.assertRaises(sl.ShortLinkError) as cm:
            sl.plan_links([("one", {"short": "dup"}), ("two", {"short": "dup"})], {})
        self.assertIn("'one'", str(cm.exception))
        self.assertIn("'two'", str(cm.exception))
        with self.assertRaises(sl.ShortLinkError):
            sl.plan_links([("one", {"short": "dup"})], {"dup": "https://example.com"})
        with self.assertRaises(sl.ShortLinkError) as cm:  # an artifact's automatic code clashes with a link
            sl.plan_links([("one", {})], {sl.auto_code("one"): "https://example.com"})
        self.assertIn("automatic", str(cm.exception))

    def test_links_json_validation(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "links.json"

            def load(text):
                f.write_text(text, encoding="utf-8")
                return sl.load_links(f)

            self.assertEqual(load('{"ok": "https://example.com/x?y=1#z"}'), {"ok": "https://example.com/x?y=1#z"})
            self.assertEqual(sl.load_links(Path(d) / "missing.json"), {})
            for bad in (
                "not json",
                "[]",
                '{"x": "https://example.com"}',  # code too short
                '{"assets": "https://example.com"}',  # reserved
                '{"Bad": "https://example.com"}',
                '{"ok": "javascript:alert(1)"}',
                '{"ok": "ftp://example.com/f"}',
                '{"ok": "https://exa mple.com"}',
                '{"ok": 5}',
                '{"ok": "/relative"}',
            ):
                with self.assertRaises(sl.ShortLinkError, msg=bad):
                    load(bad)

    def test_redirect_page_escapes_and_forwards(self):
        page = sl.redirect_page('https://example.com/?a="1"&b=<x>', "ex</title>", forward=False)
        self.assertNotIn("</title><", page.split("<title>")[1][:40])
        self.assertIn("&quot;1&quot;&amp;b=&lt;x&gt;", page)
        self.assertNotIn("location.search", page)
        self.assertIn("\\u003cx>", page)  # '<' never appears raw inside the script string
        self.assertIn("location.search + location.hash", sl.redirect_page("../artifacts/a/", "a", forward=True))

    def test_base_url(self):
        self.assertIsNone(sl.base_url({}))
        self.assertEqual(sl.base_url({"GITHUB_REPOSITORY": "Ariffurrhmn/shelf"}), "https://ariffurrhmn.github.io/shelf/")
        self.assertEqual(sl.base_url({"GITHUB_REPOSITORY": "me/me.github.io"}), "https://me.github.io/")
        self.assertEqual(sl.base_url({"GITHUB_REPOSITORY": "me/shelf", "SHELF_CNAME": "go.example.com"}), "https://go.example.com/")
        self.assertEqual(sl.base_url({"SHELF_BASE_URL": "https://x.example.com/s"}), "https://x.example.com/s/")


class TestShortLinkBuild(unittest.TestCase):
    def build(self, d, extra_links=None, **meta):
        root, out = Path(d) / "artifacts", Path(d) / "site"
        artifact(root, "one", meta.get("one", ""))
        artifact(root, "two", meta.get("two", ""))
        artifact(root, "draft-one", ',"draft":true,"short":"drafty"')
        links = Path(d) / "links.json"
        if extra_links is not None:
            links.write_text(json.dumps(extra_links), encoding="utf-8")
        rc = build.main(["--artifacts-dir", str(root), "--out", str(out), "--skip-gallery", "--no-thumbnails", "--links", str(links)])
        return rc, out

    def test_redirect_pages_and_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = self.build(d, {"docs": "https://example.com/docs"}, one=',"short":"first"')
            self.assertEqual(rc, 0)
            self.assertIn("../artifacts/one/", (out / "first" / "index.html").read_text())
            self.assertIn("../artifacts/two/", (out / sl.auto_code("two") / "index.html").read_text())
            self.assertIn("https://example.com/docs", (out / "docs" / "index.html").read_text())
            self.assertFalse((out / "drafty").exists())  # drafts get no short link
            shorts = {a["slug"]: a["short"] for a in json.loads((out / "artifacts.json").read_text())["artifacts"]}
            self.assertEqual(shorts, {"one": "first", "two": sl.auto_code("two")})

    def test_collision_stops_the_build_before_writing(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = self.build(d, None, one=',"short":"same"', two=',"short":"same"')
            self.assertEqual(rc, 1)
            self.assertFalse(out.exists())

    def test_clash_with_existing_output_folder_is_an_error(self):
        with tempfile.TemporaryDirectory() as d:
            plan = sl.Plan(external={"taken": "https://example.com"})
            out = Path(d)
            (out / "taken").mkdir()
            with self.assertRaises(sl.ShortLinkError):
                sl.write_redirects(out, plan)


if __name__ == "__main__":
    unittest.main()
