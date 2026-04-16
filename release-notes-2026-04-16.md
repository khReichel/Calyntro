# Release Notes · Calyntro v0.3.8
**April 16, 2026**

---

## C# Support

Calyntro now analyses C# codebases. Cyclomatic complexity, cognitive complexity, and lines of code are computed per file during import — no additional configuration required.

The metrics appear in every view that already works for other languages: Hotspot Analysis, Complexity trends, Scatter Analysis, and the File Details drawer.

---

## Getting Started Faster — Config Generator

Setting up `config.yaml` for a new repository used to mean manually inspecting the directory tree and git log. A new script does this for you:

```bash
./scripts/generate_config.sh /path/to/repo -o config/config.yaml
```

It produces a ready-to-use draft with:

- **Authors** — one entry per person, with e-mail variants automatically detected as aliases
- **Components** — top-level directories ranked by commit activity
- **Exclusions** — low-activity directories and non-code file types pre-filled

Review the output, add your teams, and run the import. Teams are left empty intentionally — they reflect your organisation's structure and need to be filled in manually.

---

## Changed: Dashboard Port

The dashboard now runs on **port 8765** instead of port 80.

```
http://localhost:8765
```

Port 80 requires elevated privileges on many systems and frequently conflicts with other running services. No changes to your `config.yaml` are needed — only the `docker-compose.yml` is affected.

---

## Bug Fix: Silent Import Failures for C# Files

In previous releases, C# metric values were imported as empty — even when `csharpmetrics` was installed and appeared to run correctly. The root cause was a Docker build issue: `Cargo.lock` was excluded from the build context, causing dependency versions to be resolved differently in Docker than in local builds. This produced a binary that started without errors but failed silently on every file.

The build is now reproducible. If you have existing data with empty C# metrics, re-running the import will fill them in.

---

## Under the Hood

- Running the importer against a host-mounted repository no longer requires a manual `git config --add safe.directory` step — both `import_local_src.sh` and `generate_config.sh` handle this automatically.
- `import_local_src.sh` now uses the locally built image instead of the published one, keeping local development self-contained.
