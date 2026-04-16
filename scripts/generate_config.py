#!/usr/bin/env python3
"""
generate_config.py

Scans a git repository and writes a draft Calyntro config.yaml with:

  analysis.users             — one entry per author, email variants as aliases
  analysis.components        — source-code directories at appropriate depth
  analysis.excluded_prefixes — top-level dirs with no meaningful code
  analysis.excluded_extensions — non-code file types found in HEAD

Teams and team_memberships are left empty — they require organisational
knowledge that predates the analysis and should be filled in manually.

Usage:
  python scripts/generate_config.py /path/to/repo [options]

Options:
  --branch BRANCH       Branch to scan          (default: auto-detected)
  --since  YYYY-MM-DD   analysis_since date     (default: 2020-01-01)
  --min-files INT       Min code files for a dir to become a component
                                                (default: 5)
  --max-depth INT       Max directory depth to explore (default: 2)
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

def _is_code_file(path: str) -> bool:
    ext = Path(path).suffix.lower()
    return bool(ext) and ext not in _NON_CODE


def _build_code_tree(repo: Repo) -> tuple[dict, dict]:
    """
    Walk the HEAD tree and build two maps over directories that contain code:
      recursive_count[dir] — total code files in dir and all subdirectories
      children[dir]        — direct child directories that contain code files
    Root-level files (no parent directory) are ignored.
    """
    recursive_count: dict[str, int] = defaultdict(int)
    children: dict[str, set] = defaultdict(set)

    for item in repo.head.commit.tree.traverse():
        if item.type != "blob" or not _is_code_file(item.path):
            continue
        parts = item.path.split("/")
        if len(parts) < 2:
            continue  # root-level file — no directory to assign

        for depth in range(1, len(parts)):
            ancestor = "/".join(parts[:depth])
            recursive_count[ancestor] += 1
            if depth > 1:
                parent = "/".join(parts[:depth - 1])
                children[parent].add(ancestor)

    return dict(recursive_count), {k: set(v) for k, v in children.items()}


def _collect_components(
    dir_path: str,
    recursive_count: dict,
    children: dict,
    min_files: int,
    max_depth: int,
    depth: int,
) -> list[str]:
    """
    Recursively decide whether dir_path is a component or should be
    expanded into its children.

    A directory is expanded when it has >= 2 children that each contain
    at least min_files code files AND the current depth is below max_depth.
    Otherwise the directory itself becomes the component (if it meets min_files).
    """
    total = recursive_count.get(dir_path, 0)
    if total < min_files:
        return []

    if depth >= max_depth:
        return [dir_path]

    significant = sorted(
        [c for c in children.get(dir_path, set())
         if recursive_count.get(c, 0) >= min_files],
        key=lambda c: recursive_count.get(c, 0),
        reverse=True,
    )

    if len(significant) >= 2:
        result = []
        for child in significant:
            result.extend(_collect_components(
                child, recursive_count, children, min_files, max_depth, depth + 1
            ))
        return result

    return [dir_path]


def _find_components(
    repo: Repo,
    min_files: int,
    max_depth: int,
) -> tuple[list[dict], list[str]]:
    """
    Return (components, excluded_prefixes).
    Only actual top-level directories (trees, not files) are considered.
    """
    recursive_count, children = _build_code_tree(repo)

    # Top-level directories only — explicitly excludes root-level files
    top_dirs = sorted(
        item.name for item in repo.head.commit.tree if item.type == "tree"
    )

    component_paths: list[str] = []
    excluded_prefixes: list[str] = []

    for top_dir in top_dirs:
        found = _collect_components(
            top_dir, recursive_count, children, min_files, max_depth, depth=1
        )
        if found:
            component_paths.extend(found)
        else:
            excluded_prefixes.append(f"{top_dir}/")

    components = [
        {
            "component_name": p.replace("/", "_"),
            "path_prefix":    f"{p}/",
            "display_name":   p.split("/")[-1].replace("_", " ").replace("-", " ").title(),
        }
        for p in component_paths
    ]

    return components, sorted(excluded_prefixes)


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

def generate(repo_path: str, branch: str, since: str, min_files: int, max_depth: int) -> dict:
    repo = Repo(repo_path)

    print("  Scanning commit history for authors …", file=sys.stderr)
    users = _extract_users(repo, branch)

    print("  Reading HEAD tree …", file=sys.stderr)
    components, excluded_prefixes = _find_components(repo, min_files, max_depth)
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
    parser.add_argument("--min-files", type=int, default=5, metavar="INT",
                        help="Min code files for a directory to become a component "
                             "(default: 5)")
    parser.add_argument("--max-depth", type=int, default=2, metavar="INT",
                        help="Max directory depth to explore (default: 2)")
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

    config = generate(args.repo_path, branch, args.since, args.min_files, args.max_depth)

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
