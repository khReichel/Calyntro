#!/usr/bin/env python3
"""
generate_config.py

Scans a git repository and writes a draft Calyntro config.yaml with:

  analysis.users            — one entry per author, email variants as aliases
  analysis.components       — top-level dirs ranked by commit activity
  analysis.excluded_prefixes — low-activity dirs (complement of components)
  analysis.excluded_extensions — non-code file types found in HEAD

Teams and team_memberships are left empty — they require organisational
knowledge that predates the analysis and should be filled in manually.

Usage:
  python scripts/generate_config.py /path/to/repo [options]

Options:
  --branch BRANCH       Branch to scan          (default: auto-detected)
  --since  YYYY-MM-DD   analysis_since date     (default: 2020-01-01)
  --threshold FLOAT     Min commit share [0..1] for a dir to become a
                        component               (default: 0.02 = 2 %%)
  -o, --output PATH     Write to file instead of stdout
"""

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml
from git import Repo, InvalidGitRepositoryError


# ---------------------------------------------------------------------------
# Non-code extension list
# ---------------------------------------------------------------------------

_NON_CODE: set[str] = {
    # Documentation / text
    ".md", ".rst", ".txt", ".adoc", ".log", ".csv", ".tsv",
    # Build / config
    ".yml", ".yaml", ".toml", ".ini", ".cfg", ".conf", ".properties",
    ".lock", ".sum", ".mod", ".in", ".ac", ".m4",
    ".bazelrc", ".bazeliskrc", ".cmake",
    # Scripts (tooling, not product code)
    ".sh", ".bash", ".zsh", ".fish", ".ps1", ".bat", ".cmd",
    # IDE / VCS
    ".gitignore", ".gitattributes", ".editorconfig",
    ".prettierignore", ".prettierrc", ".eslintrc", ".eslintignore",
    # Assets / binaries
    ".svg", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".bmp",
    ".pdf", ".docx", ".xlsx", ".pptx",
    ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    # Build artefacts / misc
    ".map", ".patch", ".diff", ".rpath",
}


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

def _extract_users(repo: Repo, branch: str) -> list[dict]:
    """
    Group commit authors by e-mail address.
    Most frequent name per e-mail → canonical name.
    Other spelling variants → aliases list.
    """
    email_names: dict[str, Counter] = defaultdict(Counter)

    for commit in repo.iter_commits(branch):
        email = (commit.author.email or "").strip().lower()
        name  = (commit.author.name  or "").strip()
        if email and name:
            email_names[email][name] += 1

    users: list[dict] = []
    for _, name_counts in sorted(email_names.items()):
        canonical, _ = name_counts.most_common(1)[0]
        aliases = sorted(n for n in name_counts if n != canonical)
        entry: dict = {"name": canonical}
        if aliases:
            entry["aliases"] = aliases
        users.append(entry)

    return sorted(users, key=lambda u: u["name"].lower())


# ---------------------------------------------------------------------------
# Components & excluded_prefixes
# ---------------------------------------------------------------------------

def _top_dir(path: str) -> str | None:
    parts = Path(path).parts
    return parts[0] if parts else None


def _dir_commit_counts(repo: Repo, branch: str) -> Counter:
    """Count commits that touched each top-level directory."""
    counts: Counter = Counter()
    for commit in repo.iter_commits(branch):
        touched = {_top_dir(p) for p in commit.stats.files} - {None}
        for d in touched:
            counts[d] += 1
    return counts


def _head_top_dirs(repo: Repo) -> set[str]:
    """All top-level directories present in the HEAD tree."""
    dirs: set[str] = set()
    for item in repo.head.commit.tree.traverse():
        d = _top_dir(item.path)
        if d:
            dirs.add(d)
    return dirs


def _split_components(
    head_dirs: set[str],
    dir_counts: Counter,
    threshold: float,
) -> tuple[list[dict], list[str]]:
    """
    Dirs above the commit-share threshold → components.
    Dirs below                            → excluded_prefixes.
    Both lists are sorted: components by activity desc, exclusions alphabetically.
    """
    total = sum(dir_counts.values()) or 1
    min_commits = total * threshold

    components: list[dict] = []
    excluded:   list[str]  = []

    for d in sorted(head_dirs, key=lambda x: dir_counts.get(x, 0), reverse=True):
        if dir_counts.get(d, 0) >= min_commits:
            components.append({
                "component_name": d,
                "path_prefix":    f"{d}/",
                "display_name":   d.replace("_", " ").replace("-", " ").title(),
            })
        else:
            excluded.append(f"{d}/")

    return components, sorted(excluded)


# ---------------------------------------------------------------------------
# excluded_extensions
# ---------------------------------------------------------------------------

def _excluded_extensions(repo: Repo) -> list[str]:
    """
    Extensions present in HEAD that are in the non-code set,
    ordered by file count descending.
    """
    counts: Counter = Counter()
    for item in repo.head.commit.tree.traverse():
        if item.type == "blob":
            ext = Path(item.path).suffix.lower()
            if ext:
                counts[ext] += 1
    return [ext for ext, _ in counts.most_common() if ext in _NON_CODE]


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------

def generate(repo_path: str, branch: str, since: str, threshold: float) -> dict:
    repo = Repo(repo_path)

    print("  Scanning commit history for authors …", file=sys.stderr)
    users = _extract_users(repo, branch)

    print("  Counting commits per directory …", file=sys.stderr)
    dir_counts = _dir_commit_counts(repo, branch)

    print("  Reading HEAD tree …", file=sys.stderr)
    head_dirs = _head_top_dirs(repo)
    components, excluded_prefixes = _split_components(head_dirs, dir_counts, threshold)
    excluded_extensions = _excluded_extensions(repo)

    return {
        "project": {
            "name":             Path(repo_path).resolve().name,
            "db_basename":      "calyntro",
            "db_path":          "data",
            "db_update_path":   "data/update_data",
            "repo_path":        "/repo",
            "branch":           branch,
            "analysis_since":   since,
        },
        "analysis": {
            "components":           components,
            "excluded_prefixes":    excluded_prefixes,
            "excluded_extensions":  excluded_extensions,
            "excluded_patterns":    [],
            # Teams require organisational knowledge — fill in manually.
            "users":                users,
            "teams":                [],
            "team_memberships":     {"entries": []},
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _detect_branch(repo: Repo) -> str:
    try:
        return repo.head.reference.name
    except TypeError:
        return "main"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a draft Calyntro config.yaml from a git repository.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("repo_path",
                        help="Path to the git repository")
    parser.add_argument("--branch", default=None,
                        help="Branch to scan (default: auto-detected from HEAD)")
    parser.add_argument("--since", default="2020-01-01", metavar="YYYY-MM-DD",
                        help="analysis_since date (default: 2020-01-01)")
    parser.add_argument("--threshold", type=float, default=0.02, metavar="FLOAT",
                        help="Min commit share for a dir to become a component "
                             "(default: 0.02 = 2%%)")
    parser.add_argument("-o", "--output", default=None, metavar="PATH",
                        help="Write output to file instead of stdout")
    args = parser.parse_args()

    try:
        repo = Repo(args.repo_path)
    except InvalidGitRepositoryError:
        print(f"Error: {args.repo_path!r} is not a git repository.", file=sys.stderr)
        sys.exit(1)

    branch = args.branch or _detect_branch(repo)
    print(f"Scanning {args.repo_path!r}  branch={branch!r} …", file=sys.stderr)

    config = generate(args.repo_path, branch, args.since, args.threshold)

    output = yaml.dump(
        config,
        allow_unicode=True,
        default_flow_style=False,
        sort_keys=False,
    )

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        sys.stdout.write(output)


if __name__ == "__main__":
    main()
