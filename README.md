# RepoLens README

<div align="center">

  <img src="artefacts/repoLens.png" alt="RepoLens Logo" width="200"/>

# RepoLens

**From Code to Clarity: Understand Your Project's Pulse**

[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue.svg)](https://github.com/ibrl/RepoLens/wiki)

</div>

---

## Overview

**RepoLens**  is an advanced repository analytics platform that extracts and interprets version control metadata to uncover software evolution patterns, code quality risks, and team interaction dynamics.
By bridging the gap between raw Git history and actionable insights, Pulseflow empowers engineering teams to manage technical debt proactively, optimize their architecture, and improve collaboration.

It uses pre-built Docker images and a configurable workflow to provide actionable insights without requiring users to build images locally.

## Key Features

RepoLens provides a multi-dimensional view of your software project across **Files**, **Modules**, and **Teams**:

###  Evolution & Pulse
* **Hotspot Trends:** Identifies files and modules that are becoming increasingly problematic ("Rising") or stabilizing ("Cooling") by comparing historical baselines with current activity.
* **Activity Recency:** Quickly spot abandoned legacy code versus areas of intense recent development.
* **Code Churn:** Analyze the raw volume of changes (added/deleted lines) to find unstable components.

###  Structure & Logic
* **Combined Complexity:** A holistic view combining *Cognitive Complexity*, *Cyclomatic Complexity*, and structural *Effort* to pinpoint exactly where code is hardest to maintain.

###  Team & Knowledge (Conway's Law in Action)
* **Code Ownership & Fragmentation:** Identify knowledge silos (single points of failure/Bus Factor) and fragmented code (too many developers touching the same file).
* **Module-Team Alignment:** Visualize which teams effectively "own" which architectural components, helping to align software architecture with team topology.

---

## Quick Start

### 1. Prepare Configuration

RepoLens uses a **`config.yaml`** file in the `config/` directory. Example:

```yaml
project:
  name: "myproject"
  db_path: "/app/data"
  db_update_path: "/app/data/update_data"
  db_basename: "repolens"
  repo_path: "/repo"
```

> Paths defined in the config are automatically mapped to the containers. Users do **not** need to change any file system paths manually.

---

### 2. Start RepoLens Runtime

```bash
./manage.sh up
```

This will start:

* `backend` (API and analysis engine)
* `ui` (frontend dashboard)
* `gateway` (Nginx for web access)

Stop containers:

```bash
./manage.sh down
```

---

### 3. Import Repository Data (Staging)

```bash
./manage.sh import /path/to/local/repo
```

* Imports repository data **into the staging database** (`db_update_path`).
* No live data is modified yet.
* If no path is provided, the `repo_path` from `config.yaml` is used.

---

### 4. Refresh Runtime Database

```bash
./manage.sh refresh
```

* Atomically swaps the staging database into the runtime database (`db_path`).
* Stops the backend container briefly to allow the swap.
* Creates a timestamped backup of the previous runtime database.
* Restarts the backend container automatically.

---

### 5. Update Docker Images

```bash
./manage.sh pull    # Pull latest images
./manage.sh update  # Pull latest images and restart containers
```

---

### 6. Optional: View Logs

```bash
docker compose logs -f
```

## Architecture

* **Backend:** FastAPI + Python for metrics and analysis.
* **Storage:** DuckDB, embedded, high-performance analytical DB.
* **UI:** React + Tailwind CSS, served through Nginx gateway.
* **Importer:** CLI tool inside container, processes Git history and populates staging DB.

---

## Recommended Workflow

1. `import` → Import repository into staging.
2. `refresh` → Swap staging DB into runtime atomically.
3. `update` → Pull latest container images and restart runtime.
4. Repeat steps 1–3 daily or as needed.

---

## Workflow Diagram

![RepoLens Workflow](artefacts/repolens_workflow.png)

---

## Notes

* All paths are read from `config.yaml` and mapped correctly in Docker Compose.
* The staging workflow ensures **zero downtime** for the backend during updates.
* Backups are automatically created before every refresh.

---

## Feedback, Bugs & Feature Requests

RepoLens is actively evolving, and your feedback is highly appreciated!

If you encounter any issues, discover a bug, or have a great idea for a new analysis feature, please let us know. We welcome all feedback to make this tool better for everyone.

 **[Open an Issue on our GitHub Tracker](https://github.com/khreichel/RepoLens/issues)**

When reporting bugs, please provide as much context as possible (steps to reproduce, logs, or error messages). For feature requests, describe the use case and how it would benefit your workflow.

---
##  Terms of Use & Disclaimer

RepoLens is distributed as free-to-use Docker containers. You are welcome to deploy and use the provided images for your own projects.

**Disclaimer of Warranty:**
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE. USE AT YOUR OWN RISK.
