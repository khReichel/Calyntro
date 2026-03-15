<div align="center">

  <img src="ui/pulseflowui/public/pulseflow.svg" alt="Pulseflow Logo" width="200"/>

  # Pulseflow

  **From Code to Clarity: Understand Your Project's Pulse**

  [![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-blue.svg)](https://khreichel.github.io/Pulseflow/)

</div>

---

**Pulseflow** is an advanced repository analytics platform that extracts and interprets version control metadata to uncover software evolution patterns, code quality risks, and team interaction dynamics.

By bridging the gap between raw Git history and actionable insights, Pulseflow empowers engineering teams to manage technical debt proactively, optimize their architecture, and improve collaboration.

---

##  Key Features

Pulseflow provides a multi-dimensional view of your software project across **Files**, **Modules**, and **Teams**:

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

##  Quick Start

Get Pulseflow running locally via Docker in under 5 minutes:

```bash
# 1. Download the deployment configuration
# (Assuming you provide a docker-compose.yml and manage.sh for users)
mkdir pulseflow-deployment && cd pulseflow-deployment
# Download necessary files...

# 2. Setup your configuration
# Create your config file based on the provided template
cp examples/pulseflow_config.yaml ./pulseflow_config.yaml

# Edit pulseflow_config.yaml to point to the repository you want to analyze.
# You can use a symlink in the project root for easier access:
ln -s /path/to/your/target/repo ./repo

# 3. Import Data
# This will analyze your repository and build the DuckDB databases
./manage.sh import ./repo

# 4. Start the Application
./manage.sh up
```

Now open your browser at **`http://localhost`** to explore your dashboard.

---

##  Architecture

Pulseflow is designed for speed and simplicity, utilizing a modern, containerized stack:

* **Backend:** A fast, asynchronous REST API built with **Python & FastAPI**.
* **Storage:** **DuckDB** serves as an embedded analytical database, providing blazing-fast queries over complex version control data without the overhead of a dedicated database server.
* **Frontend:** A highly responsive Single Page Application built with **React, Vite, Tailwind CSS, and Radix UI**, featuring interactive charts (Recharts) and 3D visualizations.
* **Importer:** A robust CLI tool utilizing `gitpython` and `rust-code-analysis` to parse repository history and calculate metrics efficiently.

---

##  Comprehensive Documentation

For detailed guides on configuration, API usage, and interpreting the metrics, please visit our official documentation:

**[Pulseflow Documentation (GitHub Pages)](https://khreichel.github.io/Pulseflow/)**

**Quick Links:**
* [Understanding Pulseflow Analyses](https://khreichel.github.io/Pulseflow/analysis.html): Deep dive into what each metric means.
* [Configuration Guide](https://khreichel.github.io/Pulseflow/pulseflow_config.html): How to set up teams, exclude files, and map your architecture.
* [API Reference](https://khreichel.github.io/Pulseflow/api.html): Build your own tools on top of the Pulseflow REST API.

---

##  Terms of Use & Disclaimer

Pulseflow is distributed as free-to-use Docker containers. You are welcome to deploy and use the provided images for your own projects.

**Disclaimer of Warranty:**
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE. USE AT YOUR OWN RISK.
