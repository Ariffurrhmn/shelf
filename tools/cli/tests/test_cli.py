"""Tests for the shelf CLI. Run: python -m unittest discover -s tools/cli/tests"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
import shelf_cli as cli  # noqa: E402

REPO = HERE.parents[3]
SAMPLE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Focus Timer</title><meta name="description" content="A tiny timer."></head>
<body><h1>Focus</h1></body></html>
"""


def run(artifacts, *argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(["--artifacts-dir", str(artifacts), *argv])
    return code, out.getvalue(), err.getvalue()


class Helpers(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(cli.slugify("Focus Timer!"), "focus-timer")
        self.assertEqual(cli.slugify("  Ünïcode — Café  "), "unicode-cafe")
        self.assertEqual(cli.slugify("../../etc/passwd"), "etc-passwd")
        self.assertEqual(cli.slugify("***"), "")
        self.assertLessEqual(len(cli.slugify("x" * 200)), 48)

    def test_unique_slug(self):
        self.assertEqual(cli.unique_slug("a", set()), "a")
        self.assertEqual(cli.unique_slug("a", {"a"}), "a-2")
        self.assertEqual(cli.unique_slug("a", {"a", "a-2"}), "a-3")

    def test_normalize_tool_and_lists(self):
        self.assertEqual(cli.normalize_tool("claude"), "Claude")
        self.assertEqual(cli.normalize_tool("Some Tool"), "Some Tool")
        self.assertEqual(cli.split_list(" a, b ,,c"), ["a", "b", "c"])
        self.assertEqual(cli.split_list(None), [])

    def test_safe_child_blocks_traversal(self):
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d) / "artifacts"
            parent.mkdir()
            for bad in ("../x", "..", "a/../../x", "/etc/passwd", "."):
                with self.assertRaises(cli.ShelfError, msg=bad):
                    cli.safe_child(parent, bad)
            self.assertEqual(cli.safe_child(parent, "ok"), (parent / "ok").resolve())

    def test_page_info(self):
        info = cli.page_info(SAMPLE)
        self.assertEqual((info["title"], info["description"], info["meta"]), ("Focus Timer", "A tiny timer.", {}))

    def test_upsert_inserts_and_replaces(self):
        once = cli.upsert_meta_block(SAMPLE, {"title": "A"})
        self.assertEqual(cli.page_info(once)["meta"], {"title": "A"})
        twice = cli.upsert_meta_block(once, {"title": "B"})
        self.assertEqual(cli.page_info(twice)["meta"], {"title": "B"})
        self.assertEqual(twice.count('id="shelf-meta"'), 1)

    def test_upsert_cannot_break_out_of_script(self):
        out = cli.upsert_meta_block(SAMPLE, {"title": "</script><script>alert(1)</script>"})
        self.assertEqual(out.count("<script"), 1)
        self.assertEqual(cli.page_info(out)["meta"]["title"], "</script><script>alert(1)</script>")

    def test_upsert_needs_a_head(self):
        with self.assertRaises(cli.ShelfError):
            cli.upsert_meta_block("<p>no head</p>", {"title": "A"})

    def test_fix_basics(self):
        fixed = cli.fix_basics("<html><head></head><body></body></html>")
        self.assertIn('<html lang="en"', fixed)
        self.assertIn('name="viewport"', fixed)
        self.assertEqual(cli.fix_basics(fixed), fixed)  # idempotent

    def test_detect_behaviour(self):
        d = cli.detect_behaviour("localStorage.x; fetch('/a')")
        self.assertEqual((d["storage"], d["network"]), (["localStorage"], ["fetch()"]))


class AddCommand(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.artifacts = self.root / "artifacts"
        self.artifacts.mkdir()
        self.src = self.root / "my-app.html"
        self.src.write_text(SAMPLE, encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def add(self, *extra, src=None):
        return run(self.artifacts, "add", str(src or self.src), "--yes", *extra)

    def leftovers(self):
        return [p.name for p in self.artifacts.iterdir() if p.name.startswith(".")]

    def test_creates_valid_artifact_from_defaults_and_flags(self):
        code, out, err = self.add("--tool", "claude", "--tags", "productivity,timer", "--kind", "app")
        self.assertEqual(code, 0, err)
        meta = cli.page_info((self.artifacts / "focus-timer" / "index.html").read_text())["meta"]
        self.assertEqual(meta["title"], "Focus Timer")
        self.assertEqual(meta["description"], "A tiny timer.")
        self.assertEqual(meta["tool"], "Claude")
        self.assertEqual(meta["tags"], ["productivity", "timer"])
        self.assertRegex(meta["created"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertIn("link:", out)
        self.assertIn("git push", out)
        self.assertEqual(self.leftovers(), [])

    def test_category_is_an_alias_for_kind(self):
        self.assertEqual(self.add("--tool", "x", "--category", "game")[0], 0)
        meta = cli.page_info((self.artifacts / "focus-timer" / "index.html").read_text())["meta"]
        self.assertEqual(meta["kind"], "game")

    def test_dry_run_writes_nothing(self):
        code, out, _ = self.add("--tool", "claude", "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("Dry run", out)
        self.assertEqual(list(self.artifacts.iterdir()), [])

    def test_missing_required_metadata_is_a_clear_error(self):
        self.src.write_text(SAMPLE.replace('<meta name="description" content="A tiny timer.">', ""), encoding="utf-8")
        code, _, err = self.add()
        self.assertEqual(code, 1)
        self.assertIn("--description", err)
        self.assertIn("--tool", err)
        self.assertEqual(list(self.artifacts.iterdir()), [])

    def test_validation_failure_leaves_nothing_behind(self):
        self.src.write_text(SAMPLE.replace("<body>", '<body><script>var k = "ghp_' + "a" * 36 + '";</script>'), encoding="utf-8")
        code, out, err = self.add("--tool", "claude")
        self.assertEqual(code, 1)
        self.assertIn("SECRET", out)
        self.assertEqual(list(self.artifacts.iterdir()), [])

    def test_storage_error_gets_an_actionable_hint(self):
        self.src.write_text(SAMPLE.replace("<body>", "<body><script>localStorage.a=1</script>"), encoding="utf-8")
        code, _, err = self.add("--tool", "claude")
        self.assertEqual(code, 1)
        self.assertIn("--storage local", err)
        self.assertEqual(self.add("--tool", "claude", "--storage", "local")[0], 0)

    def test_fix_flag_repairs_missing_lang_and_viewport(self):
        self.src.write_text("<!doctype html><html><head><title>X</title></head><body>hi</body></html>", encoding="utf-8")
        self.assertEqual(self.add("--tool", "claude", "--description", "d")[0], 1)
        self.assertEqual(self.add("--tool", "claude", "--description", "d", "--fix")[0], 0)

    def test_explicit_slug_conflict_is_refused(self):
        self.assertEqual(self.add("--tool", "x", "--slug", "mine")[0], 0)
        before = (self.artifacts / "mine" / "index.html").read_text()
        code, _, err = self.add("--tool", "y", "--slug", "mine", "--title", "Other")
        self.assertEqual(code, 1)
        self.assertIn("already taken", err)
        self.assertEqual((self.artifacts / "mine" / "index.html").read_text(), before)

    def test_derived_slug_conflict_fails_noninteractive_unless_auto_suffix(self):
        self.assertEqual(self.add("--tool", "x")[0], 0)
        self.assertEqual(self.add("--tool", "x")[0], 1)
        self.assertEqual(self.add("--tool", "x", "--auto-suffix")[0], 0)
        self.assertTrue((self.artifacts / "focus-timer-2").is_dir())

    def test_force_replaces_but_keeps_created_short_and_makes_backup(self):
        self.assertEqual(self.add("--tool", "x", "--created", "2026-01-05", "--short", "timer")[0], 0)
        self.src.write_text(SAMPLE.replace("<h1>Focus</h1>", "<h1>Second version</h1>"), encoding="utf-8")
        code, out, err = self.add("--tool", "x", "--force")
        self.assertEqual(code, 0, err)
        text = (self.artifacts / "focus-timer" / "index.html").read_text()
        self.assertIn("Second version", text)
        meta = cli.page_info(text)["meta"]
        self.assertEqual((meta["created"], meta["short"]), ("2026-01-05", "timer"))
        backups = list((self.root / ".shelf-cache" / "backups").iterdir())
        self.assertEqual(len(backups), 1)
        self.assertNotIn("Second version", (backups[0] / "index.html").read_text())

    def test_path_traversal_slug_is_rejected(self):
        for bad in ("../evil", "a/b", "/abs"):
            code, _, err = self.add("--tool", "x", "--slug", bad)
            self.assertEqual(code, 1, bad)
        self.assertEqual([p.name for p in self.root.iterdir() if p.name not in ("artifacts", "my-app.html")], [])

    def test_rejects_bad_sources(self):
        txt = self.root / "notes.txt"
        txt.write_text("hello")
        self.assertEqual(self.add("--tool", "x", src=txt)[0], 1)
        self.assertEqual(self.add("--tool", "x", src=self.root / "missing.html")[0], 1)
        empty = self.root / "empty"
        empty.mkdir()
        self.assertEqual(self.add("--tool", "x", src=empty)[0], 1)
        notes = self.root / "fake.html"
        notes.write_text("just some words")
        self.assertEqual(self.add("--tool", "x", src=notes)[0], 1)
        binary = self.root / "bin.html"
        binary.write_bytes(b"\xff\xfe\x00bad")
        self.assertEqual(self.add("--tool", "x", src=binary)[0], 1)

    def test_folder_source_copies_assets_and_skips_dotfiles(self):
        folder = self.root / "bundle"
        folder.mkdir()
        (folder / "index.html").write_text(SAMPLE, encoding="utf-8")
        (folder / "style.css").write_text("body{}")
        (folder / ".secret").write_text("x")
        self.assertEqual(self.add("--tool", "x", src=folder)[0], 0)
        made = self.artifacts / "focus-timer"
        self.assertTrue((made / "style.css").is_file())
        self.assertFalse((made / ".secret").exists())

    def test_folder_symlink_escaping_the_folder_is_refused(self):
        folder = self.root / "bundle"
        folder.mkdir()
        (folder / "index.html").write_text(SAMPLE, encoding="utf-8")
        outside = self.root / "outside.txt"
        outside.write_text("private")
        (folder / "link.txt").symlink_to(outside)
        code, _, err = self.add("--tool", "x", src=folder)
        self.assertEqual(code, 1)
        self.assertIn("symbolic link", err)
        self.assertEqual(list(self.artifacts.iterdir()), [])

    def test_thumbnail_override_is_copied_and_declared(self):
        img = self.root / "shot.png"
        img.write_bytes(b"\x89PNG\r\n")
        self.assertEqual(self.add("--tool", "x", "--thumbnail", str(img))[0], 0)
        made = self.artifacts / "focus-timer"
        self.assertTrue((made / "thumbnail.png").is_file())
        self.assertEqual(cli.page_info((made / "index.html").read_text())["meta"]["thumbnail"], "thumbnail.png")

    def test_icon_flag_copies_the_png_and_makes_the_artifact_installable(self):
        sys.path.insert(0, str(REPO / "tools" / "build"))
        import pwa

        img = self.root / "art.png"
        img.write_bytes(pwa.encode_png(512, 3, [bytearray(512 * 3) for _ in range(512)]))
        self.assertEqual(self.add("--tool", "x", "--icon", str(img))[0], 0)
        made = self.artifacts / "focus-timer"
        self.assertTrue((made / "icon.png").is_file())
        meta = cli.page_info((made / "index.html").read_text())["meta"]
        self.assertEqual((meta["icon"], meta["install"]), ("icon.png", True))
        small = self.root / "small.png"
        small.write_bytes(pwa.encode_png(64, 3, [bytearray(64 * 3) for _ in range(64)]))
        code, out, _ = self.add("--tool", "x", "--icon", str(small), "--slug", "second")
        self.assertEqual(code, 1)
        self.assertIn("at least 512", out)
        self.assertFalse((self.artifacts / "second").exists())

    def test_existing_metadata_block_in_the_file_is_respected(self):
        self.src.write_text(cli.upsert_meta_block(SAMPLE, {
            "title": "From the AI", "description": "d", "created": "2026-02-02", "tool": "ChatGPT", "kind": "game", "tags": ["x"],
        }), encoding="utf-8")
        self.assertEqual(self.add()[0], 0)
        meta = cli.page_info((self.artifacts / "from-the-ai" / "index.html").read_text())["meta"]
        self.assertEqual((meta["tool"], meta["kind"], meta["created"]), ("ChatGPT", "game", "2026-02-02"))


class RenameAndLinks(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.artifacts = Path(self._tmp.name) / "artifacts"
        self.artifacts.mkdir()
        src = Path(self._tmp.name) / "a.html"
        src.write_text(SAMPLE, encoding="utf-8")
        for slug in ("old-name", "other"):
            run(self.artifacts, "add", str(src), "--yes", "--tool", "x", "--slug", slug)

    def tearDown(self):
        self._tmp.cleanup()

    def test_rename_keeps_old_address_and_short_link(self):
        from shortlinks import auto_code

        code, out, err = run(self.artifacts, "rename", "old-name", "new-name")
        self.assertEqual(code, 0, err)
        self.assertFalse((self.artifacts / "old-name").exists())
        meta = cli.page_info((self.artifacts / "new-name" / "index.html").read_text())["meta"]
        self.assertEqual(meta["aliases"], ["old-name"])
        self.assertEqual(meta["short"], auto_code("old-name"))

    def test_rename_refuses_taken_names_and_old_addresses(self):
        self.assertEqual(run(self.artifacts, "rename", "old-name", "other")[0], 1)
        run(self.artifacts, "rename", "old-name", "new-name")
        self.assertEqual(run(self.artifacts, "rename", "other", "old-name")[0], 1)  # alias of new-name
        self.assertEqual(run(self.artifacts, "rename", "missing", "x")[0], 1)
        self.assertEqual(run(self.artifacts, "rename", "other", "../escape")[0], 1)

    def test_rename_dry_run(self):
        self.assertEqual(run(self.artifacts, "rename", "old-name", "new-name", "--dry-run")[0], 0)
        self.assertTrue((self.artifacts / "old-name").is_dir())

    def test_links_that_would_break(self):
        import shelf_validate as sv
        from shortlinks import auto_code

        before = {"gone": {}, "kept": {}, "renamed": {}, "pinned": {"short": "mine"}}
        class R:  # minimal stand-in for sv.Result
            def __init__(self, slug, meta, draft=False):
                self.slug, self.metadata, self.draft = slug, meta, draft

        now = [R("kept", {}), R("renamed-new", {"aliases": ["renamed"], "short": auto_code("renamed")}), R("pinned", {"short": "mine"})]
        problems = cli.links_that_would_break(before, now, {})
        self.assertEqual(len([p for p in problems if "artifacts/gone/" in p]), 1)
        self.assertEqual(len([p for p in problems if "/" + auto_code("gone") in p]), 1)
        self.assertFalse([p for p in problems if "renamed" in p or "kept" in p or "pinned" in p])
        # a draft does not count as live
        self.assertTrue(cli.links_that_would_break({"kept": {}}, [R("kept", {}, draft=True)], {}))

    def test_removing_on_purpose_is_allowed_only_when_retired(self):
        from shortlinks import auto_code

        class R:
            def __init__(self, slug, meta):
                self.slug, self.metadata, self.draft = slug, meta, False

        before = {"gone": {}, "kept": {}}
        now = [R("kept", {})]
        self.assertEqual(len(cli.links_that_would_break(before, now, {})), 2)  # address and short code
        self.assertEqual(cli.links_that_would_break(before, now, {}, ({"gone"}, {auto_code("gone")})), [])
        self.assertEqual(cli.links_that_would_break(before, now, {}, ({"gone"}, set())), [])  # retiring a slug retires its code too
        self.assertEqual(len(cli.links_that_would_break(before, now, {}, (set(), {auto_code("gone")}))), 1)  # a code alone does not hide the address

    def test_retired_file_is_read_and_validated(self):
        import tempfile as tf

        with tf.TemporaryDirectory() as d:
            f = Path(d) / "retired.json"
            self.assertEqual(cli.load_retired(f), (set(), set()))
            f.write_text('{"artifacts": ["a"], "codes": ["abcd"]}')
            self.assertEqual(cli.load_retired(f), ({"a"}, {"abcd"}))
            f.write_text("[1, 2]")
            with self.assertRaises(cli.ShelfError):
                cli.load_retired(f)
        self.assertEqual(cli.load_retired()[0], {"url-shortener"})  # this repo's own file

    def test_prompt_full_includes_spec_and_metadata(self):
        code, out, _ = run(self.artifacts, "prompt", "--full")
        self.assertEqual(code, 0)
        for needle in ("You are building one artifact", "## 1. Layout", "| `aliases` |"):
            self.assertIn(needle, out)

    def test_list_json_and_validate(self):
        code, out, _ = run(self.artifacts, "list", "--json")
        self.assertEqual(code, 0)
        self.assertEqual(sorted(r["slug"] for r in json.loads(out)), ["old-name", "other"])
        self.assertEqual(run(self.artifacts, "validate")[0], 0)
        self.assertEqual(run(self.artifacts, "validate", "other")[0], 0)
        self.assertEqual(run(self.artifacts, "validate", "nope")[0], 1)


REPLY = """Here's your timer! I wrote it as one file.

```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Focus Timer</title>
<script type="application/json" id="shelf-meta">
{"title":"Focus Timer","description":"A 25-minute focus timer.","created":"2026-11-04","tool":"Claude","kind":"app"}
</script>
</head>
<body><h1>Focus</h1></body>
</html>
```

Checklist: I closed </html> properly and used no storage. All rules pass.
"""


class ClipboardInput(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.artifacts = self.root / "artifacts"
        self.artifacts.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def run_with_clipboard(self, text, *extra):
        from unittest import mock

        with mock.patch.object(cli, "read_clipboard", return_value=text):
            return run(self.artifacts, "add", "--clipboard", "--yes", *extra)

    def test_extract_keeps_only_the_document(self):
        html = cli.extract_html(REPLY)
        self.assertTrue(html.startswith("<!doctype html>"))
        self.assertTrue(html.rstrip().endswith("</html>"))
        self.assertNotIn("Checklist", html)
        self.assertNotIn("```", html)

    def test_extract_ignores_a_commentary_line_that_mentions_the_closing_tag(self):
        self.assertNotIn("Checklist", cli.extract_html(REPLY))  # "</html>" appears in the commentary, mid-line
        bare = "<html><body>x</body></html>"
        self.assertEqual(cli.extract_html(bare), bare + "\n")  # no own-line terminator: falls back to the last tag

    def test_extract_errors_are_actionable(self):
        with self.assertRaises(cli.ShelfError) as no_html:
            cli.extract_html("just some chat, no code")
        self.assertIn("Copy the whole code block", str(no_html.exception))
        with self.assertRaises(cli.ShelfError) as cut:
            cli.extract_html("<!doctype html><html><body>half a page")
        self.assertIn("cut off", str(cut.exception))

    def test_clipboard_add_uses_the_embedded_metadata_without_asking(self):
        code, out, err = self.run_with_clipboard(REPLY)
        self.assertEqual(code, 0, err)
        text = (self.artifacts / "focus-timer" / "index.html").read_text()
        self.assertNotIn("Checklist", text)
        self.assertEqual(cli.page_info(text)["meta"]["tool"], "Claude")

    def test_clipboard_add_validates_before_writing(self):
        leaky = REPLY.replace("<h1>Focus</h1>", '<script>var k = "ghp_' + "a" * 36 + '";</script>')
        code, out, _ = self.run_with_clipboard(leaky)
        self.assertEqual(code, 1)
        self.assertIn("SECRET", out)
        self.assertEqual(list(self.artifacts.iterdir()), [])

    def test_stdin_dash_works_like_the_clipboard(self):
        import io
        from unittest import mock

        with mock.patch.object(sys, "stdin", io.StringIO(REPLY)):
            code, _, err = run(self.artifacts, "add", "-", "--yes")
        self.assertEqual(code, 0, err)
        self.assertTrue((self.artifacts / "focus-timer").is_dir())

    def test_needs_a_source_and_rejects_both(self):
        self.assertEqual(run(self.artifacts, "add", "--yes")[0], 1)
        f = self.root / "a.html"
        f.write_text(REPLY)
        from unittest import mock

        with mock.patch.object(cli, "read_clipboard", return_value=REPLY):
            self.assertEqual(run(self.artifacts, "add", str(f), "--clipboard", "--yes")[0], 1)

    def test_interactive_clipboard_add_asks_before_writing(self):
        import io
        from unittest import mock

        tty = mock.Mock(wraps=io.StringIO(""))
        tty.isatty = lambda: True
        for answer, expect_added in (("n", False), ("y", True)):
            shutil_dir = self.artifacts / "focus-timer"
            if shutil_dir.exists():
                import shutil

                shutil.rmtree(shutil_dir)
            with mock.patch.object(cli, "read_clipboard", return_value=REPLY), mock.patch.object(sys, "stdin", tty), mock.patch("builtins.input", return_value=answer):
                code, out, _ = run(self.artifacts, "add", "--clipboard")
            self.assertIn("About to add", out)
            self.assertEqual((self.artifacts / "focus-timer").is_dir(), expect_added, answer)
            self.assertEqual(code, 0 if expect_added else 1)

    def test_read_clipboard_picks_the_platform_tool_and_explains_when_missing(self):
        from unittest import mock

        with mock.patch.object(sys, "platform", "linux"), mock.patch.dict("os.environ", {}, clear=False), mock.patch("shutil.which", side_effect=lambda c: "/bin/" + c if c == "xclip" else None), mock.patch("subprocess.run") as run_mock:
            run_mock.return_value = mock.Mock(returncode=0, stdout="<html></html>".encode())
            self.assertEqual(cli.read_clipboard(), "<html></html>")
            self.assertEqual(run_mock.call_args[0][0][0], "xclip")
        with mock.patch.object(sys, "platform", "darwin"), mock.patch("shutil.which", return_value=None):
            with self.assertRaises(cli.ShelfError) as ctx:
                cli.read_clipboard()
            self.assertIn("pbpaste | python shelf add -", str(ctx.exception))


class CommitAndPush(unittest.TestCase):
    def setUp(self):
        import subprocess

        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.remote = base / "remote.git"
        self.repo = base / "repo"
        self.git = lambda *a, cwd=None: subprocess.run(["git", *a], cwd=cwd or self.repo, check=True, capture_output=True, text=True).stdout
        subprocess.run(["git", "init", "-q", "--bare", str(self.remote)], check=True)
        subprocess.run(["git", "init", "-q", "-b", "work", str(self.repo)], check=True)
        for k, v in (("user.name", "t"), ("user.email", "t@example.com")):
            self.git("config", k, v)
        self.git("remote", "add", "origin", str(self.remote))
        (self.repo / "artifacts").mkdir()
        (self.repo / "README.md").write_text("x")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "init")
        self.src = base / "a.html"
        self.src.write_text(SAMPLE)

    def tearDown(self):
        self._tmp.cleanup()

    def add(self, *extra):
        return run(self.repo / "artifacts", "add", str(self.src), "--yes", "--tool", "x", *extra)

    def test_commit_only_touches_the_artifact_and_does_not_push(self):
        (self.repo / "unrelated.txt").write_text("staged by someone else")
        self.git("add", "unrelated.txt")
        code, out, err = self.add("--commit")
        self.assertEqual(code, 0, err)
        self.assertEqual(self.git("log", "-1", "--format=%s").strip(), "Add Focus Timer")
        self.assertEqual(self.git("show", "--name-only", "--format=", "HEAD").split(), ["artifacts/focus-timer/index.html"])
        self.assertIn("unrelated.txt", self.git("status", "--short"))  # still staged, not swept in
        self.assertEqual(self.git("branch", "-r").strip(), "")  # nothing was pushed

    def test_push_is_explicit_and_sets_the_upstream(self):
        code, out, err = self.add("--push")
        self.assertEqual(code, 0, err)
        self.assertIn("pushed:", out)
        self.assertIn("Add Focus Timer", self.git("log", "--format=%s", "work", cwd=self.remote))

    def test_without_flags_nothing_is_committed(self):
        self.assertEqual(self.add()[0], 0)
        self.assertEqual(self.git("log", "--format=%s").strip(), "init")


class Inbox(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.artifacts = self.root / "artifacts"
        self.inbox = self.root / "inbox"
        self.artifacts.mkdir()
        self.inbox.mkdir()
        (self.inbox / "README.md").write_text("how to use the inbox")

    def tearDown(self):
        self._tmp.cleanup()

    def with_meta(self, html=SAMPLE, **over):
        meta = {"title": "Focus Timer", "description": "A tiny timer.", "created": "2026-01-05", "tool": "Claude", "kind": "app", **over}
        return cli.upsert_meta_block(html, meta)

    def ingest(self, *extra):
        return run(self.artifacts, "ingest", *extra)

    def test_adds_files_and_empties_the_inbox_but_keeps_the_readme(self):
        (self.inbox / "whatever.html").write_text(self.with_meta())
        code, out, err = self.ingest()
        self.assertEqual(code, 0, out + err)
        self.assertTrue((self.artifacts / "focus-timer" / "index.html").is_file())
        self.assertEqual(sorted(p.name for p in self.inbox.iterdir()), ["README.md"])
        self.assertIn("| `whatever.html` | added |", out)
        self.assertIn("https://ariffurrhmn.github.io/shelf/", out)

    def test_a_file_named_after_an_artifact_updates_it_and_keeps_its_identity(self):
        (self.inbox / "first.html").write_text(self.with_meta(short="timer"))
        self.ingest()
        (self.inbox / "focus-timer.html").write_text(self.with_meta(SAMPLE.replace("<h1>Focus</h1>", "<h1>Second</h1>"), created="2026-02-02"))
        code, out, _ = self.ingest()
        self.assertEqual(code, 0, out)
        text = (self.artifacts / "focus-timer" / "index.html").read_text()
        self.assertIn("Second", text)
        meta = cli.page_info(text)["meta"]
        self.assertEqual((meta["created"], meta["short"]), ("2026-01-05", "timer"))
        self.assertRegex(meta["updated"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertIn("updated", out)

    def test_a_duplicate_title_is_refused_not_silently_suffixed(self):
        (self.inbox / "one.html").write_text(self.with_meta())
        self.ingest()
        (self.inbox / "two.html").write_text(self.with_meta())
        code, out, _ = self.ingest()
        self.assertEqual(code, 1)
        self.assertIn("already taken", out)
        self.assertTrue((self.inbox / "two.html").exists())  # stays in the inbox for you to fix
        self.assertFalse((self.artifacts / "focus-timer-2").exists())

    def test_failures_stay_and_do_not_block_the_good_files(self):
        (self.inbox / "good.html").write_text(self.with_meta())
        (self.inbox / "leaky.html").write_text(self.with_meta(SAMPLE.replace("<h1>Focus</h1>", '<script>var k = "ghp_' + "a" * 36 + '";</script>'), title="Leaky"))
        (self.inbox / "notes.txt").write_text("not html")
        code, out, _ = self.ingest()
        self.assertEqual(code, 1)
        self.assertTrue((self.artifacts / "focus-timer").is_dir())
        self.assertFalse((self.artifacts / "leaky").exists())
        self.assertTrue((self.inbox / "leaky.html").exists() and (self.inbox / "notes.txt").exists())
        self.assertIn("SECRET", out)
        self.assertIn("only .html files", out)

    def test_missing_required_metadata_is_reported_not_guessed(self):
        (self.inbox / "bare.html").write_text(SAMPLE.replace('<meta name="description" content="A tiny timer.">', ""))
        code, out, _ = self.ingest()
        self.assertEqual(code, 1)
        self.assertIn("--description", out)
        self.assertEqual([p.name for p in self.artifacts.iterdir()], [])

    def test_dry_run_changes_nothing(self):
        (self.inbox / "x.html").write_text(self.with_meta())
        code, out, _ = self.ingest("--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("would add", out)
        self.assertTrue((self.inbox / "x.html").exists())
        self.assertEqual([p.name for p in self.artifacts.iterdir()], [])

    def test_report_cannot_inject_markdown_or_mentions(self):
        report = cli.ingest_report([
            {"file": "@octocat `x`.html", "status": "added", "link": "https://e/x", "output": ""},
            {"file": "bad.html", "status": "failed", "output": "```\n@everyone [click](http://evil)\n```"},
        ])
        self.assertIn("`@octocat 'x'.html`", report)  # inside a code span, so it notifies nobody
        self.assertEqual(report.count("```"), 2)  # one fence opened, one closed: the uploaded text cannot break out of it
        self.assertEqual(report.count("```text"), 1)

    def test_report_file_and_empty_inbox(self):
        out_file = self.root / "report.md"
        code, out, _ = self.ingest("--report", str(out_file))
        self.assertEqual(code, 0)
        self.assertIn("nothing to add", out_file.read_text())


class Misc(unittest.TestCase):
    def test_prompt_matches_the_spec_fields(self):
        text = cli.prompt_text()
        import shelf_validate as sv

        for field in sv.KNOWN_FIELDS:
            self.assertIn(field, text, f"spec/PROMPT.md does not mention metadata field {field!r}")
        for word in ("storage", "network", "secrets", "responsive"):
            self.assertIn(word.lower(), text.lower())

    def test_doctor_runs_on_this_repo(self):
        code, out, _ = run(REPO / "artifacts", "doctor")
        self.assertIn("Artifacts validate", out)
        self.assertIn("Short links", out)

    def test_preview_handler_respects_prefix(self):
        h = cli._Handler.__new__(cli._Handler)
        h.directory = "/srv"
        h.prefix = "/shelf"
        self.assertTrue(h.translate_path("/shelf/artifacts/x/").rstrip("/").endswith("artifacts/x"))
        self.assertIn("__outside_prefix__", h.translate_path("/other/"))


if __name__ == "__main__":
    unittest.main()
