#!/usr/bin/env python3
"""The "Spec + prompt" text: everything an AI assistant needs to write a Shelf-ready artifact.

Built from spec/ so it can never drift: the gallery's "Spec + prompt" button copies the
generated shelf-spec.txt, and `shelf prompt --full` prints the same text.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def prompt_block(spec_dir: Path = REPO / "spec") -> str:
    """The ````text block of spec/PROMPT.md."""
    text = (spec_dir / "PROMPT.md").read_text(encoding="utf-8")
    m = re.search(r"````text\n(.*?)\n````", text, re.S)
    if not m:
        raise ValueError("spec/PROMPT.md has no ````text block")
    return m.group(1)


def _body(path: Path) -> str:
    """A spec file without its top-level title (the bundle supplies its own headings)."""
    text = path.read_text(encoding="utf-8").strip()
    return re.sub(r"\A# .*\n+", "", text)


def bundle(spec_dir: Path = REPO / "spec") -> str:
    return "\n".join(
        [
            "# Shelf: how to make an artifact (spec + prompt)",
            "",
            "Shelf is a personal gallery for small standalone HTML creations. Read everything below,",
            "then follow the PROMPT in part 1. Parts 2 and 3 are the full rules it summarises; if they",
            "disagree with the prompt, the spec wins.",
            "",
            "## Part 1. The prompt (follow this)",
            "",
            prompt_block(spec_dir),
            "",
            "## Part 2. The specification",
            "",
            _body(spec_dir / "SPEC.md"),
            "",
            "## Part 3. The metadata reference",
            "",
            _body(spec_dir / "METADATA.md"),
            "",
        ]
    )
