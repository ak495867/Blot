import argparse
import csv
import fnmatch
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

from pygments.lexers import get_lexer_for_filename
from pygments.lexers.special import TextLexer
from pygments.token import Comment, Text

from blot import __version__

DEFAULT_IGNORES = {
    ".git", ".hg", ".svn", ".idea", ".vscode", ".venv", "venv",
    "env", "__pycache__", "node_modules", "bower_components",
    "dist", "build", "target", "coverage", ".next", ".nuxt",
    ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox",
    "vendor", "Pods", ".gradle", ".terraform"
}

SPECIAL_FILENAMES = {
    "Dockerfile", "Containerfile", "Makefile", "GNUmakefile",
    "Jenkinsfile", "Vagrantfile", "Procfile", "justfile",
    ".gitignore", ".gitattributes", ".dockerignore", ".editorconfig",
    ".env.example", ".env.sample", "CMakeLists.txt"
}

def get_lexer(path):
    try:
        return get_lexer_for_filename(path.name, stripnl=False, ensurenl=False)
    except Exception:
        if path.name in SPECIAL_FILENAMES:
            return TextLexer()
        return None

def classify_source(source, lexer):
    states = [[False, False] for _ in source.splitlines()]
    line_index = 0

    try:
        tokens = lexer.get_tokens(source)
        for token_type, value in tokens:
            pieces = value.splitlines(keepends=True)
            if not pieces and value == "":
                continue
            for piece in pieces:
                if line_index >= len(states):
                    states.append([False, False])
                if token_type in Comment:
                    if piece.strip():
                        states[line_index][1] = True
                elif token_type in Text and not piece.strip():
                    pass
                elif piece.strip():
                    states[line_index][0] = True
                if piece.endswith(("\n", "\r")):
                    line_index += 1
    except Exception:
        return {"code": len(source.splitlines()), "comments": 0, "blank": 0}

    result = {"code": 0, "comments": 0, "blank": 0}
    for has_code, has_comment in states:
        if has_code:
            result["code"] += 1
        elif has_comment:
            result["comments"] += 1
        else:
            result["blank"] += 1
    return result

def matches_patterns(path, patterns):
    if not patterns:
        return False
    normalized = path.as_posix()
    name = path.name
    return any(
        fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(normalized, pattern)
        for pattern in patterns
    )

def scan_folder(root, include=None, exclude=None, show_hidden=False,
                follow_symlinks=False, no_ignore=False):
    root = Path(root).expanduser().resolve()
    if not root.exists():
        raise FileNotFoundError(f"Path does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {root}")

    include = include or []
    exclude = exclude or []
    by_language = defaultdict(lambda: {
        "files": 0, "code": 0, "comments": 0, "blank": 0, "total": 0
    })
    totals = {"files": 0, "code": 0, "comments": 0, "blank": 0, "total": 0}
    errors = []
    skipped = 0

    for current, dirs, filenames in os.walk(root, followlinks=follow_symlinks):
        current_path = Path(current)
        relative_dir = current_path.relative_to(root)

        dirs[:] = sorted(
            d for d in dirs
            if (no_ignore or d not in DEFAULT_IGNORES)
            and (show_hidden or not d.startswith("."))
            and not matches_patterns(relative_dir / d, exclude)
        )

        for filename in sorted(filenames):
            path = current_path / filename
            relative = path.relative_to(root)

            if not show_hidden and any(part.startswith(".") for part in relative.parts):
                skipped += 1
                continue
            if matches_patterns(relative, exclude):
                skipped += 1
                continue
            if include and not matches_patterns(relative, include):
                skipped += 1
                continue

            lexer = get_lexer(path)
            if lexer is None:
                skipped += 1
                continue

            try:
                if path.is_symlink() and not follow_symlinks:
                    skipped += 1
                    continue
                raw = path.read_bytes()
                if b"\x00" in raw:
                    skipped += 1
                    continue
                source = raw.decode("utf-8", errors="replace")
                counts = classify_source(source, lexer)
                language = lexer.name

                item = by_language[language]
                item["files"] += 1
                item["code"] += counts["code"]
                item["comments"] += counts["comments"]
                item["blank"] += counts["blank"]
                item["total"] += sum(counts.values())

                totals["files"] += 1
                for key in ("code", "comments", "blank"):
                    totals[key] += counts[key]
                totals["total"] += sum(counts.values())
            except (OSError, PermissionError, UnicodeError) as exc:
                errors.append({"file": str(relative), "error": str(exc)})

    return {
        "directory": str(root),
        "summary": totals,
        "languages": dict(sorted(by_language.items())),
        "skipped": skipped,
        "errors": errors
    }

def print_table(report, top=0):
    print(f"\nBLOT  |  {report['directory']}\n")
    print(f"{'LANGUAGE':<23} {'FILES':>8} {'CODE':>12} {'COMMENTS':>12} {'BLANK':>12} {'TOTAL':>12}")
    print("-" * 83)

    rows = list(report["languages"].items())
    if top > 0:
        rows = sorted(rows, key=lambda item: item[1]["code"], reverse=True)[:top]

    for language, stats in rows:
        print(
            f"{language[:22]:<23} {stats['files']:>8,} "
            f"{stats['code']:>12,} {stats['comments']:>12,} "
            f"{stats['blank']:>12,} {stats['total']:>12,}"
        )

    print("-" * 83)
    total = report["summary"]
    print(
        f"{'TOTAL':<23} {total['files']:>8,} {total['code']:>12,} "
        f"{total['comments']:>12,} {total['blank']:>12,} "
        f"{total['total']:>12,}"
    )
    print(f"\nSkipped: {report['skipped']:,}  |  Errors: {len(report['errors']):,}")
    if report["errors"]:
        print("\nUnreadable files:")
        for error in report["errors"][:10]:
            print(f"  {error['file']}: {error['error']}")
        if len(report["errors"]) > 10:
            print(f"  ... and {len(report['errors']) - 10} more")

def write_csv(report, output):
    fields = ["language", "files", "code", "comments", "blank", "total"]
    with open(output, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for language, stats in report["languages"].items():
            writer.writerow({"language": language, **stats})
        writer.writerow({"language": "TOTAL", **report["summary"]})

def build_parser():
    parser = argparse.ArgumentParser(
        prog="blot",
        description="Count source lines across a project, recursively."
    )
    parser.add_argument("path", nargs="?", default=".", help="Folder to scan")
    parser.add_argument("-f", "--format", choices=("table", "json", "csv"),
                        default="table", help="Output format")
    parser.add_argument("-o", "--output", help="Write report to a file")
    parser.add_argument("-i", "--include", action="append", default=[],
                        help="Include glob pattern; can be repeated")
    parser.add_argument("-e", "--exclude", action="append", default=[],
                        help="Exclude glob pattern; can be repeated")
    parser.add_argument("--hidden", action="store_true",
                        help="Include hidden files and folders")
    parser.add_argument("--no-ignore", action="store_true",
                        help="Do not skip common dependency and build folders")
    parser.add_argument("--follow-symlinks", action="store_true",
                        help="Follow symbolic links")
    parser.add_argument("--top", type=int, default=0,
                        help="Show only the top N languages by code LOC")
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {__version__}")
    return parser

def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.top < 0:
        parser.error("--top must be zero or greater")

    try:
        report = scan_folder(
            args.path,
            include=args.include,
            exclude=args.exclude,
            show_hidden=args.hidden,
            follow_symlinks=args.follow_symlinks,
            no_ignore=args.no_ignore
        )

        if args.format == "json":
            rendered = json.dumps(report, indent=2)
            if args.output:
                Path(args.output).write_text(rendered + "\n", encoding="utf-8")
            else:
                print(rendered)
        elif args.format == "csv":
            if args.output:
                write_csv(report, args.output)
                print(f"CSV report saved to {args.output}")
            else:
                writer = csv.DictWriter(
                    sys.stdout,
                    fieldnames=["language", "files", "code", "comments", "blank", "total"]
                )
                writer.writeheader()
                for language, stats in report["languages"].items():
                    writer.writerow({"language": language, **stats})
                writer.writerow({"language": "TOTAL", **report["summary"]})
        else:
            print_table(report, args.top)
            if args.output:
                Path(args.output).write_text(
                    json.dumps(report, indent=2) + "\n", encoding="utf-8"
                )
                print(f"\nJSON report saved to {args.output}")

        return 1 if report["errors"] else 0
    except (OSError, ValueError) as exc:
        print(f"blot: error: {exc}", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
