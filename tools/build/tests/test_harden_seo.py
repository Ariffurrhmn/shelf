"""Tests for CSP hardening, SEO files, aliases and share cards."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
import build  # noqa: E402
import harden  # noqa: E402
import seo  # noqa: E402
import shortlinks as sl  # noqa: E402
from test_build import artifact  # noqa: E402


def directive(csp: str, name: str) -> list[str]:
    for part in csp.split(";"):
        bits = part.strip().split()
        if bits and bits[0] == name:
            return bits[1:]
    raise AssertionError(f"{name} missing from {csp}")


class TestCsp(unittest.TestCase):
    def test_default_blocks_network(self):
        csp = harden.policy({})
        self.assertEqual(directive(csp, "default-src"), ["'none'"])
        self.assertEqual(directive(csp, "connect-src"), ["'self'", "data:", "blob:"])
        self.assertEqual(directive(csp, "img-src"), ["'self'", "data:", "blob:"])
        self.assertEqual(directive(csp, "object-src"), ["'none'"])
        self.assertEqual(directive(csp, "base-uri"), ["'self'"])

    def test_declared_network_is_allowed_with_subdomains_and_websockets(self):
        csp = harden.policy({"network": ["api.example.com"]})
        for name in ("connect-src", "img-src", "form-action"):
            self.assertIn("https://api.example.com", directive(csp, name))
            self.assertIn("https://*.api.example.com", directive(csp, name))
        self.assertIn("wss://api.example.com", directive(csp, "connect-src"))
        self.assertNotIn("https://evil.example.org", csp)

    def test_pinned_cdns_keep_working_for_code_and_styles_only(self):
        csp = harden.policy({})
        self.assertIn("https://cdn.jsdelivr.net", directive(csp, "script-src"))
        self.assertIn("https://fonts.googleapis.com", directive(csp, "style-src"))
        self.assertNotIn("https://cdn.jsdelivr.net", directive(csp, "connect-src"))
        self.assertNotIn("https://cdn.jsdelivr.net", directive(csp, "img-src"))

    def test_inject_puts_policy_first_in_head(self):
        html = '<!doctype html><html lang="en"><head><meta charset="utf-8"><script>var a</script></head><body></body></html>'
        out = harden.inject_csp(html, {})
        self.assertLess(out.index("Content-Security-Policy"), out.index("<meta charset"))
        self.assertEqual(out.count("Content-Security-Policy"), 1)

    def test_inject_ignores_head_text_in_comments(self):
        html = '<!-- <head> --><!doctype html><html lang="en"><head data-x="1"><title>t</title></head><body></body></html>'
        out = harden.inject_csp(html, {})
        self.assertGreater(out.index("Content-Security-Policy"), out.index('<head data-x="1">'))

    def test_inject_handles_multiline_head(self):
        html = '<!doctype html>\n<html lang="en">\n<head\n  data-a="1">\n<title>t</title></head><body></body></html>'
        out = harden.inject_csp(html, {})
        self.assertIn('data-a="1"><meta http-equiv="Content-Security-Policy"', out)


class TestSeo(unittest.TestCase):
    def test_robots_and_sitemap(self):
        base = "https://example.github.io/shelf/"
        self.assertIn("Sitemap: https://example.github.io/shelf/sitemap.xml", seo.robots_txt(base))
        xml = seo.sitemap_xml(base, [{"url": "artifacts/a/", "created": "2026-01-02", "updated": "2026-03-04"}])
        self.assertIn("<loc>https://example.github.io/shelf/</loc>", xml)
        self.assertIn("<loc>https://example.github.io/shelf/artifacts/a/</loc><lastmod>2026-03-04</lastmod>", xml)

    def test_share_tags_escape_html(self):
        tags = seo.share_tags(title='A "quoted" <b>', description="x & y", url="https://e/x/", image="https://e/i.webp")
        self.assertIn('content="A &quot;quoted&quot; &lt;b&gt;"', tags)
        self.assertIn("x &amp; y", tags)
        self.assertIn("summary_large_image", tags)

    def test_inject_site_urls(self):
        self.assertEqual(seo.inject_site_urls('<link href="__SHELF_BASE_URL__og.png">', "https://e.io/s"), '<link href="https://e.io/s/og.png">')


class TestGalleryCsp(unittest.TestCase):
    def test_added_once_and_strict(self):
        html = "<!doctype html><html><head><title>x</title></head></html>"
        out = seo.inject_gallery_csp(html)
        self.assertEqual(out.count("Content-Security-Policy"), 1)
        self.assertIn("script-src 'self';", out)
        self.assertNotIn("unsafe-inline'; img", out.split("script-src")[1].split("style-src")[0])
        self.assertEqual(seo.inject_gallery_csp(out), out)


class TestBuildOutputs(unittest.TestCase):
    def build(self, d, extra_meta=""):
        root, out = Path(d) / "artifacts", Path(d) / "site"
        artifact(root, "new-name", extra_meta)
        rc = build.main(["--artifacts-dir", str(root), "--out", str(out), "--skip-gallery", "--no-thumbnails",
                         "--links", str(Path(d) / "none.json")])
        return rc, out

    def test_alias_redirect_is_written(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = self.build(d, ',"aliases":["old-name"]')
            self.assertEqual(rc, 0)
            code = sl.auto_code("new-name")
            page = (out / "artifacts" / "old-name" / "index.html").read_text()
            self.assertIn(f'"../../{code}/"', page)
            self.assertIn(f'"../../{code}/"', (out / "artifacts" / "new-name" / "index.html").read_text())
            self.assertIn("location.search + location.hash", page)
            data = json.loads((out / "artifacts.json").read_text())["artifacts"][0]
            self.assertEqual(data["aliases"], ["old-name"])

    def test_alias_that_is_also_a_slug_fails(self):
        with tempfile.TemporaryDirectory() as d:
            root, out = Path(d) / "artifacts", Path(d) / "site"
            artifact(root, "one", ',"aliases":["two"]')
            artifact(root, "two")
            rc = build.main(["--artifacts-dir", str(root), "--out", str(out), "--skip-gallery", "--no-thumbnails",
                             "--links", str(Path(d) / "none.json")])
            self.assertEqual(rc, 1)

    def test_artifact_page_is_the_share_card_and_seo_files_exist(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = self.build(d)
            self.assertEqual(rc, 0)
            code = sl.auto_code("new-name")
            page = (out / code / "index.html").read_text()  # served directly at its short address
            self.assertIn('property="og:title" content="T new-name"', page)
            self.assertIn('property="og:image" content="https://ariffurrhmn.github.io/shelf/og.png"', page)
            self.assertIn(f'property="og:url" content="https://ariffurrhmn.github.io/shelf/{code}/"', page)
            self.assertIn(f'<link rel="canonical" href="https://ariffurrhmn.github.io/shelf/{code}/">', page)
            self.assertLess(page.index("Content-Security-Policy"), page.index("<script"))
            self.assertIn(f"{code}/", (out / "sitemap.xml").read_text())
            self.assertIn("Sitemap:", (out / "robots.txt").read_text())

    def test_authors_own_share_tags_are_left_alone(self):
        html = '<html><head><meta property="og:title" content="Mine"></head></html>'
        self.assertEqual(seo.artifact_head_tags(html, title="T", description="d", url="https://e/x/", image="https://e/i.png"), "")

    def test_spec_bundle_is_written_and_complete(self):
        with tempfile.TemporaryDirectory() as d:
            rc, out = self.build(d)
            text = (out / "shelf-spec.txt").read_text()
            for needle in ("You are building one artifact", "## 1. Layout", "| `featured` |", "Part 1", "Part 3"):
                self.assertIn(needle, text)

    def test_thumbnail_jobs_include_override_and_declared_hosts(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "artifacts"
            artifact(root, "a", ',"thumbnail":"cover.png","network":["api.example.com"]')
            (root / "a" / "cover.png").write_bytes(b"\x89PNG")
            results = build.sv.validate_all(root)
            job = build.thumbnail_jobs(results, {"a": "abcd"})["items"][0]
            self.assertEqual((job["override"], job["path"]), ("cover.png", "abcd"))
            self.assertIn("api.example.com", job["allowHosts"])
            self.assertIn("cdn.jsdelivr.net", job["allowHosts"])


if __name__ == "__main__":
    unittest.main()
