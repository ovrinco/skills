#!/usr/bin/env python3
"""Find ONE chat session and export it word for word.

Reads one session log of Claude Code (~/.claude/projects/*/*.jsonl) or Codex
(~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl) and writes
<out-root>/<provider>/<date>_<id>/export.md and record.json.

Standard library only. No network. The session log is opened read-only and is
never changed, moved or pruned. One session per run: there is no batch mode.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

VERSION = "2026-10-04"
HOME = Path.home()
CLAUDE_HOME = HOME / ".claude"
CODEX_HOME = HOME / ".codex"
CLAUDE_STORE = CLAUDE_HOME / "projects"
CODEX_STORE = CODEX_HOME / "sessions"
DEFAULT_OUT_ROOT = Path.cwd() / "chat-output"

REFUSAL = ("refused: chat-distill exports one session per run. Name one session "
           "(--source PATH, --session-id ID, --match TEXT or --latest).")
MANY_FLAGS = {"--all", "--all-sessions", "--batch", "--every", "--since", "--until", "--days", "--week",
              "--today", "--last", "--recent"}
MANY_WORDS = {"all", "batch", "export-all", "discover-all"}

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
NOTIF_RE = re.compile(r"<task-notification>.*?</task-notification>", re.S)
CODEX_ID_RE = re.compile(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.jsonl$")
CLAUDE_CONTINUATION = "This session is being continued from a previous conversation"
CLAUDE_INTERRUPT = "[Request interrupted by user"
CLAUDE_SKIP_WRAPPERS = ("<local-command-caveat>", "<local-command-stdout>", "<local-command-stderr>",
                        "<command-message>", "<command-args>", "<system-reminder>")
# Codex puts harness text into user-role messages; these openings mark it.
CODEX_HARNESS_OPENINGS = ("# AGENTS.md instructions", "<environment_context>", "<user_instructions>",
                          "<skills_instructions>", "<permissions instructions>", "<collaboration_mode>",
                          "<user_shell_command>", "<system-reminder>", "<INSTRUCTIONS>")

# Secrets are masked in everything that is written. Pattern-based: a secret in an unusual form can pass.
_SECRET_PATTERNS = [
    ("private-key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S)),
    ("anthropic-key", re.compile(r"\bsk-ant-[A-Za-z0-9_\-]{20,}")),
    ("openai-key", re.compile(r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_\-]{20,}")),
    ("github-token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})")),
    ("aws-key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("google-key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}")),
    ("slack-token", re.compile(r"\bxox[abposr]-[A-Za-z0-9\-]{10,}")),
    ("huggingface-token", re.compile(r"\bhf_[A-Za-z0-9]{30,}")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}")),
]
_BEARER_RE = re.compile(r"(?i)(\bBearer\s+)([A-Za-z0-9._~+/\-]{20,}=*)")
_ASSIGNED_RE = re.compile(
    r"(?i)(\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|refresh[_-]?token|client[_-]?secret|secret[_-]?key"
    r"|secret|password|passwd|token)\b[\"']?\s*[:=]\s*[\"']?)([A-Za-z0-9_\-+=.]{20,})")


class Masker:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}

    def _hit(self, kind: str) -> str:
        self.counts[kind] = self.counts.get(kind, 0) + 1
        return f"[masked:{kind}]"

    def __call__(self, text: str) -> str:
        for kind, pattern in _SECRET_PATTERNS:
            text = pattern.sub(lambda m, k=kind: self._hit(k), text)
        text = _BEARER_RE.sub(lambda m: m.group(1) + self._hit("bearer-token"), text)

        def assigned(m: re.Match) -> str:
            value = m.group(2)
            if re.search(r"[0-9]", value) and re.search(r"[A-Za-z]", value):
                return m.group(1) + self._hit("assigned-secret")
            return m.group(0)
        return _ASSIGNED_RE.sub(assigned, text)

    @property
    def total(self) -> int:
        return sum(self.counts.values())


# ------------------------------------------------------------------ reading
def read_jsonl(path: Path, stats: dict, limit: int | None = None) -> Iterator[dict]:
    """One record at a time; the file is never loaded whole. Unreadable lines are counted, not fatal
    (a session that is still running can end on a half-written line). With `limit`, nothing past that
    byte is read: a session that grows during the export is exported up to the size seen at the start."""
    consumed = 0
    with path.open("rb") as handle:
        for raw_bytes in handle:
            consumed += len(raw_bytes)
            if limit is not None and consumed > limit:
                break
            stats["source_lines"] = stats.get("source_lines", 0) + 1
            line = raw_bytes.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                stats["unreadable_lines"] = stats.get("unreadable_lines", 0) + 1
                continue
            if isinstance(obj, dict):
                yield obj


def sha256_of(path: Path, limit: int | None = None) -> str:
    """Hash of the file, or of its first `limit` bytes."""
    digest, left = hashlib.sha256(), limit
    with path.open("rb") as handle:
        while left is None or left > 0:
            chunk = handle.read(1 << 20 if left is None else min(1 << 20, left))
            if not chunk:
                break
            digest.update(chunk)
            if left is not None:
                left -= len(chunk)
    return digest.hexdigest()


def detect_provider(path: Path) -> str:
    for n, obj in enumerate(read_jsonl(path, {})):
        if obj.get("type") in {"session_meta", "event_msg", "response_item", "turn_context"} and "payload" in obj:
            return "codex"
        if "sessionId" in obj or obj.get("type") in {"user", "assistant", "file-history-snapshot"}:
            return "claude"
        if n > 200:
            break
    raise ValueError(f"not a Claude Code or Codex session log: {path}")


def first_timestamp(path: Path) -> str | None:
    for n, obj in enumerate(read_jsonl(path, {})):
        ts = obj.get("timestamp")
        if isinstance(ts, str) and ts:
            return ts
        if n > 500:
            break
    return None


# ------------------------------------------------------------------ finding one session
def claude_files() -> list[Path]:
    return [p for p in CLAUDE_STORE.glob("*/*.jsonl") if p.is_file()]


def codex_files() -> list[Path]:
    return [p for p in CODEX_STORE.glob("*/*/*/rollout-*.jsonl") if p.is_file()]


def session_id_of(provider: str, path: Path) -> str:
    if provider == "codex":
        m = CODEX_ID_RE.search(path.name)
        return m.group(1) if m else path.stem
    return path.stem


def by_id(provider: str, wanted: str) -> list[tuple[str, Path]]:
    found = []
    if provider in ("auto", "claude"):
        found += [("claude", p) for p in claude_files() if p.stem.startswith(wanted)]
    if provider in ("auto", "codex"):
        found += [("codex", p) for p in codex_files() if session_id_of("codex", p).startswith(wanted)]
    return found


def history_matches(provider: str, fragment: str) -> dict[tuple[str, str], float]:
    """Session ids whose prompt history holds the fragment, with the time of the newest matching prompt."""
    needle = fragment.lower()
    hits: dict[tuple[str, str], float] = {}
    sources = []
    if provider in ("auto", "claude"):
        sources.append(("claude", CLAUDE_HOME / "history.jsonl", "sessionId", "display", 1000.0))
    if provider in ("auto", "codex"):
        sources.append(("codex", CODEX_HOME / "history.jsonl", "session_id", "text", 1.0))
    for prov, path, id_key, text_key, divisor in sources:
        if not path.exists():
            continue
        for obj in read_jsonl(path, {}):
            sid, text = obj.get(id_key), obj.get(text_key)
            stamp = obj.get("timestamp", obj.get("ts"))
            if not sid or not isinstance(text, str) or stamp is None or needle not in text.lower():
                continue
            when = float(stamp) / divisor
            if when > hits.get((prov, sid), 0.0):
                hits[(prov, sid)] = when
    return hits


def resolve(args: argparse.Namespace) -> dict:
    note = None
    if args.source:
        path = Path(args.source).expanduser()
        if any(ch in args.source for ch in "*?[") or path.is_dir():
            raise SystemExit(REFUSAL)
        if not path.is_file():
            raise FileNotFoundError(f"no such session file: {path}")
        provider = detect_provider(path)
    elif args.session_id:
        found = by_id(args.provider, args.session_id)
        if not found:
            raise FileNotFoundError(f"no session with id '{args.session_id}' in the {args.provider} store(s)")
        if len(found) > 1:
            raise ValueError(f"{len(found)} sessions start with '{args.session_id}': give more of the id")
        provider, path = found[0]
    elif args.match:
        hits = history_matches(args.provider, args.match)
        ranked = sorted(hits.items(), key=lambda item: item[1], reverse=True)
        provider = path = None
        for (prov, sid), _when in ranked:
            found = by_id(prov, sid)
            if len(found) == 1:
                provider, path = found[0]
                break
        if path is None:
            raise FileNotFoundError(f"no session's prompt history contains '{args.match}'")
        if len(ranked) > 1:
            note = f"{len(ranked)} sessions contain the fragment; this is the most recent. Use --session-id for another."
    else:  # --latest
        pool = []
        if args.provider in ("auto", "claude"):
            pool += [("claude", p) for p in claude_files()]
        if args.provider in ("auto", "codex"):
            pool += [("codex", p) for p in codex_files()]
        if not pool:
            raise FileNotFoundError("no session found")
        provider, path = max(pool, key=lambda item: item[1].stat().st_mtime)
    stat = path.stat()
    return {
        "provider": provider,
        "session_id": session_id_of(provider, path),
        "source": str(path.resolve()),
        "bytes": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(timespec="seconds"),
        "first_timestamp": first_timestamp(path),
        "note": note,
    }


# ------------------------------------------------------------------ parsing
# Each parser yields (kind, text, timestamp, detail):
#   "user" / "assistant": one turn, text in full   "boundary": context compacted
#   "notice": one line about a harness event       "tool": one work-log line
def tag(block: str, name: str) -> str:
    m = re.search(rf"<{name}>(.*?)</{name}>", block, re.S)
    return m.group(1).strip() if m else ""


def notification_lines(text: str) -> list[str]:
    lines = []
    for block in NOTIF_RE.findall(text):
        summary = tag(block, "summary") or "background task notice"
        status = tag(block, "status")
        lines.append(f"harness notice: {summary}" + (f" [{status}]" if status and status not in summary else ""))
    return lines


def claude_parts(content: object) -> tuple[str, list[str], bool]:
    """Text of a user record, attachment markers, and whether it carries tool results."""
    if isinstance(content, str):
        return content, [], False
    texts, attachments, has_tool_result = [], [], False
    if isinstance(content, list):
        for block in content:
            if not isinstance(block, dict):
                continue
            kind = block.get("type")
            if kind == "text" and isinstance(block.get("text"), str):
                texts.append(block["text"])
            elif kind == "tool_result":
                has_tool_result = True
            elif kind in ("image", "document", "file"):
                name = block.get("name") or block.get("title") or (block.get("source") or {}).get("media_type") or ""
                attachments.append(f"{kind}{': ' + str(name) if name else ''}")
    return "\n\n".join(texts), attachments, has_tool_result


def claude_tool_line(name: str, inp: dict) -> str:
    target = ""
    if isinstance(inp, dict):
        for key in ("file_path", "notebook_path", "description", "skill", "url", "query", "pattern", "path"):
            if inp.get(key):
                target = str(inp[key]).replace("\n", " ")[:160]
                break
    return f"{name}: {target}" if target else name


def parse_claude(path: Path, stats: dict, limit: int | None = None) -> Iterator[tuple[str, str, str | None, dict]]:
    seen: set[str] = set()
    modern = False  # today's logs mark who sent a user record in `origin`; older logs do not
    for obj in read_jsonl(path, stats, limit):
        uid = obj.get("uuid")
        if uid:
            if uid in seen:
                continue
            seen.add(uid)
        if obj.get("isSidechain"):
            continue
        kind, ts = obj.get("type"), obj.get("timestamp")

        if kind == "system" and obj.get("subtype") == "compact_boundary":
            meta = obj.get("compactMetadata") or {}
            yield "boundary", "", ts, {"trigger": meta.get("trigger"), "before": meta.get("preTokens"),
                                       "after": meta.get("postTokens")}
            continue

        if kind == "attachment":
            att = obj.get("attachment") or {}
            if att.get("type") != "queued_command":
                continue
            text, attachments, _ = claude_parts(att.get("prompt"))
            notes = notification_lines(text)
            if notes:
                for line in notes:
                    yield "notice", line, ts, {}
            elif (att.get("origin") or {}).get("kind") == "human" or att.get("humanTurn"):
                # A message the operator sent while the assistant was working. The log keeps it as an
                # attachment, not as a user record, but it is the operator's words: exported as a turn.
                yield "user", text, att.get("timestamp") or ts, {"mid_turn": True, "attachments": attachments}
            continue

        if kind == "user":
            text, attachments, has_tool_result = claude_parts((obj.get("message") or {}).get("content"))
            if obj.get("isCompactSummary"):
                # The summary the harness wrote after a compaction sits in a user record, sometimes with a
                # human turn origin. It is not the operator's: one labelled line, the text is not exported.
                yield "notice", (f"harness summary of the conversation so far ({len(text):,} characters), written "
                                 "by the harness after the compaction; not an operator turn, not exported"), ts, {}
                continue
            if has_tool_result or obj.get("toolUseResult") is not None or obj.get("sourceToolAssistantUUID"):
                continue
            if "origin" in obj:
                modern = True
            origin = (obj.get("origin") or {}).get("kind")
            head = text.lstrip()
            if origin == "human":
                if text.strip() or attachments:
                    yield "user", text, ts, {"mid_turn": False, "attachments": attachments}
                continue
            if origin == "task-notification" or head.startswith("<task-notification>"):
                for line in notification_lines(text) or ["harness notice: background task"]:
                    yield "notice", line, ts, {}
                continue
            if head.startswith(CLAUDE_INTERRUPT):
                yield "notice", "the operator interrupted the assistant", ts, {}
                continue
            if "<command-name>" in head[:400]:
                yield "notice", f"the operator ran the local command `{tag(head, 'command-name') or '?'}`", ts, {}
                continue
            if obj.get("isMeta") or head.startswith(CLAUDE_SKIP_WRAPPERS):
                continue
            if head.startswith(CLAUDE_CONTINUATION):
                yield "boundary", "", ts, {"trigger": "continued from an earlier conversation"}
                continue
            if modern or origin is not None:
                continue  # a record today's harness wrote itself
            if text.strip() or attachments:  # older log: plain user text is the operator's
                yield "user", text, ts, {"mid_turn": False, "attachments": attachments}
            continue

        if kind == "assistant":
            message = obj.get("message") or {}
            synthetic = message.get("model") == "<synthetic>"
            for block in message.get("content") or []:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "text" and isinstance(block.get("text"), str) and block["text"].strip():
                    if synthetic:
                        yield "notice", "harness message: " + block["text"].strip().replace("\n", " ")[:200], ts, {}
                    else:
                        yield "assistant", block["text"], ts, {}
                elif block.get("type") == "tool_use":
                    yield "tool", claude_tool_line(str(block.get("name")), block.get("input") or {}), ts, {}


def codex_is_modern(path: Path, limit: int | None = None) -> bool:
    """Today's Codex logs carry the conversation as response_item messages; older ones as event messages."""
    for obj in read_jsonl(path, {}, limit):
        payload = obj.get("payload")
        if obj.get("type") == "response_item" and isinstance(payload, dict) and payload.get("type") == "message" \
                and payload.get("role") in ("user", "assistant"):
            return True
    return False


def parse_codex(path: Path, stats: dict, limit: int | None = None) -> Iterator[tuple[str, str, str | None, dict]]:
    modern = codex_is_modern(path, limit)
    for obj in read_jsonl(path, stats, limit):
        kind, ts, payload = obj.get("type"), obj.get("timestamp"), obj.get("payload")
        if not isinstance(payload, dict):
            continue
        ptype = payload.get("type")
        if kind == "compacted" or (kind == "event_msg" and ptype == "context_compacted"):
            yield "boundary", "", ts, {"trigger": "codex"}
            continue
        if kind == "response_item" and ptype in ("function_call", "custom_tool_call", "local_shell_call"):
            yield "tool", str(payload.get("name") or ptype), ts, {}
            continue
        if modern and kind == "response_item" and ptype == "message":
            role = payload.get("role")
            if role not in ("user", "assistant"):
                continue  # developer text is system text
            texts, attachments = [], []
            for block in payload.get("content") or []:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype in ("input_text", "output_text", "text") and isinstance(block.get("text"), str):
                    text = block["text"]
                    head = text.lstrip()
                    if role == "user":
                        if head.startswith("<subagent_notification>"):
                            yield "notice", "harness notice: a sub-agent reported back", ts, {}
                            continue
                        if head.startswith("<turn_aborted>"):
                            yield "notice", "the operator interrupted the assistant", ts, {}
                            continue
                        if head.startswith(CODEX_HARNESS_OPENINGS):
                            continue
                    texts.append(text)
                elif btype in ("input_image", "image", "input_file"):
                    attachments.append(btype.replace("input_", ""))
            body = "\n\n".join(texts)
            if not body.strip() and not attachments:
                continue
            if role == "user":
                yield "user", body, ts, {"mid_turn": False, "attachments": attachments}
            else:
                yield "assistant", body, ts, {"update": payload.get("phase") == "commentary"}
            continue
        if not modern and kind == "event_msg" and ptype in ("user_message", "agent_message"):
            body = payload.get("message")
            if not isinstance(body, str) or not body.strip():
                continue
            if ptype == "user_message":
                yield "user", body, ts, {"mid_turn": False, "attachments": []}
            else:
                yield "assistant", body, ts, {"update": payload.get("phase") == "commentary"}


# ------------------------------------------------------------------ writing
def fenced(text: str) -> str:
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    fence = "`" * max(3, longest + 1)
    return f"{fence}text\n{text}\n{fence}\n"


def local_date(ts: str | None, fallback: float) -> str:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone().strftime("%Y-%m-%d")
    except (AttributeError, ValueError):
        return datetime.fromtimestamp(fallback).strftime("%Y-%m-%d")


def inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def export(found: dict, out_root: Path, work_log: bool, replace: bool) -> dict:
    source = Path(found["source"])
    if inside(out_root, CLAUDE_HOME) or inside(out_root, CODEX_HOME):
        raise ValueError("the output folder may not be inside ~/.claude or ~/.codex: native histories are read-only")
    provider, sid = found["provider"], found["session_id"]
    out_root = out_root.resolve()
    out_dir = out_root / provider / f"{local_date(found['first_timestamp'], source.stat().st_mtime)}_{sid}"
    export_path, record_path = out_dir / "export.md", out_dir / "record.json"
    if export_path.exists() and not replace:
        raise FileExistsError(f"already exported: {export_path} (pass --replace to keep it aside and export again)")

    # The size is taken once. Reading and hashing stop at that byte, so a session that is still being
    # written is exported up to this point and the hash describes exactly what was read.
    size_before = source.stat().st_size
    source_hash = sha256_of(source, size_before)
    out_dir.mkdir(parents=True, exist_ok=True)
    mask = Masker()
    stats: dict = {}
    counts = {"operator": 0, "operator_mid_turn": 0, "assistant": 0, "assistant_updates": 0,
              "boundaries": 0, "notices": 0, "work_log_lines": 0}
    last_ts = None
    parser = parse_claude if provider == "claude" else parse_codex
    body_path = out_dir / ".export.body.tmp"
    try:
        with body_path.open("w", encoding="utf-8") as body:
            for kind, text, ts, detail in parser(source, stats, size_before):
                last_ts = ts or last_ts
                when = f" · {ts}" if ts else ""
                if kind in ("user", "assistant"):
                    clean = mask(ANSI_RE.sub("", text)).strip("\n")
                    if kind == "user":
                        counts["operator"] += 1
                        label = "Operator"
                        if detail.get("mid_turn"):
                            counts["operator_mid_turn"] += 1
                            label = "Operator (sent while the assistant was working)"
                        body.write(f"## U{counts['operator']} · {label}{when}\n\n")
                    else:
                        counts["assistant"] += 1
                        label = "Assistant"
                        if detail.get("update"):
                            counts["assistant_updates"] += 1
                            label = "Assistant (progress update)"
                        body.write(f"## A{counts['assistant']} · {label}{when}\n\n")
                    body.write(fenced(clean) + "\n")
                    for name in detail.get("attachments") or []:
                        body.write(f"*attachment: {mask(name)}*\n\n")
                elif kind == "boundary":
                    counts["boundaries"] += 1
                    facts = [str(detail["trigger"])] if detail.get("trigger") else []
                    if detail.get("before"):
                        facts.append(f"{detail['before']:,} tokens before, {detail.get('after') or 0:,} after")
                    body.write(f"---\n\n**Context compacted here**{when}{' (' + '; '.join(facts) + ')' if facts else ''}. "
                               "The summary the harness generated is not a turn and is not exported.\n\n---\n\n")
                elif kind == "notice":
                    counts["notices"] += 1
                    body.write(f"*{mask(text)}{when}*\n\n")
                elif kind == "tool" and work_log:
                    counts["work_log_lines"] += 1
                    body.write(f"- work log{when} · {mask(text)}\n\n")
    except BaseException:
        body_path.unlink(missing_ok=True)  # leave no half-written file behind
        raise

    size_after = source.stat().st_size
    exported_at = datetime.now().astimezone().isoformat(timespec="seconds")
    left_out = "system and developer text, hidden reasoning, tool calls and their output"
    if work_log:
        left_out += " (one line per tool call is kept as a work log: name and target only)"
    header = [
        f"# Chat export: {provider} session {sid}",
        "",
        f"- Source: `{source}` (the session log on disk, read only)",
        f"- Source sha256: `{source_hash}` ({size_before:,} bytes, {stats.get('source_lines', 0):,} lines)"
        + (f". The session was still being written: this export holds its first {size_before:,} bytes "
           f"(the log had {size_after:,} when the export ended)" if size_after != size_before else ""),
        f"- First record: {found['first_timestamp'] or 'unknown'} · last turn or event: {last_ts or 'unknown'}",
        f"- Operator turns: {counts['operator']} (U1 to U{counts['operator']}; {counts['operator_mid_turn']} sent "
        "while the assistant was working)",
        f"- Assistant turns: {counts['assistant']} (A1 to A{counts['assistant']}; {counts['assistant_updates']} are "
        "progress updates)",
        f"- Compaction boundaries: {counts['boundaries']} · harness notices: {counts['notices']} · secrets masked: "
        f"{mask.total}",
        f"- Exported: {exported_at} by export_chat_log.py {VERSION}",
        "",
        "Every turn of the operator and every answer of the assistant is here in full and in order, each in its own "
        f"fenced block. Left out: {left_out}. Changed: secrets are replaced by `[masked:<kind>]` and terminal colour "
        "codes are removed; nothing else.",
        "",
        "---",
        "",
        "",
    ]
    if export_path.exists():  # --replace: the earlier export is kept aside, never overwritten
        stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        for old in (export_path, record_path):
            if old.exists():
                old.rename(old.with_name(f"{old.stem}.before-{stamp}{old.suffix}"))
    tmp_path = out_dir / ".export.md.tmp"
    with tmp_path.open("w", encoding="utf-8") as out, body_path.open("r", encoding="utf-8") as body:
        out.write("\n".join(header))
        shutil.copyfileobj(body, out)
    body_path.unlink()
    os.replace(tmp_path, export_path)

    record = {
        "provider": provider,
        "session_id": sid,
        "source_path": str(source),
        "source_sha256": source_hash,
        "source_bytes": size_before,
        "source_bytes_read": size_before,
        "source_bytes_when_export_ended": size_after,
        "source_lines": stats.get("source_lines", 0),
        "source_unreadable_lines": stats.get("unreadable_lines", 0),
        "source_changed_during_export": size_after != size_before,
        "source_read_note": ("the session was still being written; read and hashed up to source_bytes_read only"
                             if size_after != size_before else "the whole log was read"),
        "first_timestamp": found["first_timestamp"],
        "last_timestamp": last_ts,
        "turns": {"operator": counts["operator"], "operator_mid_turn": counts["operator_mid_turn"],
                  "assistant": counts["assistant"], "assistant_updates": counts["assistant_updates"]},
        "compaction_boundaries": counts["boundaries"],
        "harness_notices": counts["notices"],
        "work_log_lines": counts["work_log_lines"],
        "secrets_masked": mask.counts,
        "export_path": str(export_path),
        "export_sha256": sha256_of(export_path),
        "exported_at": exported_at,
        "exporter_version": VERSION,
    }
    record_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return record


# ------------------------------------------------------------------ command line
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="export_chat_log.py",
        description="Find ONE Claude Code or Codex session and export it word for word. No batch mode.")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, text in (("find", "Locate one session and print where it is. Writes nothing."),
                       ("export", "Export one session to <out-root>/<provider>/<date>_<id>/.")):
        cmd = sub.add_parser(name, help=text, description=text)
        pick = cmd.add_mutually_exclusive_group(required=True)
        pick.add_argument("--source", help="path of the session log")
        pick.add_argument("--session-id", help="session id, or its first characters if they are unique")
        pick.add_argument("--match", help="text fragment of a prompt (searched in the prompt history index)")
        pick.add_argument("--latest", action="store_true", help="the most recently written session")
        cmd.add_argument("--provider", choices=["auto", "claude", "codex"], default="auto")
        cmd.add_argument("--json", action="store_true", help="print the result as JSON")
        if name == "export":
            cmd.add_argument("--out-root", default=str(DEFAULT_OUT_ROOT),
                             help=f"folder that holds the exports (default {DEFAULT_OUT_ROOT})")
            cmd.add_argument("--work-log", action="store_true",
                             help="add one line per tool call (name and target only)")
            cmd.add_argument("--replace", action="store_true",
                             help="export again; the earlier export is renamed aside, not overwritten")
    return parser


def main(argv: list[str]) -> int:
    # A request for many sessions is refused with one line, before anything is read.
    selectors, many, skip = 0, bool(argv) and argv[0].lower() in MANY_WORDS, False
    for arg in argv:
        if skip:  # the value of an option is not a request
            skip = False
            continue
        name = arg.split("=")[0]
        selectors += name in ("--source", "--session-id", "--match", "--latest")
        many = many or name.lower() in MANY_FLAGS
        skip = name in ("--source", "--session-id", "--match", "--out-root", "--provider") and "=" not in arg
    if many or selectors > 1:
        print(REFUSAL, file=sys.stderr)
        return 2
    parser = build_parser()
    args, extra = parser.parse_known_args(argv)
    if extra:  # several logs on one line (a shell pattern that expanded) is a request for many sessions
        if any(e.endswith(".jsonl") or os.path.exists(e) for e in extra):
            print(REFUSAL, file=sys.stderr)
            return 2
        parser.error("unrecognized arguments: " + " ".join(extra))
    try:
        found = resolve(args)
        if args.command == "find":
            if args.json:
                print(json.dumps(found, indent=2))
            else:
                for key in ("provider", "session_id", "source", "bytes", "modified", "first_timestamp", "note"):
                    if found.get(key) is not None:
                        print(f"{key}: {found[key]}")
            return 0
        record = export(found, Path(args.out_root).expanduser(), args.work_log, args.replace)
        if args.json:
            print(json.dumps(record, indent=2, ensure_ascii=False))
        else:
            turns = record["turns"]
            print(f"exported {record['export_path']}")
            print(f"operator turns {turns['operator']} · assistant turns {turns['assistant']} · "
                  f"boundaries {record['compaction_boundaries']} · secrets masked {sum(record['secrets_masked'].values())}")
        return 0
    except SystemExit as stop:
        print(stop.code if isinstance(stop.code, str) else REFUSAL, file=sys.stderr)
        return 2
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
