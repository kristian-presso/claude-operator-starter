#!/usr/bin/env python3
"""Approval gate: a Claude Code PreToolUse hook that stops and asks before Claude sends,
publishes, pays or deletes.

Reads the hook's JSON from stdin. Prints a PreToolUse decision on stdout:
  - "ask"  when the call matches a built-in gate or an "ask" entry in the config
  - "deny" when the call matches a "deny" entry in the config
  - nothing (exit 0) otherwise, so Claude Code's normal permission flow applies

An "allow" entry only waives this gate. It never grants a permission Claude Code would
otherwise ask for.

Config: .claude/approval-gate.json in the project (or the path in APPROVAL_GATE_CONFIG):

  {
    "allow": ["Bash(git push origin main)"],
    "ask":   ["mcp__*__create_post", "Bash(terraform apply*)"],
    "deny":  ["Bash(git push --force*)"],
    "protected_branches": ["main", "master"],
    "payment_hosts": ["api.example-bank.com"]
  }

Entries use Claude Code's permission rule shape: "ToolName" or "ToolName(pattern)", with
shell-style wildcards. For Bash the pattern matches the command (or any one part of a
compound command); for other tools it matches the tool input as compact JSON.

Precedence: deny, then allow, then ask. Python standard library only.
This is a best-effort guard rail, not a sandbox: a determined command can get past any
text-matching hook, so keep real secrets and permissions locked down too.
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import shlex
import subprocess
import sys
from urllib.parse import urlparse

CONFIG_REL = os.path.join(".claude", "approval-gate.json")
DEFAULT_PROTECTED = ["main", "master"]
DEFAULT_PAYMENT_HOSTS = [
    "api.stripe.com",
    "api.paypal.com",
    "api-m.paypal.com",
    "connect.squareup.com",
    "api.gocardless.com",
    "api.paddle.com",
    "api.lemonsqueezy.com",
    "api.wise.com",
    "api.mollie.com",
    "api.razorpay.com",
    "api.checkout.com",
    "api.braintreegateway.com",
]

# MCP tool-name words that mean the call sends, publishes, pays or deletes.
MCP_GATED = {
    "send": "sends a message",
    "reply": "sends a reply",
    "forward": "forwards a message",
    "broadcast": "sends a broadcast",
    "publish": "publishes",
    "unpublish": "unpublishes",
    "tweet": "publishes a post",
    "pay": "makes a payment",
    "payment": "makes a payment",
    "payments": "makes a payment",
    "charge": "charges money",
    "charges": "charges money",
    "payout": "pays money out",
    "payouts": "pays money out",
    "refund": "refunds money",
    "refunds": "refunds money",
    "transfer": "moves money",
    "transfers": "moves money",
    "delete": "deletes",
    "trash": "deletes",
    "destroy": "deletes",
    "purge": "deletes",
    "erase": "deletes",
}
# A tool whose name starts with one of these only reads, whatever else it mentions.
MCP_READ_VERBS = {
    "get", "list", "search", "read", "find", "query", "fetch", "describe", "count",
    "preview", "check", "retrieve", "lookup", "show", "view", "validate", "estimate",
    "compose", "draft",
}

PUBLISH_COMMANDS = {
    ("npm", "publish"), ("pnpm", "publish"), ("yarn", "publish"), ("bun", "publish"),
    ("npm", "unpublish"), ("cargo", "publish"), ("poetry", "publish"),
    ("twine", "upload"), ("gem", "push"),
}
MAIL_COMMANDS = {"sendmail", "mail", "mailx", "mutt"}
WRAPPERS = {"sudo", "env", "nohup", "time", "command", "exec", "nice", "doas"}
SEPARATORS = {";", "&&", "||", "|", "&", "\n", "|&", "(", ")"}
ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
SUBSHELL = re.compile(r"\$\(([^()]*)\)|`([^`]*)`")


# ---------------------------------------------------------------- output helpers

def decide(decision: str, reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }))


def ask_text(what: str, detail: str) -> str:
    return (
        f"Approval gate: this {what}: {detail}. "
        "Confirm with the person before it runs. To stop being asked for this, add an "
        "\"allow\" entry to .claude/approval-gate.json."
    )


# ---------------------------------------------------------------- config

def load_config(project_dir: str) -> tuple[dict, str | None]:
    """Return (config, problem). A missing file is fine; a broken one is reported."""
    path = os.environ.get("APPROVAL_GATE_CONFIG") or os.path.join(project_dir, CONFIG_REL)
    if not os.path.isfile(path):
        return {}, None
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        return {}, f"could not read {path} ({exc.__class__.__name__}); using built-in rules only"
    if not isinstance(data, dict):
        return {}, f"{path} must hold a JSON object; using built-in rules only"
    clean: dict = {}
    for key in ("allow", "ask", "deny", "protected_branches", "payment_hosts"):
        value = data.get(key, [])
        if isinstance(value, list) and all(isinstance(v, str) for v in value):
            clean[key] = value
    return clean, None


RULE = re.compile(r"^([^()]+?)(?:\((.*)\))?$", re.S)


def rule_matches(rule: str, tool: str, tool_input: dict, segments: list[str]) -> bool:
    m = RULE.match(rule.strip())
    if not m:
        return False
    name, pattern = m.group(1).strip(), m.group(2)
    if not fnmatch.fnmatchcase(tool, name):
        return False
    if pattern is None:
        return True
    if tool == "Bash":
        command = str(tool_input.get("command", ""))
        candidates = [command.strip()] + segments
        return any(fnmatch.fnmatchcase(c, pattern) for c in candidates)
    blob = json.dumps(tool_input, sort_keys=True, separators=(",", ":"))
    return fnmatch.fnmatchcase(blob, pattern)


# ---------------------------------------------------------------- shell parsing

def split_commands(command: str) -> list[list[str]]:
    """Split a shell command into simple commands (token lists), best effort.

    Handles quotes, ; && || | &, newlines, $( ) and backticks, and `bash -c "..."`.
    """
    extra: list[str] = []
    for m in SUBSHELL.finditer(command):
        extra.append(m.group(1) if m.group(1) is not None else m.group(2))
    try:
        lex = shlex.shlex(command, posix=True, punctuation_chars=";&|()\n")
        lex.whitespace = " \t\r"
        lex.whitespace_split = True
        tokens = list(lex)
    except ValueError:
        # Unbalanced quotes: fall back to a crude split so nothing is silently skipped.
        tokens = re.split(r"\s+", re.sub(r"(;|&&|\|\||\||&|\n)", r" \1 ", command))
        tokens = [t.strip("'\"") for t in tokens if t]
    out: list[list[str]] = []
    current: list[str] = []
    for tok in tokens:
        if tok in SEPARATORS or (tok and set(tok) <= set(";&|()\n")):
            if current:
                out.append(current)
            current = []
        else:
            current.append(tok)
    if current:
        out.append(current)
    for inner in extra:
        out.extend(split_commands(inner))
    # Recurse into `bash -c "..."` and friends.
    for toks in list(out):
        core = strip_wrappers(toks)
        if len(core) >= 3 and os.path.basename(core[0]) in {"bash", "sh", "zsh", "dash"} and "-c" in core[1:]:
            idx = core.index("-c")
            if idx + 1 < len(core):
                out.extend(split_commands(core[idx + 1]))
    return out


def strip_wrappers(tokens: list[str]) -> list[str]:
    toks = list(tokens)
    while toks:
        if ASSIGNMENT.match(toks[0]):
            toks.pop(0)
        elif os.path.basename(toks[0]) in WRAPPERS:
            toks.pop(0)
            while toks and toks[0].startswith("-"):
                toks.pop(0)
        else:
            break
    return toks


# ---------------------------------------------------------------- built-in gates

def current_branch(cwd: str, git_dir_args: list[str]) -> str | None:
    try:
        res = subprocess.run(
            ["git", *git_dir_args, "symbolic-ref", "--short", "-q", "HEAD"],
            cwd=cwd if os.path.isdir(cwd) else None,
            capture_output=True, text=True, timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return res.stdout.strip() if res.returncode == 0 and res.stdout.strip() else None


def check_git_push(toks: list[str], cwd: str, protected: list[str]) -> str | None:
    if not toks or os.path.basename(toks[0]) != "git":
        return None
    i, git_dir_args = 1, []
    while i < len(toks) and toks[i].startswith("-"):
        if toks[i] in ("-C", "-c", "--git-dir", "--work-tree") and i + 1 < len(toks):
            if toks[i] == "-C":
                git_dir_args = ["-C", toks[i + 1]]
            i += 2
        else:
            i += 1
    if i >= len(toks) or toks[i] != "push":
        return None
    args = toks[i + 1:]
    shown = " ".join(toks)
    risky = {"--force", "-f", "--force-with-lease", "--mirror", "--all", "--delete", "-d", "--prune"}
    for a in args:
        if a in risky or a.startswith("--force-with-lease=") or (re.match(r"^-[a-zA-Z]+$", a) and "f" in a[1:]):
            return ask_text("command force-pushes, deletes or mirrors branches on a remote", shown)
    positionals = []
    skip = False
    for a in args:
        if skip:
            skip = False
            continue
        if a in ("-o", "--push-option", "--repo", "--receive-pack", "--exec"):
            skip = True
            continue
        if not a.startswith("-"):
            positionals.append(a)
    refspecs = positionals[1:]
    if not refspecs:
        branch = current_branch(cwd, git_dir_args)
        if branch is None:
            return ask_text("command pushes, and the current branch could not be read", shown)
        return ask_text(f"command pushes to {branch}", shown) if branch in protected else None
    for ref in refspecs:
        ref = ref.lstrip("+")
        dst = ref.split(":", 1)[1] if ":" in ref else ref
        dst = dst.replace("refs/heads/", "", 1)
        if dst == "HEAD":
            dst = current_branch(cwd, git_dir_args) or "HEAD"
        if dst in protected or dst == "HEAD":
            return ask_text(f"command pushes to {dst}", shown)
    return None


def check_publish(toks: list[str]) -> str | None:
    if len(toks) < 2:
        return None
    tool = os.path.basename(toks[0])
    shown = " ".join(toks)
    if "--dry-run" in toks:
        return None
    if (tool, toks[1]) in PUBLISH_COMMANDS:
        return ask_text("command publishes a package", shown)
    if tool == "yarn" and len(toks) >= 3 and toks[1] == "npm" and toks[2] == "publish":
        return ask_text("command publishes a package", shown)
    if tool == "gh" and len(toks) >= 3 and toks[1] == "release" and toks[2] == "create":
        return ask_text("command publishes a release", shown)
    return None


def check_mail(toks: list[str]) -> str | None:
    if toks and os.path.basename(toks[0]) in MAIL_COMMANDS and len(toks) > 1:
        return ask_text("command sends email", " ".join(toks))
    return None


def inside(path: str, root: str) -> bool:
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def check_rm(toks: list[str], cwd: str, project: str) -> str | None:
    if not toks or os.path.basename(toks[0]) != "rm":
        return None
    recursive, targets, end_of_flags = False, [], False
    for a in toks[1:]:
        if not end_of_flags and a == "--":
            end_of_flags = True
        elif not end_of_flags and a.startswith("--"):
            recursive = recursive or a == "--recursive"
        elif not end_of_flags and a.startswith("-") and len(a) > 1:
            recursive = recursive or "r" in a or "R" in a
        else:
            targets.append(a)
    if not recursive:
        return None
    shown = " ".join(toks)
    root = os.path.realpath(project)
    for t in targets:
        expanded = os.path.expandvars(os.path.expanduser(t))
        if "$" in expanded or "`" in expanded:
            return ask_text("command recursively deletes a path that could not be resolved", shown)
        base = expanded.split("*", 1)[0].split("?", 1)[0] or "."
        full = os.path.realpath(os.path.join(cwd, base))
        if full == root:
            return ask_text("command recursively deletes the whole project", shown)
        if not inside(full, root):
            return ask_text("command recursively deletes files outside the project", shown)
    return None


def host_matches(host: str, hosts: list[str]) -> bool:
    host = (host or "").lower()
    return any(host == h.lower() or host.endswith("." + h.lower()) for h in hosts)


def check_http(toks: list[str], hosts: list[str]) -> str | None:
    if not toks:
        return None
    tool = os.path.basename(toks[0])
    shown = " ".join(toks)
    writes = {"POST", "PUT", "PATCH", "DELETE"}
    urls = [t for t in toks if re.match(r"^https?://", t, re.I)]
    method = None
    if tool == "curl":
        data, get = False, False
        for i, t in enumerate(toks):
            if t in ("-X", "--request") and i + 1 < len(toks):
                method = toks[i + 1].upper()
            elif t.startswith("-X") and len(t) > 2:
                method = t[2:].upper()
            elif t.startswith("--request="):
                method = t.split("=", 1)[1].upper()
            elif t in ("-d", "-F", "--form", "--json", "-T", "--upload-file") or t.startswith("--data") or t.startswith("--form") or t.startswith("--json"):
                data = True
            elif t in ("-G", "--get"):
                get = True
            elif t == "--url" and i + 1 < len(toks):
                urls.append(toks[i + 1])
        if method is None and data and not get:
            method = "POST"
    elif tool == "wget":
        for t in toks:
            if t.startswith("--method="):
                method = t.split("=", 1)[1].upper()
            elif t.startswith(("--post-data", "--post-file", "--body-data", "--body-file")):
                method = method or "POST"
    elif tool in ("http", "https", "xh") and len(toks) > 2 and toks[1].upper() in writes:
        method = toks[1].upper()
        urls += [t if "://" in t else "https://" + t for t in toks[2:3]]
    elif tool == "stripe" and any(t in ("create", "delete", "update", "post", "cancel", "capture", "pay") for t in toks[1:]):
        return ask_text("command changes live payment data with the Stripe CLI", shown)
    if method not in writes:
        return None
    for u in urls:
        if host_matches(urlparse(u).hostname or "", hosts):
            return ask_text(f"command sends a {method} request to a payment API", shown)
    return None


def check_bash(command: str, cwd: str, project: str, cfg: dict) -> list[tuple[str, str]]:
    """Return (segment text, reason) for every gated part of the command."""
    protected = cfg.get("protected_branches") or DEFAULT_PROTECTED
    hosts = DEFAULT_PAYMENT_HOSTS + cfg.get("payment_hosts", [])
    hits = []
    eff_cwd = cwd
    for raw in split_commands(command):
        toks = strip_wrappers(raw)
        if not toks:
            continue
        if toks[0] == "cd":
            target = os.path.expanduser(toks[1]) if len(toks) > 1 else os.path.expanduser("~")
            eff_cwd = os.path.normpath(os.path.join(eff_cwd, target))
            continue
        for check in (
            lambda t: check_git_push(t, eff_cwd, protected),
            check_publish,
            check_mail,
            lambda t: check_rm(t, eff_cwd, project),
            lambda t: check_http(t, hosts),
        ):
            reason = check(toks)
            if reason:
                hits.append((" ".join(raw), reason))
                break
    return hits


def mcp_words(tool: str) -> list[str]:
    name = tool.split("__")[-1]
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return [w for w in re.split(r"[_\-\s.]+", name.lower()) if w]


def check_mcp(tool: str) -> str | None:
    if not tool.startswith("mcp__"):
        return None
    words = mcp_words(tool)
    if not words or words[0] in MCP_READ_VERBS:
        return None
    for w in words:
        if w in MCP_GATED:
            return ask_text(f"tool {MCP_GATED[w]}", tool)
    return None


# ---------------------------------------------------------------- main

def evaluate(payload: object) -> tuple[str, str] | None:
    """Return (decision, reason), or None to stay silent."""
    if not isinstance(payload, dict) or not isinstance(payload.get("tool_name"), str):
        return ("ask", "Approval gate: the tool call could not be read, so it was not checked. "
                       "Confirm with the person before it runs.")
    tool = payload["tool_name"]
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = {}
    cwd = payload.get("cwd") if isinstance(payload.get("cwd"), str) else os.getcwd()
    project = os.environ.get("CLAUDE_PROJECT_DIR") or cwd
    cfg, problem = load_config(project)

    segments: list[str] = []
    if tool == "Bash":
        command = tool_input.get("command")
        if not isinstance(command, str):
            return ("ask", "Approval gate: this Bash call has no readable command, so it was not "
                           "checked. Confirm with the person before it runs.")
        segments = [" ".join(s) for s in split_commands(command)]

    for rule in cfg.get("deny", []):
        if rule_matches(rule, tool, tool_input, segments):
            return ("deny", f"Approval gate: blocked by the deny rule \"{rule}\" in "
                            ".claude/approval-gate.json. Do not retry; tell the person.")

    allowed = [r for r in cfg.get("allow", [])]

    def waived(seg: str | None) -> bool:
        segs = [seg] if seg else segments
        return any(rule_matches(r, tool, tool_input, segs) for r in allowed)

    reasons: list[str] = []
    if tool == "Bash":
        for seg, reason in check_bash(tool_input["command"], cwd, project, cfg):
            if not waived(seg):
                reasons.append(reason)
    else:
        reason = check_mcp(tool)
        if reason and not waived(None):
            reasons.append(reason)

    for rule in cfg.get("ask", []):
        if rule_matches(rule, tool, tool_input, segments) and not waived(None):
            reasons.append(f"Approval gate: \"{rule}\" is on the ask list in "
                           ".claude/approval-gate.json. Confirm with the person before it runs.")
            break

    if not reasons:
        return None
    reason = reasons[0]
    if problem:
        reason += f" (Note: {problem}.)"
    return ("ask", reason)


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw) if raw.strip() else None
    except ValueError:
        payload = None
    result = evaluate(payload)
    if result:
        decide(*result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
