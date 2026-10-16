#!/usr/bin/env python3
"""Validate a Claude skill folder before it is shared or uploaded.

Usage:
    python3 validate_skill.py path/to/skill-folder [--check-text PATTERN ...]

Checks, each reported as ok / FAIL / warn:
  - SKILL.md exists, with YAML frontmatter between two '---' lines
  - name: present, at most 64 characters, lowercase letters, digits and hyphens only,
    no reserved words, and equal to the folder name
  - description: present, non-empty, at most 1024 characters, no XML tags (a lone '<' or
    '>' in prose is allowed; the documented rule is 'cannot contain XML tags')
  - body under 500 lines (warn above 400)
  - every relative markdown link in SKILL.md resolves to a file inside the folder (a link
    into a sibling skill of the same plugin is a warning, since it breaks on solo upload)
  - reference files over 100 lines start with a table of contents (warn)
  - no leftover template placeholders such as {{NAME}} or TODO markers (files under a
    templates/ folder are exempt, since holding placeholders is their job)
  - no obvious secrets (private key headers, common API key prefixes)
  - any extra --check-text patterns (for example a company name) do not appear

Exit code: 0 when nothing failed, 1 when anything failed. Warnings never fail the run.
Needs only the Python standard library, so it runs anywhere Claude can run Python.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

NAME_MAX = 64            # limit from the Agent Skills documentation
DESCRIPTION_MAX = 1024   # limit from the Agent Skills documentation
BODY_LINES_MAX = 500     # authoring guidance: keep SKILL.md under 500 lines
BODY_LINES_WARN = 400    # leave headroom before the hard guidance
TOC_THRESHOLD = 100      # reference files longer than this should open with contents
RESERVED_WORDS = ("anthropic", "claude")
NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
PLACEHOLDER = re.compile(r"\{\{[A-Za-z0-9_]+\}\}|\bTODO\b|\bTBD\b")
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),          # common API key prefix
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),              # AWS access key id
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),    # GitHub tokens
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),    # Slack tokens
]
# An XML-like tag: '<' immediately followed by a tag name (optionally '/'), optional
# attributes, then '>'. Matches <example>, </b>, <br/> and <tag attr="x">, but not a lone
# '<' or '>' in prose such as "under 5 MB (< 5)", "3 > 2" or an arrow "->".
XML_TAG = re.compile(r"</?[A-Za-z_][\w:.-]*(?:\s+[^<>]*?)?\s*/?>")
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
TEXT_SUFFIXES = {".md", ".txt", ".py", ".sh", ".js", ".ts", ".json", ".yaml", ".yml", ".toml", ".html", ".css"}


class Report:
    def __init__(self) -> None:
        self.failures = 0

    def ok(self, msg: str) -> None:
        print(f"ok    {msg}")

    def fail(self, msg: str) -> None:
        self.failures += 1
        print(f"FAIL  {msg}")

    def warn(self, msg: str) -> None:
        print(f"warn  {msg}")


def split_frontmatter(text: str) -> tuple[dict[str, str], str] | None:
    """Return (fields, body) or None. Parses the simple 'key: value' form skills use,
    including folded values continued on indented lines, without needing PyYAML.
    Windows line endings are accepted: a SKILL.md saved with CRLF is still valid."""
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    raw, body = text[4:end], text[end + 4:].lstrip("\n")
    fields: dict[str, str] = {}
    key = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        if line[0] in " \t" and key:
            fields[key] = (fields[key] + " " + line.strip()).strip()
            continue
        if ":" not in line:
            return None
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value in (">", "|", ">-", "|-"):
            value = ""
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        fields[key] = value
    return fields, body


def check(folder: Path, extra_patterns: list[str]) -> int:
    r = Report()
    skill_md = folder / "SKILL.md"
    if not skill_md.is_file():
        r.fail(f"{skill_md} not found")
        return 1
    try:
        text = skill_md.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        r.fail("SKILL.md is not valid UTF-8; save it as UTF-8")
        return 1
    parsed = split_frontmatter(text)
    if parsed is None:
        r.fail("SKILL.md must start with frontmatter between two '---' lines, as 'key: value' pairs")
        return 1
    fields, body = parsed
    r.ok("frontmatter parses")

    name = fields.get("name", "")
    if not name:
        r.fail("name is missing")
    else:
        if len(name) > NAME_MAX:
            r.fail(f"name is {len(name)} characters; the limit is {NAME_MAX}")
        if not NAME_PATTERN.match(name):
            r.fail(f"name '{name}' must be lowercase letters, digits and single hyphens")
        for word in RESERVED_WORDS:
            if word in name:
                r.fail(f"name '{name}' contains the reserved word '{word}'")
        if XML_TAG.search(name):
            r.fail(f"name '{name}' contains an XML tag")
        if name != folder.name:
            r.fail(f"name '{name}' does not match the folder name '{folder.name}'")
        else:
            r.ok(f"name '{name}' matches the folder")

    desc = fields.get("description", "")
    if not desc:
        r.fail("description is missing or empty")
    else:
        if len(desc) > DESCRIPTION_MAX:
            r.fail(f"description is {len(desc)} characters; the limit is {DESCRIPTION_MAX}")
        else:
            r.ok(f"description is {len(desc)} characters")
        tags = XML_TAG.findall(desc)
        if tags:
            r.fail(f"description contains XML tags ({', '.join(sorted(set(tags))[:3])}); remove them")
        if not re.search(r"\b(use|used) (it |this )?(when|for|to|before|after)\b", desc, re.I):
            r.warn("description does not seem to say when to use the skill ('Use when ...')")
        if re.match(r"\s*(I |I'm |you can |this skill lets you)", desc, re.I):
            r.warn("description should be in the third person ('Builds ...', not 'I can ...')")

    lines = body.count("\n") + 1
    if lines > BODY_LINES_MAX:
        r.fail(f"body is {lines} lines; keep it under {BODY_LINES_MAX} and move depth to references/")
    elif lines > BODY_LINES_WARN:
        r.warn(f"body is {lines} lines; consider moving detail to references/")
    else:
        r.ok(f"body is {lines} lines")

    for target in LINK.findall(body):
        if re.match(r"^[a-z]+:", target) or target.startswith("#"):
            continue
        path = (folder / target.split("#", 1)[0]).resolve()
        skills_dir = folder.resolve().parent
        inside = path.is_relative_to(folder.resolve())
        sibling = (not inside and path.is_relative_to(skills_dir)
                   and len(path.relative_to(skills_dir).parts) > 1
                   and (skills_dir / path.relative_to(skills_dir).parts[0] / "SKILL.md").is_file())
        if sibling and path.exists():
            r.warn(f"link '{target}' points into a sibling skill: fine inside an installed plugin, "
                   "but it breaks if this skill is uploaded on its own, so keep the body usable without it")
        elif not inside:
            r.fail(f"link '{target}' points outside the skill folder")
        elif not path.exists():
            r.fail(f"link '{target}' does not resolve to a file")
        else:
            r.ok(f"link '{target}' resolves")

    for ref in sorted(folder.rglob("*.md")):
        if ref == skill_md:
            continue
        ref_lines = ref.read_text(encoding="utf-8", errors="replace").splitlines()
        if len(ref_lines) > TOC_THRESHOLD and not any(
            re.match(r"^#+\s*(contents|table of contents)\s*$", l, re.I) for l in ref_lines[:15]
        ):
            r.warn(f"{ref.relative_to(folder)} is {len(ref_lines)} lines with no contents list near the top")

    extra = [(p, re.compile(re.escape(p), re.I)) for p in extra_patterns]
    for f in sorted(folder.rglob("*")):
        if not f.is_file() or f.suffix not in TEXT_SUFFIXES or f.resolve() == Path(__file__).resolve():
            continue
        content = f.read_text(encoding="utf-8", errors="replace")
        rel = f.relative_to(folder)
        # Files under a templates/ folder are meant to hold placeholders; everything
        # else must have had them filled in.
        if "templates" not in rel.parts:
            for m in PLACEHOLDER.finditer(content):
                r.fail(f"{rel}: leftover placeholder '{m.group(0)}'")
        for pat in SECRET_PATTERNS:
            if pat.search(content):
                r.fail(f"{rel}: looks like it contains a secret ({pat.pattern[:30]}...)")
        for text, pat in extra:
            if pat.search(content):
                r.fail(f"{rel}: contains '{text}'")

    print()
    print("FAILED" if r.failures else "PASSED", f"({r.failures} failure(s))")
    return 1 if r.failures else 0


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("folder", type=Path)
    ap.add_argument("--check-text", nargs="*", default=[], metavar="PATTERN",
                    help="text that must not appear anywhere, e.g. a company or client name")
    args = ap.parse_args()
    sys.exit(check(args.folder.resolve(), args.check_text))


if __name__ == "__main__":
    main()
