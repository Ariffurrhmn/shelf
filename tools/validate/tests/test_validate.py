"""Tests for the Shelf validator. Run: python -m unittest discover -s tools/validate/tests"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import shelf_validate as v  # noqa: E402

REPO = Path(__file__).resolve().parents[3]

META = {"title": "T", "description": "One line.", "created": "2026-01-02", "tool": "Claude", "kind": "app"}


def page(meta=None, head="", body="<p>hi</p>", lang='lang="en"', viewport=True, title="<title>T</title>", extra_meta=True):
    m = dict(META)
    m.update(meta or {})
    block = f'<script type="application/json" id="shelf-meta">{json.dumps(m)}</script>' if extra_meta else ""
    vp = '<meta name="viewport" content="width=device-width, initial-scale=1">'
    return f"<!doctype html><html {lang}><head><meta charset=utf-8>{vp if viewport else ''}{title}{block}{head}</head><body>{body}</body></html>"


class Base(unittest.TestCase):
    def check(self, html, slug="demo", extra=None):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / slug
            root.mkdir()
            (root / "index.html").write_text(html, encoding="utf-8")
            for name, content in (extra or {}).items():
                (root / name).write_text(content, encoding="utf-8")
            return v.validate_artifact(root)

    def codes(self, res, severity=None):
        return {i.code for i in res.issues if severity is None or i.severity == severity}


class TestValid(Base):
    def test_minimal_passes(self):
        res = self.check(page())
        self.assertTrue(res.ok, res.issues)

    def test_repo_artifacts_pass(self):
        for r in v.validate_all(REPO / "artifacts"):
            self.assertTrue(r.ok, (r.slug, [i.message for i in r.errors]))


class TestLayoutAndHtml(Base):
    def test_bad_slug(self):
        self.assertIn("LAYOUT-SLUG", self.codes(self.check(page(), slug="Bad_Slug")))

    def test_missing_entry(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "x").mkdir()
            self.assertIn("LAYOUT-ENTRY", self.codes(v.validate_artifact(Path(d) / "x")))

    def test_missing_lang_viewport_title(self):
        res = self.check(page(lang="", viewport=False, title=""))
        self.assertTrue({"HTML-LANG", "HTML-VIEWPORT", "HTML-TITLE"} <= self.codes(res))

    def test_empty_title(self):
        self.assertIn("HTML-TITLE", self.codes(self.check(page(title="<title>  </title>"))))

    def test_local_asset_missing_and_outside(self):
        res = self.check(page(body='<img src="nope.png"><img src="../other/x.png"><img src="/abs.png">'))
        self.assertTrue({"LAYOUT-MISSING", "LAYOUT-OUTSIDE"} <= self.codes(res))

    def test_local_asset_ok(self):
        res = self.check(page(body='<img src="a.svg">'), extra={"a.svg": "<svg xmlns='http://www.w3.org/2000/svg'/>"})
        self.assertTrue(res.ok, res.issues)


class TestMetadata(Base):
    def test_missing_block(self):
        self.assertIn("META-MISSING", self.codes(self.check(page(extra_meta=False))))

    def test_bad_json(self):
        html = page(extra_meta=False, head='<script type="application/json" id="shelf-meta">{oops}</script>')
        self.assertIn("META-JSON", self.codes(self.check(html)))

    def test_missing_required(self):
        html = page(extra_meta=False, head='<script type="application/json" id="shelf-meta">{"title":"x"}</script>')
        res = self.check(html)
        self.assertEqual(sum(1 for i in res.issues if i.code == "META-REQUIRED"), 4)

    def test_bad_values(self):
        res = self.check(page({"kind": "widget", "created": "2026-13-40", "storage": "cloud", "tags": "a", "draft": "yes"}))
        self.assertTrue({"META-KIND", "META-DATE", "META-STORAGE", "META-TYPE"} <= self.codes(res))

    def test_description_multiline(self):
        self.assertIn("META-DESCRIPTION", self.codes(self.check(page({"description": "a\nb"}))))

    def test_network_must_be_bare_domain(self):
        self.assertIn("META-NETWORK", self.codes(self.check(page({"network": ["https://api.example.com/x"]}))))

    def test_unknown_field_is_warning(self):
        res = self.check(page({"mood": "happy"}))
        self.assertTrue(res.ok)
        self.assertIn("META-UNKNOWN", self.codes(res, v.WARNING))

    def test_wrong_script_type(self):
        html = page(extra_meta=False, head='<script type="text/javascript" id="shelf-meta">{}</script>')
        self.assertIn("META-TYPE", self.codes(self.check(html)))


class TestInstall(Base):
    def test_install_ok(self):
        res = self.check(page({"install": True, "color": "#d64933"}))
        self.assertTrue(res.ok, [i.message for i in res.issues])
        self.assertFalse(res.warnings)

    def test_install_and_color_types(self):
        self.assertIn("META-TYPE", self.codes(self.check(page({"install": "yes"}))))
        for bad in ("red", "#fff", "#gggggg", 5):
            self.assertIn("META-COLOR", self.codes(self.check(page({"color": bad}))), bad)

    def test_reserved_files_collide(self):
        res = self.check(page({"install": True}), extra={"manifest.webmanifest": "{}", "icon-192.png": "x"})
        self.assertEqual(sum(1 for i in res.issues if i.code == "PWA-RESERVED"), 2)
        # Not installable: the names are free to use.
        self.assertNotIn("PWA-RESERVED", self.codes(self.check(page(), extra={"manifest.webmanifest": "{}"})))

    def test_live_network_warns_but_cdn_does_not(self):
        res = self.check(page({"install": True, "network": ["api.example.com"]}, head='<link rel="preconnect" href="https://api.example.com">'))
        self.assertIn("PWA-OFFLINE", self.codes(res, v.WARNING))
        res = self.check(page({"install": True, "network": ["cdn.jsdelivr.net"]}))
        self.assertNotIn("PWA-OFFLINE", self.codes(res))

    def test_service_worker_in_source_still_forbidden(self):
        res = self.check(page({"install": True}, body="<script>navigator.serviceWorker.register('x.js')</script>"), )
        self.assertIn("STORAGE", self.codes(res))


class TestDependencies(Base):
    def test_pinned_cdn_ok(self):
        res = self.check(page({"network": ["cdn.jsdelivr.net", "cdnjs.cloudflare.com", "unpkg.com", "code.jquery.com"]}, head=(
            '<script src="https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"></script>'
            '<script src="https://cdnjs.cloudflare.com/ajax/libs/vue/3.4.21/vue.global.min.js"></script>'
            '<script src="https://unpkg.com/react@18.2.0/umd/react.production.min.js"></script>'
            '<script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>')))
        self.assertTrue(res.ok, [i.message for i in res.issues])

    def test_unpinned_forms_fail(self):
        for url in (
            "https://cdn.jsdelivr.net/npm/marked/marked.min.js",
            "https://cdn.jsdelivr.net/npm/marked@latest/marked.min.js",
            "https://cdn.jsdelivr.net/npm/marked@^12.0.0/marked.min.js",
            "https://cdn.jsdelivr.net/npm/marked@12/marked.min.js",
            "https://unpkg.com/react@18.2/umd/react.js",
            "https://unpkg.com/react/umd/react.js",
        ):
            res = self.check(page(head=f'<script src="{url}"></script>'))
            self.assertIn("DEP-VERSION", self.codes(res), url)

    def test_unapproved_host(self):
        res = self.check(page(head='<script src="https://evil.example.net/x.js"></script>'))
        self.assertIn("DEP-HOST", self.codes(res))

    def test_unlisted_cdn_is_warning(self):
        res = self.check(page(head='<script src="https://unpkg.com/react@18.2.0/x.js"></script>'))
        self.assertTrue(res.ok)
        self.assertIn("NET-UNLISTED", self.codes(res, v.WARNING))

    def test_remote_image_needs_network(self):
        html = page(body='<img src="https://img.example.com/a.png">')
        self.assertIn("NET-REMOTE-ASSET", self.codes(self.check(html)))
        ok = page({"network": ["img.example.com"]}, body='<img src="https://img.example.com/a.png">')
        self.assertTrue(self.check(ok).ok)

    def test_css_remote_url(self):
        html = page(head="<style>body{background:url(https://img.example.com/b.png)}</style>")
        self.assertIn("NET-REMOTE-ASSET", self.codes(self.check(html)))

    def test_data_uri_fine(self):
        self.assertTrue(self.check(page(body='<img src="data:image/gif;base64,R0lGODlhAQABAAAAACw=">')).ok)


class TestStorageAndNetwork(Base):
    def test_storage_blocked_by_default(self):
        for snippet in ("localStorage.setItem('a',1)", "sessionStorage.x", "indexedDB.open('d')",
                        "document.cookie='a=1'", "navigator.serviceWorker.register('s.js')"):
            res = self.check(page(body=f"<script>{snippet}</script>"))
            self.assertIn("STORAGE", self.codes(res), snippet)

    def test_storage_local_allowed(self):
        res = self.check(page({"storage": "local"}, body="<script>localStorage.setItem('a',1)</script>"))
        self.assertTrue(res.ok, res.issues)

    def test_network_blocked_by_default(self):
        for snippet in ("fetch('/x')", "new XMLHttpRequest()", "new WebSocket('wss://a')", "navigator.sendBeacon('/b')"):
            res = self.check(page(body=f"<script>{snippet}</script>"))
            self.assertIn("NETWORK", self.codes(res), snippet)

    def test_network_allowed_when_listed(self):
        res = self.check(page({"network": ["api.example.com"]}, body="<script>fetch('https://api.example.com/x')</script>"))
        self.assertTrue(res.ok, res.issues)

    def test_checks_local_js_files(self):
        res = self.check(page(body='<script src="app.js"></script>'), extra={"app.js": "localStorage.x=1"})
        self.assertIn("STORAGE", self.codes(res))

    def test_form_post_external(self):
        res = self.check(page(body='<form action="https://collect.example.net/p"></form>'))
        self.assertIn("NET-FORM", self.codes(res))


class TestSecrets(Base):
    def test_detects_secrets(self):
        samples = {
            "aws": "AKIA" + "IOSFODNN7EXAMPLE",
            "gh": "ghp_" + "a" * 36,
            "anthropic": "sk-ant-" + "api03-" + "x" * 30,
            "openai": "sk-" + "A" * 40,
            "slack": "xoxb-" + "1234567890-abcdef",
            "pem": "-----BEGIN RSA PRIVATE KEY-----",
            "assign": 'const apiKey = "abcd1234efgh5678"',
        }
        for name, s in samples.items():
            res = self.check(page(body=f"<script>// {s}\n</script>"))
            self.assertIn("SECRET", self.codes(res), name)

    def test_secret_in_other_file(self):
        res = self.check(page(), extra={"data.json": json.dumps({"token_x": "ghp_" + "b" * 36})})
        hit = [i for i in res.issues if i.code == "SECRET"]
        self.assertTrue(hit)
        self.assertEqual(hit[0].file, "data.json")

    def test_email_flagged_but_example_ok(self):
        self.assertIn("PII", self.codes(self.check(page(body="<p>mail jane.doe@gmail.com</p>"))))
        self.assertTrue(self.check(page(body="<p>mail jane@example.com</p>")).ok)

    def test_phone_is_warning(self):
        res = self.check(page(body="<p>call 555 123 4567</p>"))
        self.assertTrue(res.ok)
        self.assertIn("PII-PHONE", self.codes(res, v.WARNING))

    def test_versions_not_mistaken_for_email(self):
        self.assertTrue(self.check(page(head='<script src="https://unpkg.com/react@18.2.0/x.js"></script>')).ok)


class TestPresentation(Base):
    GOOD = (
        "<style>@media print{.s{break-after:page}}</style>"
        "<script>document.addEventListener('keydown',function(e){"
        "if(e.key==='ArrowRight'||e.key===' ')n();if(e.key==='ArrowLeft')p();"
        "if(e.key==='f'||e.key==='F')document.documentElement.requestFullscreen();});</script>"
    )

    def test_good_presentation(self):
        res = self.check(page({"kind": "presentation"}, body=self.GOOD))
        self.assertTrue(res.ok, [i.message for i in res.issues])

    def test_bare_presentation_fails_all_rules(self):
        res = self.check(page({"kind": "presentation"}))
        self.assertTrue({"PRES-KEYS", "PRES-SPACE", "PRES-FULLSCREEN", "PRES-PRINT"} <= self.codes(res))

    def test_rules_do_not_apply_to_apps(self):
        self.assertTrue(self.check(page()).ok)


class TestDrafts(Base):
    def test_draft_downgrades_but_keeps_secrets(self):
        html = page({"draft": True}, lang="", body="<p>ghp_" + "c" * 36 + "</p>")
        res = self.check(html)
        self.assertTrue(res.draft)
        self.assertIn("SECRET", self.codes(res, v.ERROR))
        self.assertIn("HTML-LANG", self.codes(res, v.WARNING))

    def test_draft_without_problems_passes(self):
        self.assertTrue(self.check(page({"draft": True})).ok)


class TestCli(Base):
    def test_exit_codes_and_json(self):
        import contextlib
        import io

        with tempfile.TemporaryDirectory() as d:
            good = Path(d) / "good"
            bad = Path(d) / "bad"
            good.mkdir()
            bad.mkdir()
            (good / "index.html").write_text(page(), encoding="utf-8")
            (bad / "index.html").write_text(page(lang=""), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(v.main([str(good)]), 0)
                self.assertEqual(v.main([str(bad)]), 1)
                self.assertEqual(v.main(["--artifacts-dir", d]), 1)


if __name__ == "__main__":
    unittest.main()
